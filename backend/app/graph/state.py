# app/graph/state.py
from typing import TypedDict, Dict, Any, Optional
from app.schemas.parsing_agent_schema import ParsingAgentOutput
from app.schemas.summary_agent_schema import SummaryOutputModel
from app.schemas.glossary_agent_schema import GlossaryOutputModel

class GraphState(TypedDict):
    # Entrées initiales du système
    file_name: str
    file_content: str
    
    # 1. Parsing Agent : Résultats & Métriques
    parsed_json_dict: Optional[Dict[str, Any]]
    parsed_doc: Optional[ParsingAgentOutput]
    parsing_metrics: Optional[Dict[str, Any]]
    
    # 2. Summary Agent : Résultats & Métriques (Parallèle A)
    summary_doc: Optional[SummaryOutputModel]
    summary_metrics: Optional[Dict[str, Any]]
    
    # 3. Glossary Agent : Résultats & Métriques (Parallèle B)
    glossary_doc: Optional[GlossaryOutputModel]
    glossary_metrics: Optional[Dict[str, Any]]

    # 4. Diagram Agent : Résultats & Métriques (Parallèle C)
    diagram_doc: Optional[Any]
    diagram_metrics: Optional[Dict[str, Any]]
    diagram_pdf_path: Optional[str]
# # app/graph/state.py
# from typing import TypedDict, Dict, Any, Optional
# from app.schemas.parsing_agent_schema import ParsingAgentOutput
# from app.schemas.summary_agent_schema import SummaryOutputModel
# from app.schemas.glossary_agent_schema import GlossaryOutputModel

# class GraphState(TypedDict):
#     # Entrées initiales du système
#     file_name: str
#     file_content: str
    
#     # 1. Parsing Agent : Résultats & Métriques
#     parsed_json_dict: Optional[Dict[str, Any]]
#     parsed_doc: Optional[ParsingAgentOutput]
#     parsing_metrics: Optional[Dict[str, Any]]
    
#     # 2. Summary Agent : Résultats & Métriques (Parallèle A)
#     summary_doc: Optional[SummaryOutputModel]
#     summary_metrics: Optional[Dict[str, Any]]
    
#     # 3. Glossary Agent : Résultats & Métriques (Parallèle B)
#     glossary_doc: Optional[GlossaryOutputModel]
#     glossary_metrics: Optional[Dict[str, Any]]