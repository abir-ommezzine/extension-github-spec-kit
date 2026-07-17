from pydantic import BaseModel, Field
from typing import List

class TechnicalStackSchema(BaseModel):
    """
    Sous-schéma détaillant la pile technique et ses contraintes physiques.
    """
    languages_and_frameworks: List[str] = Field(
        ...,
        description=(
            "Liste ordonnée des langages, frameworks, bibliothèques et outils tiers "
            "explicitement mentionnés (ex: FastAPI, PostgreSQL, LocalStorage, Resend)."
        )
    )
    architectural_constraints: List[str] = Field(
        ...,
        description=(
            "Contraintes physiques et décisions architecturales fortes imposées par le projet "
            "(ex: absence d'authentification, architecture asynchrone, persistance locale pure, etc.)."
        )
    )

class SummaryOutputModel(BaseModel):
    """
    Modèle de validation principal pour la sortie du Summary Agent.
    Garantit l'alignement strict avec summary_spec.json.
    """
    executive_brief: str = Field(
        ...,
        description=(
            "Synthèse macro de l'intention de l'application et de sa valeur métier. "
            "Doit être rédigée sur un ton technique et assertif en 3 ou 4 phrases maximum. "
            "Aucune hallucination ou extrapolation fonctionnelle n'est autorisée."
        )
    )
    technical_stack: TechnicalStackSchema = Field(
        ...,
        description="Détails de la pile technologique et des contraintes d'implémentation."
    )
    maturity_assessment: str = Field(
        ...,
        description=(
            "Évaluation narrative et objective de la viabilité du document d'architecture. "
            "Doit obligatoirement qualifier le projet (ex: PRÊT, IMMATURE, ou CRITIQUE) "
            "en s'appuyant sur le nombre de 'structural_gaps' et d''open_questions' du projet."
        )
    )
    critical_dependencies: List[str] = Field(
        ...,
        description=(
            "Liste des dépendances bloquantes, des intégrations externes critiques, ou "
            "des prérequis de configuration (ex: variables d'environnement pour clés d'API, limites physiques du LocalStorage)."
        )
    )