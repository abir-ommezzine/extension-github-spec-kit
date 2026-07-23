# app/schemas/parsing_agent_schema.py
from enum import Enum
from typing import List, Optional, Dict, Any
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

# NEW — the slim shape the LLM actually has to produce
class LLMSectionMapping(BaseModel):
    section_index: int  # index into pre_parsed_sections, not the text itself
    mapped_to_template_field: Optional[str] = None

class ParsingAgentLLMOutput(BaseModel):
    parsing_rationale: str
    project_info: dict
    doc_type: DocumentType
    section_mappings: List[LLMSectionMapping]
    elements: List[GraphElement]          # unchanged shape — already slim
    relationships: List[GraphRelationship] # unchanged shape — already slim
    structural_gaps: List[StructuralGap]   # unchanged shape — already slim
    open_questions: List[str] 
    
class ParsingAgentOutput(BaseModel):
    parsing_rationale: str
    project_info: dict
    doc_type: DocumentType
    sections: List[SectionOutput]
    elements: List[GraphElement]
    relationships: List[GraphRelationship]
    structural_gaps: List[StructuralGap]
    open_questions: List[str]

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
        valid_sections = {s.title.strip().lower() for s in self.sections}
        for el in self.elements:
            if el.source_section and el.source_section.strip().lower() not in valid_sections:
                raise ValueError(
                    f"Erreur de traçabilité : L'élément micro '{el.identifier or el.content[:20]}' "
                    f"fait référence à une section physique inexistante : '{el.source_section}'"
                )
                
        return self
# from enum import Enum
# from typing import List, Optional, Dict, Any
# from pydantic import BaseModel, model_validator

# class DocumentType(str, Enum):
#     spec = "spec"
#     plan = "plan"
#     task = "task"
#     constitution = "constitution"

# class SectionOutput(BaseModel):
#     title: str
#     level: int
#     raw_content: str
#     mapped_to_template_field: Optional[str] = None

# # --- LE MICRO-ELEMENT CORRIGÉ ET ANCRÉ ---
# class GraphElement(BaseModel):
#     type: str  # requirement, task, user_story, entity, decision, etc.
#     identifier: Optional[str] = None
#     content: str
#     # LA CORRECTION : Fait le pont direct avec le titre de la SectionOutput d'origine
#     source_section: Optional[str] = None  
#     attributes: Dict[str, Any] = {}

# class GraphRelationship(BaseModel):
#     source: str  # identifiant ou texte court de l'élément source
#     to: str      # identifiant ou texte court de l'élément cible
#     relation_type: str  # depends_on, implements, contains, relates_to

# class StructuralGap(BaseModel):
#     missing_section: str
#     priority: str
#     remediation_advice: str

# # --- LE CONTENEUR GLOBAL SÉCURISÉ ---
# class ParsingAgentOutput(BaseModel):
#     parsing_rationale: str
#     project_info: dict
#     doc_type: DocumentType
#     sections: List[SectionOutput]
#     elements: List[GraphElement]
#     relationships: List[GraphRelationship]
#     structural_gaps: List[StructuralGap]
#     open_questions: List[str]

#     @model_validator(mode='after')
#     def verify_no_contradictions(self) -> 'ParsingAgentOutput':
#         # 1. Votre garde-fou anti-contradiction (Inchangé et protecteur)
#         mapped_fields = {s.mapped_to_template_field for s in self.sections if s.mapped_to_template_field is not None}
#         gap_fields = {g.missing_section for g in self.structural_gaps}
#         contradictions = mapped_fields.intersection(gap_fields)
        
#         if contradictions:
#             raise ValueError(f"Contradiction logique détectée : Les sections suivantes sont mappées ET manquantes : {list(contradictions)}")
            
#         # 2. Nouveau garde-fou de traçabilité macro-micro
#         valid_sections = {s.title.strip().lower() for s in self.sections}
#         for el in self.elements:
#             if el.source_section and el.source_section.strip().lower() not in valid_sections:
#                 raise ValueError(f"Erreur de traçabilité : L'élément micro '{el.identifier or el.content[:20]}' fait référence à une section inexistante : '{el.source_section}'")
                
#         return self
# # app/schemas/parser.py
# from enum import Enum
# from typing import List, Optional
# from pydantic import BaseModel, model_validator

# class DocumentType(str, Enum):
#     spec = "spec"
#     plan = "plan"
#     task = "task"
#     constitution = "constitution"

# class SectionOutput(BaseModel):
#     title: str
#     level: int
#     raw_content: str
#     mapped_to_template_field: Optional[str] = None

# class StructuralGap(BaseModel):
#     missing_section: str
#     priority: str
#     remediation_advice: str

# class ParsingAgentOutput(BaseModel):
#     parsing_rationale: str
#     project_info: dict
#     doc_type: DocumentType
#     sections: List[SectionOutput]
#     structural_gaps: List[StructuralGap]
#     open_questions: List[str]

#     @model_validator(mode='after')
#     def verify_no_contradictions(self) -> 'ParsingAgentOutput':
#         # 1. Récupérer tous les champs réellement mappés (non nuls)
#         mapped_fields = {
#             s.mapped_to_template_field 
#             for s in self.sections 
#             if s.mapped_to_template_field is not None
#         }
        
#         # 2. Récupérer toutes les sections déclarées comme "manquantes"
#         gap_fields = {g.missing_section for g in self.structural_gaps}
        
#         # 3. Trouver l'intersection (les contradictions)
#         contradictions = mapped_fields.intersection(gap_fields)
        
#         if contradictions:
#             raise ValueError(
#                 f"Contradiction logique détectée : Les sections suivantes sont à la fois "
#                 f"mappées ET déclarées comme manquantes (structural_gaps) : {list(contradictions)}. "
#                 f"Si une section existe, elle ne doit pas être dans 'structural_gaps'."
#             )
#         return self