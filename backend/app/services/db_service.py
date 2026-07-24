import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.models import (
    Project,
    Artifact,
    DocVersion,
    PipelineRun,
    ArtifactType,
    PipelineStage,
    GeneratedBy,
)


def compute_sha256(file_path: Path) -> str:
    """Calcule l'empreinte SHA-256 du contenu d'un fichier Markdown."""
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def detect_artifact_type(file_path: Path) -> ArtifactType:
    """
    Détermine dynamiquement le type d'artefact parmi les 6 types supportés :
    (spec, plan, task, constitution, requirements, contracts).
    """
    name = file_path.name.lower()

    if "constitution" in name:
        return ArtifactType.constitution
    elif "requirement" in name:
        return ArtifactType.requirements
    elif "contract" in name:
        return ArtifactType.contracts
    elif "plan" in name:
        return ArtifactType.plan
    elif "task" in name:
        return ArtifactType.task

    return ArtifactType.spec


def get_or_create_project(
    db: Session, project_name: str, repo_url: Optional[str] = None
) -> Project:
    """Récupère un projet existant ou le crée en BDD."""
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        project = Project(name=project_name, repo_url=repo_url)
        db.add(project)
        db.commit()
        db.refresh(project)
    return project


def should_process_file(
    db: Session, file_path: Path, project_name: str
) -> Tuple[bool, str, Artifact]:
    """
    Vérifie si le fichier Markdown a été modifié (comparaison Hash SHA-256 en BDD).
    
    Retourne :
      (should_run: bool, new_hash: str, artifact: Artifact)
    """
    file_path_str = str(file_path.resolve())
    new_hash = compute_sha256(file_path)

    project = get_or_create_project(db, project_name)

    artifact = (
        db.query(Artifact)
        .filter(Artifact.project_id == project.id, Artifact.source_path == file_path_str)
        .first()
    )

    if not artifact:
        # Premier enregistrement de l'artefact
        artifact = Artifact(
            project_id=project.id,
            source_path=file_path_str,
            current_file_hash=None,  # Sera mis à jour en fin de pipeline
            artifact_type=detect_artifact_type(file_path),
        )
        db.add(artifact)
        db.commit()
        db.refresh(artifact)
        return True, new_hash, artifact

    # Si le hash en BDD est identique au fichier actuel -> AUCUN CHANGEMENT
    if artifact.current_file_hash == new_hash:
        return False, new_hash, artifact

    return True, new_hash, artifact


def create_pipeline_run(db: Session, artifact_id: uuid.UUID) -> PipelineRun:
    """Initialise une exécution de pipeline en BDD à l'étape 'parsing'."""
    run = PipelineRun(artifact_id=artifact_id, current_stage=PipelineStage.parsing)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def update_pipeline_stage(
    db: Session,
    pipeline_run: PipelineRun,
    stage: PipelineStage,
    step_outputs: Optional[Dict[str, Any]] = None,
):
    """
    Met à jour l'étape courante (pour le suivi temps réel sur le tableau de bord)
    et enregistre les sorties au fur et à mesure.
    """
    pipeline_run.current_stage = stage
    if step_outputs:
        for key, value in step_outputs.items():
            if hasattr(pipeline_run, key):
                setattr(pipeline_run, key, value)
    db.commit()


def save_successful_run(
    db: Session,
    artifact: Artifact,
    pipeline_run: PipelineRun,
    new_hash: str,
    pdf_path: str,
    # --- Sorties des agents ---
    structured_json: Optional[Dict[str, Any]] = None,
    summary_output: Optional[str] = None,
    diagram_output: Optional[Dict[str, Any]] = None,
    glossary_output: Optional[Dict[str, Any]] = None,
    written_doc: Optional[str] = None,
    layout_output: Optional[str] = None,
    # --- 🎯 Évaluations JSON pour les 6 Onglets du Pop-up Frontend ---
    parsing_eval: Optional[Dict[str, Any]] = None,
    summary_eval: Optional[Dict[str, Any]] = None,
    glossary_eval: Optional[Dict[str, Any]] = None,
    diagram_eval: Optional[Dict[str, Any]] = None,
    writer_eval: Optional[Dict[str, Any]] = None,
    layout_eval: Optional[Dict[str, Any]] = None,
    # --- 🎯 Score KPI Global pour le tableau principal ---
    global_kpi_score: Optional[float] = None,
    commit_hash: Optional[str] = None,
) -> DocVersion:
    """
    Marque le PipelineRun comme complété, enregistre les évals des 6 agents,
    crée la nouvelle DocVersion et met à jour le Hash SHA-256 sur l'Artefact.
    """
    # 1. Mise à jour de l'exécution PipelineRun
    pipeline_run.current_stage = PipelineStage.completed
    pipeline_run.completed_at = datetime.now(timezone.utc)

    # Sorties des agents
    if structured_json: pipeline_run.structured_json = structured_json
    if summary_output: pipeline_run.summary_output = summary_output
    if diagram_output: pipeline_run.diagram_output = diagram_output
    if glossary_output: pipeline_run.glossary_output = glossary_output
    if written_doc: pipeline_run.written_doc = written_doc
    if layout_output: pipeline_run.layout_output = layout_output

    # Évaluations JSON des 6 agents
    pipeline_run.parsing_eval = parsing_eval
    pipeline_run.summary_eval = summary_eval
    pipeline_run.glossary_eval = glossary_eval
    pipeline_run.diagram_eval = diagram_eval
    pipeline_run.writer_eval = writer_eval
    pipeline_run.layout_eval = layout_eval

    # Score global
    pipeline_run.global_kpi_score = global_kpi_score

    # 2. Calcul automatique du numéro de version (v1, v2, v3...)
    last_version = (
        db.query(DocVersion)
        .filter(DocVersion.artifact_id == artifact.id)
        .order_by(DocVersion.version_no.desc())
        .first()
    )
    next_version = (last_version.version_no + 1) if last_version else 1

    # 3. Création de l'enregistrement DocVersion
    doc_version = DocVersion(
        artifact_id=artifact.id,
        version_no=next_version,
        pdf_path=pdf_path,
        source_file_hash=new_hash,
        generated_by=GeneratedBy.agent,
        pipeline_run_id=pipeline_run.id,
        global_kpi_score=global_kpi_score,
        commit_hash=commit_hash,
    )
    db.add(doc_version)

    # 4. Verrouillage : Mise à jour du Hash sur l'Artefact (bloque les exécutions ultérieures identiques)
    artifact.current_file_hash = new_hash

    db.commit()
    db.refresh(doc_version)
    return doc_version


