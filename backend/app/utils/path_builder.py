from pathlib import Path
from typing import Dict


def get_project_prefix(file_path: str) -> str:
    """
    Génère dynamiquement le préfixe pour le nommage des fichiers de sortie.
    
    Exemples :
    - specs/constitution.md                         -> "constitution"
    - specs/nom_projet/spec.md                      -> "nom_projet"
    - specs/nom_projet/requirements.md              -> "nom_projet_requirements"
    - specs/nom_projet/checklist/requirements.md  -> "nom_projet_requirements"
    """
    path = Path(file_path).resolve()
    parts = path.parts

    if "specs" in parts:
        specs_index = parts.index("specs")
        sub_parts = parts[specs_index + 1:]  # Éléments situés APRÈS le dossier specs/
        
        # 1. CAS : Fichier directement sous specs/ (ex: specs/constitution.md)
        if len(sub_parts) == 1:
            return path.stem

        # 2. CAS : Fichier dans un sous-dossier (ex: specs/nom_projet/...)
        project_folder = sub_parts[0]
        
        # Si c'est la spec principale ou un template, le préfixe est juste le nom du projet
        if path.stem in ["spec", "template"]:
            return project_folder
        
        # Pour les autres fichiers (ex: requirements.md), on combine : nomprojet_requirements
        return f"{project_folder}_{path.stem}"

    return path.stem


def build_pipeline_paths(file_path: str) -> Dict[str, Path]:
    """
    Génère l'ensemble des chemins absolus de sortie directement sous StageTalan/outputs/
    """
    prefix = get_project_prefix(file_path)
    
    current_file = Path(__file__).resolve()
    # 🎯 Récupère la racine du projet (StageTalan/)
    project_root = current_file.parents[3] if "backend" in current_file.parts else current_file.parents[2]
    outputs_dir = project_root / "outputs"

    paths = {
        "prefix": prefix,
        "base_output_dir": outputs_dir,
        "data_dir": outputs_dir / "data",
        "documents_dir": outputs_dir / "documents",
        "evaluations_dir": outputs_dir / "evaluations",
        "diagrams_dir": outputs_dir / "data" / "diagrams",
        
        # Fichiers cibles
        "parsed_json": outputs_dir / "data" / f"{prefix}_parsed.json",
        "parsing_eval": outputs_dir / "evaluations" / f"{prefix}_parsing_eval.json",
        "summary_json": outputs_dir / "data" / f"{prefix}_summary.json",
        "summary_eval": outputs_dir / "evaluations" / f"{prefix}_summary_eval.json",
        "glossary_json": outputs_dir / "data" / f"{prefix}_glossary.json",
        "glossary_eval": outputs_dir / "evaluations" / f"{prefix}_glossary_eval.json",
        "diagrams_json": outputs_dir / "data" / f"{prefix}_diagrams.json",
        "diagram_eval": outputs_dir / "evaluations" / f"{prefix}_diagram_eval.json",
        "doc_md": outputs_dir / "documents" / f"{prefix}_doc.md",
        "doc_eval": outputs_dir / "evaluations" / f"{prefix}_doc_eval.json",
        "final_pdf": outputs_dir / "documents" / f"{prefix}_spec.pdf",
        "layout_eval": outputs_dir / "evaluations" / f"{prefix}_layout_eval.json",
    }

    # Création automatique des dossiers de destination sous StageTalan/outputs/
    for folder in [paths["data_dir"], paths["documents_dir"], paths["evaluations_dir"], paths["diagrams_dir"]]:
        folder.mkdir(parents=True, exist_ok=True)

    return paths
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
