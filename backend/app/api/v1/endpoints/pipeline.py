import json
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import de la session DB
from app.database import get_db

# Imports des services BDD
from app.services.db_service import (
    should_process_file,
    create_pipeline_run,
    save_successful_run,
    save_failed_run,
)

from app.utils.path_builder import build_pipeline_paths
from app.graph.workflow import create_pipeline_workflow

router = APIRouter()
app_graph = create_pipeline_workflow()

# 🎯 État global du serveur (protection contre la concurrence)
PIPELINE_STATUS = {
    "is_running": False,
    "current_file": None
}


class PipelineRequest(BaseModel):
    file_path: str
    project_name: Optional[str] = None  # Optionnel : nom du projet personnalisé


def load_json_if_exists(file_path: Optional[Path]) -> Optional[Dict[str, Any]]:
    """Utilitaire pour charger un fichier JSON d'évaluation s'il existe sur le disque."""
    if file_path and file_path.exists():
        try:
            return json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def calculate_global_kpi(evaluations: Dict[str, Optional[Dict[str, Any]]]) -> float:
    """
    Calcule le KPI Global moyen à partir des vrais JSON d'évaluation des agents.
    Exrait automatiquement les scores et taux (ex: _score, _rate, health_index, etc.).
    """
    scores = []

    for agent_eval in evaluations.values():
        if not agent_eval or not isinstance(agent_eval, dict):
            continue

        # Parcourt technical_evaluation et project_management_kpis
        for section in ["technical_evaluation", "project_management_kpis"]:
            section_data = agent_eval.get(section, {})
            if isinstance(section_data, dict):
                for key, val in section_data.items():
                    # On ne garde que les nombres (ex: 100.0, 75.0, 81.8) qui représentent des scores ou taux
                    if isinstance(val, (int, float)) and not isinstance(val, bool):
                        if any(term in key for term in ["score", "rate", "index", "adherence", "conformity", "completeness"]):
                            scores.append(float(val))

    if not scores:
        return 0.0

    return round(sum(scores) / len(scores), 1)
# def calculate_global_kpi(evaluations: Dict[str, Optional[Dict[str, Any]]]) -> float:
#     """
#     Calcule automatiquement le KPI Global pour le tableau de bord Frontend 
#     en faisant la moyenne des scores disponibles dans les évals.
#     """
#     scores = []
#     for eval_data in evaluations.values():
#         if eval_data and isinstance(eval_data, dict):
#             # Récupération de la valeur si elle existe dans les KPI ou la tech eval
#             for item in eval_data.get("project_management_kpis", []):
#                 val = str(item.get("value", "")).replace("%", "")
#                 try:
#                     scores.append(float(val))
#                 except ValueError:
#                     pass
    
#     return round(sum(scores) / len(scores), 1) if scores else 0.0


@router.get("/status")
async def get_pipeline_status():
    """Endpoint consulté par le Watcher et la CLI pour vérifier la disponibilité."""
    return PIPELINE_STATUS