def save_failed_run(
    db: Session,
    pipeline_run: PipelineRun,
    error_message: str,
):
    """Marque une exécution comme échouée et enregistre l'erreur."""
    pipeline_run.current_stage = PipelineStage.failed
    pipeline_run.error_message = error_message
    pipeline_run.completed_at = datetime.now(timezone.utc)
    db.commit()
# import hashlib
# from pathlib import Path
# from typing import Tuple, Optional
# from sqlalchemy.orm import Session

# from app.models import Project, Artifact, DocVersion, PipelineRun, ArtifactType, PipelineStage, GeneratedBy

# def compute_sha256(file_path: Path) -> str:
#     """Calcule le hash SHA-256 du contenu d'un fichier Markdown."""
#     return hashlib.sha256(file_path.read_bytes()).hexdigest()

# def detect_artifact_type(file_path: Path) -> ArtifactType:
#     """Détermine le type d'artefact selon le nom du fichier."""
#     name = file_path.name.lower()
#     if "constitution" in name:
#         return ArtifactType.constitution
#     elif "plan" in name:
#         return ArtifactType.plan
#     elif "task" in name:
#         return ArtifactType.task
#     return ArtifactType.spec

# def get_or_create_project(db: Session, project_name: str) -> Project:
#     """Récupère ou crée le projet dans la DB."""
#     project = db.query(Project).filter(Project.name == project_name).first()
#     if not project:
#         project = Project(name=project_name)
#         db.add(project)
#         db.commit()
#         db.refresh(project)
#     return project

# def should_process_file(db: Session, file_path: Path, project_name: str) -> Tuple[bool, str, Artifact]:
#     """
#     Vérifie en DB si le fichier Markdown a été modifié (comparaison Hash SHA-256).
#     Retourne: (doit_etre_traite: bool, new_hash: str, artifact_obj: Artifact)
#     """
#     file_path_str = str(file_path.resolve())
#     new_hash = compute_sha256(file_path)
    
#     project = get_or_create_project(db, project_name)
    
#     artifact = db.query(Artifact).filter(
#         Artifact.project_id == project.id,
#         Artifact.source_path == file_path_str
#     ).first()

#     if not artifact:
#         # Premier enregistrement de l'artefact
#         artifact = Artifact(
#             project_id=project.id,
#             source_path=file_path_str,
#             current_file_hash=None, # Sera mis à jour après succès du pipeline
#             artifact_type=detect_artifact_type(file_path)
#         )
#         db.add(artifact)
#         db.commit()
#         db.refresh(artifact)
#         return True, new_hash, artifact

#     # Si le hash actuel est identique au hash en DB -> AUCUN CHANGEMENT
#     if artifact.current_file_hash == new_hash:
#         return False, new_hash, artifact

#     return True, new_hash, artifact

# def create_pipeline_run(db: Session, artifact_id) -> PipelineRun:
#     """Initialise un suivi d'exécution PipelineRun."""
#     run = PipelineRun(artifact_id=artifact_id, current_stage=PipelineStage.parsing)
#     db.add(run)
#     db.commit()
#     db.refresh(run)
#     return run

# def save_successful_run(
#     db: Session, 
#     artifact: Artifact, 
#     pipeline_run: PipelineRun, 
#     new_hash: str, 
#     pdf_path: str,
#     final_doc_text: Optional[str] = None
# ):
#     """Enregistre le succès du pipeline, crée une DocVersion et met à jour le hash courant."""
#     # 1. Mise à jour de la mise en exécution
#     pipeline_run.current_stage = PipelineStage.completed
#     pipeline_run.written_doc = final_doc_text
    
#     # 2. Calcul du numéro de version
#     last_version = db.query(DocVersion).filter(
#         DocVersion.artifact_id == artifact.id
#     ).order_by(DocVersion.version_no.desc()).first()
    
#     next_version = (last_version.version_no + 1) if last_version else 1

#     # 3. Création de la version de document
#     doc_version = DocVersion(
#         artifact_id=artifact.id,
#         version_no=next_version,
#         pdf_path=pdf_path,
#         source_file_hash=new_hash,
#         generated_by=GeneratedBy.agent,
#         pipeline_run_id=pipeline_run.id
#     )
#     db.add(doc_version)

#     # 4. Mise à jour du Hash sur l'Artefact pour bloquer les réexécutions identiques
#     artifact.current_file_hash = new_hash
    
#     db.commit()