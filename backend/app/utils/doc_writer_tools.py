# app/tools/doc_writer_tools.py

import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime


def extract_markdown_toc(markdown_content: str) -> List[str]:
    """
    Extrait de manière déterministe la table des matières (TOC)
    en scannant les titres Markdown (#, ##, ###).
    """
    if not markdown_content:
        return []

    lines = markdown_content.splitlines()
    toc = []
    
    for line in lines:
        line_clean = line.strip()
        # Repère les titres H1, H2, H3
        if re.match(r"^#{1,3}\s+", line_clean):
            # Nettoie les caractères '#' pour ne garder que le texte du titre
            title = re.sub(r"^#{1,3}\s+", "", line_clean).strip()
            toc.append(title)

    return toc


def save_markdown_artifact(
    markdown_content: str, 
    project_name: str, 
    output_dir: str = "test_files/outputs/markdowns"
) -> str:
    """
    Sauvegarde le contenu Markdown généré par le Documentation Writer sur le disque.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Normalisation du nom de fichier
    safe_name = re.sub(r"[^\w\-_]", "_", project_name.lower())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{safe_name}_doc_{timestamp}.md"
    file_path = os.path.join(output_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    return os.path.abspath(file_path)


def resolve_diagram_references(
    markdown_content: str, 
    diagrams_pdf_or_images: List[str]
) -> str:
    """
    Associe ou remplace les balises de diagrammes par les références visuelles 
    des artefacts générés sur le disque par le Diagram Agent.
    """
    if not markdown_content or not diagrams_pdf_or_images:
        return markdown_content

    updated_md = markdown_content
    # Insère une note sur les artefacts visuels attachés au document
    pdf_attachment_note = "\n\n> 📄 **Attached Visual Artifact**: " + ", ".join(
        [os.path.basename(path) for path in diagrams_pdf_or_images]
    )
    
    if "## 2. Architecture Workflows" in updated_md:
        updated_md = updated_md.replace(
            "## 2. Architecture Workflows & Visual Diagrams",
            f"## 2. Architecture Workflows & Visual Diagrams{pdf_attachment_note}"
        )

    return updated_md


def compile_markdown_to_pdf(
    markdown_path: str, 
    output_pdf_dir: str = "test_files/outputs/pdfs"
) -> Optional[str]:
    """
    Moteur de rendu déterministe pour convertir le Markdown unifié en fichier PDF.
    Peut être étendu avec WeasyPrint, Typst ou Pandoc.
    """
    os.makedirs(output_pdf_dir, exist_ok=True)
    
    base_name = os.path.splitext(os.path.basename(markdown_path))[0]
    pdf_path = os.path.join(output_pdf_dir, f"{base_name}.pdf")

    # Exemple de compilation basique (à relier à votre moteur WeasyPrint/Typst existant)
    # Pour l'instant, simule/prépare le chemin cible d'exportation PDF
    return os.path.abspath(pdf_path)
# Remplacez la fonction sanitize_mermaid_blocks dans app/tools/doc_writer_tools.py par celle-ci :

def sanitize_mermaid_blocks(markdown_content: str) -> str:
    """
    Détecte et assainit les blocs ```mermaid dans le document Markdown 
    pour éviter les erreurs de syntaxe et améliorer le rendu visuel lors de l'export PDF.
    Exemple : participant API as "API (/api/v1/)" -> participant API as "API (api v1)"
    """
    if not markdown_content:
        return markdown_content

    def clean_mermaid_code(match):
        mermaid_code = match.group(1)
        # Remplace les slashs et antislashs par des espaces propres
        cleaned_code = re.sub(
            r'participant\s+(\w+)\s+as\s+"([^"]+)"',
            lambda m: f'participant {m.group(1)} as "{m.group(2).replace("/", " ").replace("\\", "").strip()}"',
            mermaid_code
        )
        return f"```mermaid\n{cleaned_code}\n```"

    pattern = r"```mermaid\s*\n(.*?)\n```"
    return re.sub(pattern, clean_mermaid_code, markdown_content, flags=re.DOTALL)
# def sanitize_mermaid_blocks(markdown_content: str) -> str:
#     """
#     Détecte et assainit les blocs ```mermaid dans le document Markdown 
#     pour éviter les erreurs de syntaxe lors du rendu PDF :
#     - Remplace les slashs et guillemets imbriqués dans les alias de participants.
#     Exemple : participant API as "API (/api/v1/)" -> participant API as "API (api v1)"
#     """
#     if not markdown_content:
#         return markdown_content

#     def clean_mermaid_code(match):
#         mermaid_code = match.group(1)
#         # Remplace les alias problématiques comme "API (/api/v1/)" par "API (api-v1)"
#         cleaned_code = re.sub(
#             r'participant\s+(\w+)\s+as\s+"([^"]+)"',
#             lambda m: f'participant {m.group(1)} as "{m.group(2).replace("/", "-").replace("\\", "")}"',
#             mermaid_code
#         )
#         return f"```mermaid\n{cleaned_code}\n```"

#     # Pattern pour cibler les blocs de code mermaid
#     pattern = r"```mermaid\s*\n(.*?)\n```"
#     return re.sub(pattern, clean_mermaid_code, markdown_content, flags=re.DOTALL)