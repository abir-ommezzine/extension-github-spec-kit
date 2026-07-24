# Dans app/utils/path_builder.py

from pathlib import Path
from typing import Dict

BASE_DIR = Path(__file__).resolve().parents[3]
# BASE_DIR = Path(__file__).resolve().parent.parent.parent

def build_pipeline_paths(file_name: str, version_label: str = "1.0") -> Dict[str, Path]:
    """
    Génère des dossiers et fichiers uniques par version.
    Exemple PDF : outputs/pdf/mon_projet_v1.0.pdf
    """
    file_path = Path(file_name)
    stem = file_path.stem  # Ex: "sdd_spec"
    
    # Préfixe incluant la version
    version_prefix = f"{stem}_v{version_label}"

    data_dir = BASE_DIR / "outputs" / "data"
    eval_dir = BASE_DIR / "outputs" / "evaluations"
    pdf_dir = BASE_DIR / "outputs" / "pdf"
    diagrams_dir = BASE_DIR / "outputs" / "diagrams" / version_prefix

    for d in [data_dir, eval_dir, pdf_dir, diagrams_dir]:
        d.mkdir(parents=True, exist_ok=True)

    return {
        "prefix": stem,
        "version_prefix": version_prefix,
        
        # Fichiers de données
        "parsed_json": data_dir / f"{version_prefix}_parsed.json",
        "summary_json": data_dir / f"{version_prefix}_summary.json",
        "glossary_json": data_dir / f"{version_prefix}_glossary.json",
        "diagrams_json": data_dir / f"{version_prefix}_diagrams.json",
        "doc_md": data_dir / f"{version_prefix}_doc.md",
        
        # Fichiers d'évaluation
        "parsing_eval": eval_dir / f"{version_prefix}_parsing_eval.json",
        "summary_eval": eval_dir / f"{version_prefix}_summary_eval.json",
        "glossary_eval": eval_dir / f"{version_prefix}_glossary_eval.json",
        "diagram_eval": eval_dir / f"{version_prefix}_diagram_eval.json",
        "doc_eval": eval_dir / f"{version_prefix}_doc_eval.json",
        "layout_eval": eval_dir / f"{version_prefix}_layout_eval.json",
        
        # PDF Final spécifique à cette version
        "final_pdf": pdf_dir / f"{version_prefix}.pdf",
        "diagrams_dir": diagrams_dir,
    }
# from pathlib import Path
# from typing import Dict


# def get_project_prefix(file_path: str) -> str:
#     """
#     Génère dynamiquement le préfixe pour le nommage des fichiers de sortie.
    
#     Exemples :
#     - specs/constitution.md                         -> "constitution"
#     - specs/nom_projet/spec.md                      -> "nom_projet"
#     - specs/nom_projet/requirements.md              -> "nom_projet_requirements"
#     - specs/nom_projet/checklist/requirements.md  -> "nom_projet_requirements"
#     """
#     path = Path(file_path).resolve()
#     parts = path.parts

#     if "specs" in parts:
#         specs_index = parts.index("specs")
#         sub_parts = parts[specs_index + 1:]  # Éléments situés APRÈS le dossier specs/
        
#         # 1. CAS : Fichier directement sous specs/ (ex: specs/constitution.md)
#         if len(sub_parts) == 1:
#             return path.stem

#         # 2. CAS : Fichier dans un sous-dossier (ex: specs/nom_projet/...)
#         project_folder = sub_parts[0]
        
#         # Si c'est la spec principale ou un template, le préfixe est juste le nom du projet
#         if path.stem in ["spec", "template"]:
#             return project_folder
        
#         # Pour les autres fichiers (ex: requirements.md), on combine : nomprojet_requirements
#         return f"{project_folder}_{path.stem}"

#     return path.stem


# def build_pipeline_paths(file_path: str) -> Dict[str, Path]:
#     """
#     Génère l'ensemble des chemins absolus de sortie directement sous StageTalan/outputs/
#     """
#     prefix = get_project_prefix(file_path)
    
#     current_file = Path(__file__).resolve()
#     # 🎯 Récupère la racine du projet (StageTalan/)
#     project_root = current_file.parents[3] if "backend" in current_file.parts else current_file.parents[2]
#     outputs_dir = project_root / "outputs"

#     paths = {
#         "prefix": prefix,
#         "base_output_dir": outputs_dir,
#         "data_dir": outputs_dir / "data",
#         "documents_dir": outputs_dir / "documents",
#         "evaluations_dir": outputs_dir / "evaluations",
#         "diagrams_dir": outputs_dir / "data" / "diagrams",
        
