# app/schemas/document_writer_schema.py

from pydantic import BaseModel, Field
from typing import List, Dict
from enum import Enum


class DocumentSection(str, Enum):
    EXECUTIVE_SUMMARY = "executive_summary"
    TECHNICAL_STACK = "technical_stack"
    PROJECT_OVERVIEW = "project_overview"
    GLOSSARY = "glossary"
    DIAGRAMS = "diagrams"
    REQUIREMENTS = "requirements"
    STRUCTURAL_GAPS = "structural_gaps"
    OPEN_QUESTIONS = "open_questions"


class DocumentWriterOutput(BaseModel):
    """
    Modèle de validation principal pour la sortie du Document Writer Agent.
    Produit un document Markdown unifié et cohérent à partir des sorties des agents parallèles.
    """
    title: str = Field(
        ...,
        description="Titre principal du document généré, extrait de project_info.project_name."
    )
    markdown_content: str = Field(
        ...,
        description="Le document Markdown complet et cohérent, prêt pour le rendu."
    )
    sections_included: List[str] = Field(
        default_factory=list,
        description="Liste ordonnée des sections effectivement incluses dans le document."
    )
    sources_used: Dict[str, bool] = Field(
        default_factory=dict,
        description="Dictionnaire traçant quelles sources agent ont été intégrées (summary, glossary, diagram, parsing)."
    )
    diagram_count: int = Field(
        default=0,
        description="Nombre de diagrammes Mermaid intégrés dans le document."
    )
    glossary_term_count: int = Field(
        default=0,
        description="Nombre de termes du glossaire intégrés dans le document."
    )
    word_count: int = Field(
        default=0,
        description="Nombre approximatif de mots du document Markdown généré."
    )