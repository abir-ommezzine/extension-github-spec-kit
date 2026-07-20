from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class TermCategory(str, Enum):
    BUSINESS_DOMAIN = "BUSINESS_DOMAIN"   # Concepts métiers, entités (ex: Expense, Instructor, Enrollment)
    TECHNICAL_STACK = "TECHNICAL_STACK"   # Outils, protocoles, frameworks (ex: FastAPI, LocalStorage, JWT)

class DiscoveryType(str, Enum):
    EXPLICIT = "EXPLICIT"   # Terme ou techno nommés directement dans les sections de spécifications
    IMPLICIT = "IMPLICIT"   # Déduit du contexte, du code ou d'une règle (ex: ISO 8601, State Machine, CORS)

class GlossaryItem(BaseModel):
    term: str = Field(
        ..., 
        description="The exact technical token, domain entity, or standard identified in the text."
    )
    category: TermCategory = Field(
        ..., 
        description="Classification to position the term in the software layers."
    )
    discovery: DiscoveryType = Field(
        ..., 
        description="Identifies if the technology/concept is explicitly stated or implicitly required by the context."
    )
    contextual_anchor: str = Field(
        ..., 
        description="The specific context, rule, or section where this term impacts the system architecture."
    )
    project_definition: str = Field(
        ..., 
        description="High-density definition locked strictly to the project rules. Do NOT provide a generic Wikipedia definition."
    )

class GlossaryOutputModel(BaseModel):
    project_name: str = Field(
        ..., 
        description="The formal or inferred identity of the project."
    )
    items: List[GlossaryItem] = Field(
        ..., 
        description="List of unique domain terms and explicit/implicit technologies that anchor the project."
    )