#         # Fichiers cibles
#         "parsed_json": outputs_dir / "data" / f"{prefix}_parsed.json",
#         "parsing_eval": outputs_dir / "evaluations" / f"{prefix}_parsing_eval.json",
#         "summary_json": outputs_dir / "data" / f"{prefix}_summary.json",
#         "summary_eval": outputs_dir / "evaluations" / f"{prefix}_summary_eval.json",
#         "glossary_json": outputs_dir / "data" / f"{prefix}_glossary.json",
#         "glossary_eval": outputs_dir / "evaluations" / f"{prefix}_glossary_eval.json",
#         "diagrams_json": outputs_dir / "data" / f"{prefix}_diagrams.json",
#         "diagram_eval": outputs_dir / "evaluations" / f"{prefix}_diagram_eval.json",
#         "doc_md": outputs_dir / "documents" / f"{prefix}_doc.md",
#         "doc_eval": outputs_dir / "evaluations" / f"{prefix}_doc_eval.json",
#         "final_pdf": outputs_dir / "documents" / f"{prefix}_spec.pdf",
#         "layout_eval": outputs_dir / "evaluations" / f"{prefix}_layout_eval.json",
#     }

#     # Création automatique des dossiers de destination sous StageTalan/outputs/
#     for folder in [paths["data_dir"], paths["documents_dir"], paths["evaluations_dir"], paths["diagrams_dir"]]:
#         folder.mkdir(parents=True, exist_ok=True)

#     return paths
# from pathlib import Path
# from typing import Dict

# def get_project_prefix(file_path: str) -> str:
#     path = Path(file_path).resolve()
#     parts = path.parts

#     if "specs" in parts:
#         specs_index = parts.index("specs")
#         if specs_index + 1 < len(parts):
#             folder_name = parts[specs_index + 1]
#             # Si le fichier n'est pas spec.md (ex: requirements.md), on ajoute son nom au préfixe
#             if path.stem not in ["spec", "template"]:
#                 return f"{folder_name}_{path.stem}"
#             return folder_name

#     return path.stem

# def build_pipeline_paths(file_path: str) -> Dict[str, Path]:
#     """
#     Génère l'ensemble des chemins absolus de sortie directement sous StageTalan/outputs/
#     """
#     prefix = get_project_prefix(file_path)
    
#     current_file = Path(__file__).resolve()
    
#     # 🎯 FIX : parents[3] cible la racine du projet (StageTalan/)
#     # (StageTalan/backend/app/utils/path_builder.py -> StageTalan/)
#     project_root = current_file.parents[3]
#     outputs_dir = project_root / "outputs"

#     paths = {
#         "prefix": prefix,
#         "base_output_dir": outputs_dir,
#         "data_dir": outputs_dir / "data",
#         "documents_dir": outputs_dir / "documents",
#         "evaluations_dir": outputs_dir / "evaluations",
#         "diagrams_dir": outputs_dir / "data" / "diagrams",
        
#         # Fichiers cibles
#         "parsed_json": outputs_dir / "data" / f"{prefix}_parsed.json",
#         "parsing_eval": outputs_dir / "evaluations" / f"{prefix}_parsing_eval.json",
#         "summary_json": outputs_dir / "data" / f"{prefix}_summary.json",
#         "summary_eval": outputs_dir / "evaluations" / f"{prefix}_summary_eval.json",
#         "glossary_json": outputs_dir / "evaluations" / f"{prefix}_glossary.json",
#         "glossary_eval": outputs_dir / "evaluations" / f"{prefix}_glossary_eval.json",
#         "diagrams_json": outputs_dir / "data" / f"{prefix}_diagrams.json",
#         "diagram_eval": outputs_dir / "evaluations" / f"{prefix}_diagram_eval.json",
#         "doc_md": outputs_dir / "documents" / f"{prefix}_doc.md",
#         "doc_eval": outputs_dir / "evaluations" / f"{prefix}_doc_eval.json",
#         "final_pdf": outputs_dir / "documents" / f"{prefix}_spec.pdf",
#         "layout_eval": outputs_dir / "evaluations" / f"{prefix}_layout_eval.json",
#     }

#     # Création automatique des dossiers de destination sous StageTalan/outputs/
#     for folder in [paths["data_dir"], paths["documents_dir"], paths["evaluations_dir"], paths["diagrams_dir"]]:
#         folder.mkdir(parents=True, exist_ok=True)

#     return paths
