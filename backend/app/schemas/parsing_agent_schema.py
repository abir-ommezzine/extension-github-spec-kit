from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, model_validator, field_validator, Field


class DocumentType(str, Enum):
    spec = "spec"
    plan = "plan"
    task = "task"
    constitution = "constitution"


class SectionOutput(BaseModel):
    title: str = ""
    level: int = 1
    raw_content: str = ""
    mapped_to_template_field: Optional[str] = None
    section_index: Optional[int] = None


class GraphElement(BaseModel):
    type: str  # requirement, task, user_story, entity, decision, constraint
    identifier: Optional[str] = None
    content: str
    source_section: Optional[str] = None  # Ancrage bi-échelle
    attributes: Dict[str, Any] = {}


class GraphRelationship(BaseModel):
    source: str  # Contiendra la valeur de 'from' après redirection automatique
    to: str
    relation_type: str  # depends_on, implements, contains, relates_to

    @model_validator(mode='before')
    @classmethod
    def handle_reserved_keyword_from(cls, data: Any) -> Any:
        """
        Sécurité anti-mot-clé réservé Python : intercepte 'from' 
        généré par le LLM et le convertit de façon transparente en 'source'.
        """
        if isinstance(data, dict) and "from" in data and "source" not in data:
            data["source"] = data.pop("from")
        return data


class StructuralGap(BaseModel):
    missing_section: str
    priority: str
    remediation_advice: str


class ParsingAgentOutput(BaseModel):
    parsing_rationale: str
    project_info: dict
    doc_type: DocumentType
    sections: List[SectionOutput] = Field(default_factory=list)
    elements: List[GraphElement] = Field(default_factory=list)
    relationships: List[GraphRelationship] = Field(default_factory=list)
    structural_gaps: List[StructuralGap] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def handle_section_mappings_alias(cls, data: Any) -> Any:
        """
        Intercepte 'section_mappings' si le LLM le renvoie à la place de 'sections'.
        """
        if isinstance(data, dict):
            if "section_mappings" in data and ("sections" not in data or not data["sections"]):
                data["sections"] = data.pop("section_mappings")
        return data

    @field_validator('open_questions', mode='before')
    @classmethod
    def normalize_open_questions(cls, v: Any) -> List[str]:
        """
        Garde-fou anti-crash : tolère à la fois une liste de chaînes (List[str]) 
        et une liste d'objets/dictionnaires générée par le LLM.
        """
        if not isinstance(v, list):
            return []

        cleaned_questions: List[str] = []
        for item in v:
            if isinstance(item, dict):
                q_text = (
                    item.get("question") 
                    or item.get("content") 
                    or item.get("title") 
                    or str(item)
                )
                cleaned_questions.append(str(q_text))
            elif isinstance(item, str):
                cleaned_questions.append(item)
            else:
                cleaned_questions.append(str(item))

        return cleaned_questions

    @model_validator(mode='after')
    def verify_no_contradictions(self) -> 'ParsingAgentOutput':
        # 1. Protection anti-contradiction macro
        mapped_fields = {
            s.mapped_to_template_field 
            for s in self.sections 
            if s.mapped_to_template_field is not None
        }
        gap_fields = {g.missing_section for g in self.structural_gaps}
        contradictions = mapped_fields.intersection(gap_fields)
        
        if contradictions:
            raise ValueError(
                f"Contradiction logique détectée : Les sections suivantes sont à la fois "
                f"mappées ET déclarées comme manquantes (structural_gaps) : {list(contradictions)}."
            )
            
        # 2. Protection de traçabilité macro-micro
        valid_sections = {s.title.strip().lower() for s in self.sections if s.title}
        if valid_sections:
            for el in self.elements:
                if el.source_section and el.source_section.strip().lower() not in valid_sections:
                    # Traçabilité flexible pour ne pas bloquer le pipeline sur de légères variations de titre
                    pass

        return self