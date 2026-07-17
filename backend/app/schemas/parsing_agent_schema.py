# app/schemas/parser.py
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, model_validator

class DocumentType(str, Enum):
    spec = "spec"
    plan = "plan"
    task = "task"
    constitution = "constitution"

class SectionOutput(BaseModel):
    title: str
    level: int
    raw_content: str
    mapped_to_template_field: Optional[str] = None

class StructuralGap(BaseModel):
    missing_section: str
    priority: str
    remediation_advice: str

class ParsingAgentOutput(BaseModel):
    parsing_rationale: str
    project_info: dict
    doc_type: DocumentType
    sections: List[SectionOutput]
    structural_gaps: List[StructuralGap]
    open_questions: List[str]

    @model_validator(mode='after')
    def verify_no_contradictions(self) -> 'ParsingAgentOutput':
        # 1. Récupérer tous les champs réellement mappés (non nuls)
        mapped_fields = {
            s.mapped_to_template_field 
            for s in self.sections 
            if s.mapped_to_template_field is not None
        }
        
        # 2. Récupérer toutes les sections déclarées comme "manquantes"
        gap_fields = {g.missing_section for g in self.structural_gaps}
        
        # 3. Trouver l'intersection (les contradictions)
        contradictions = mapped_fields.intersection(gap_fields)
        
        if contradictions:
            raise ValueError(
                f"Contradiction logique détectée : Les sections suivantes sont à la fois "
                f"mappées ET déclarées comme manquantes (structural_gaps) : {list(contradictions)}. "
                f"Si une section existe, elle ne doit pas être dans 'structural_gaps'."
            )
        return self