@router.post("/run")
async def run_pipeline(
    request: PipelineRequest, 
    db: Session = Depends(get_db)
):
    """Exécute le pipeline, évalue les 6 agents et sauvegarde le résultat en BDD."""
    global PIPELINE_STATUS

    # 1. Protection contre les exécutions concurrentes
    if PIPELINE_STATUS["is_running"]:
        raise HTTPException(
            status_code=429,
            detail=f"Pipeline déjà en cours d'exécution sur : {PIPELINE_STATUS['current_file']}"
        )

    file_path_obj = Path(request.file_path)
    if not file_path_obj.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Fichier introuvable sur le disque : {request.file_path}"
        )

    # Déduction du nom de projet s'il n'est pas fourni
    project_name = request.project_name or file_path_obj.parent.name or "Default Project"

    # 2. Vérification DB : le fichier a-t-il changé ? (Hash SHA-256)
    should_run, new_hash, artifact = should_process_file(db, file_path_obj, project_name)
    if not should_run:
        return {
            "status": "skipped",
            "message": "Aucun changement détecté dans le fichier (Hash identique). Exécution ignorée.",
            "artifact_id": str(artifact.id)
        }

    # 3. Verrouillage du serveur et création du PipelineRun en BDD
    PIPELINE_STATUS["is_running"] = True
    PIPELINE_STATUS["current_file"] = request.file_path

    pipeline_run = create_pipeline_run(db, artifact.id)

    try:
        paths = build_pipeline_paths(request.file_path)
        file_content = file_path_obj.read_text(encoding="utf-8")

        initial_state = {
            "file_name": request.file_path,
            "file_content": file_content,
            "prefix": paths["prefix"]
        }

        # 4. Lancement du workflow LangGraph
        final_state = await app_graph.ainvoke(initial_state)

        # 5. Chargement des JSON d'évaluation des 6 Agents pour le Frontend
        evaluations = {
            "parsing": load_json_if_exists(paths.get("parsing_eval")),
            "summary": load_json_if_exists(paths.get("summary_eval")),
            "glossary": load_json_if_exists(paths.get("glossary_eval")),
            "diagram": load_json_if_exists(paths.get("diagram_eval")),
            "writer": load_json_if_exists(paths.get("writer_eval")),
            "layout": load_json_if_exists(paths.get("layout_eval")),
        }

        # Calcul du score KPI Global (ex: 85.6)
        global_kpi = calculate_global_kpi(evaluations)

        # 6. Enregistrement des résultats et évals dans la base de données
        doc_version = save_successful_run(
            db=db,
            artifact=artifact,
            pipeline_run=pipeline_run,
            new_hash=new_hash,
            pdf_path=str(paths["final_pdf"]),
            # Sorties brutes
            structured_json=final_state.get("structured_json"),
            summary_output=final_state.get("summary_output"),
            diagram_output=final_state.get("diagram_output"),
            glossary_output=final_state.get("glossary_output"),
            written_doc=final_state.get("written_doc"),
            layout_output=final_state.get("layout_output"),
            # Évaluations JSON pour le Pop-up Frontend
            parsing_eval=evaluations["parsing"],
            summary_eval=evaluations["summary"],
            glossary_eval=evaluations["glossary"],
            diagram_eval=evaluations["diagram"],
            writer_eval=evaluations["writer"],
            layout_eval=evaluations["layout"],
            # KPI Global pour le tableau principal
            global_kpi_score=global_kpi
        )

        return {
            "status": "success",
            "version_no": doc_version.version_no,
            "global_kpi_score": global_kpi,
            "pdf_path": str(paths["final_pdf"]),
            "data": final_state
        }

    except Exception as e:
        # En cas d'erreur, marquer le PipelineRun comme échoué en BDD
        save_failed_run(db, pipeline_run, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'exécution du pipeline : {str(e)}"
        )

    finally:
        # 7. Libération du serveur
        PIPELINE_STATUS["is_running"] = False
        PIPELINE_STATUS["current_file"] = None
# from pathlib import Path
# from fastapi import APIRouter, HTTPException, status
# from pydantic import BaseModel
# from app.services.db_service import save_successful_run
# from app.utils.path_builder import build_pipeline_paths
# from app.graph.workflow import create_pipeline_workflow

# router = APIRouter()
# app_graph = create_pipeline_workflow()

# # 🎯 État global du serveur
# PIPELINE_STATUS = {
#     "is_running": False,
#     "current_file": None
# }

# class PipelineRequest(BaseModel):
#     file_path: str


# @router.get("/status")
# async def get_pipeline_status():
#     """Endpoint consulté par le Watcher et la CLI pour vérifier la disponibilité."""
#     return PIPELINE_STATUS


# @router.post("/run")
# async def run_pipeline(request: PipelineRequest):
#     """Exécute le pipeline en garantissant qu'un seul traitement tourne à la fois."""
#     global PIPELINE_STATUS

#     # 1. Protection contre les exécutions concurrentes
#     if PIPELINE_STATUS["is_running"]:
#         raise HTTPException(
#             status_code=429,
#             detail=f"Pipeline déjà en cours d'exécution sur : {PIPELINE_STATUS['current_file']}"
#         )

#     file_path_obj = Path(request.file_path)
#     if not file_path_obj.exists():
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND, 
#             detail=f"Fichier introuvable sur le disque : {request.file_path}"
#         )

#     # 2. Verrouillage du serveur
#     PIPELINE_STATUS["is_running"] = True
#     PIPELINE_STATUS["current_file"] = request.file_path

#     try:
#         paths = build_pipeline_paths(request.file_path)
#         file_content = file_path_obj.read_text(encoding="utf-8")

#         initial_state = {
#             "file_name": request.file_path,
#             "file_content": file_content,
#             "prefix": paths["prefix"]
#         }

#         # 3. Lancement synchrone du workflow LangGraph
#         final_state = await app_graph.ainvoke(initial_state)

#         return {
#             "status": "success",
#             "pdf_path": str(paths["final_pdf"]),
#             "data": final_state
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erreur lors de l'exécution du pipeline : {str(e)}"
#         )

#     finally:
#         # 4. Libération systématique du serveur (même en cas d'erreur)
#         PIPELINE_STATUS["is_running"] = False
#         PIPELINE_STATUS["current_file"] = None
