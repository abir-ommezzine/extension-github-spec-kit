from typing import TypedDict, Dict, Any, Optional
from uuid import UUID
from app.schemas.parsing_agent_schema import ParsingAgentOutput
from app.schemas.summary_agent_schema import SummaryOutputModel
from app.schemas.glossary_agent_schema import GlossaryOutputModel
from app.schemas.document_writer_schema import DocumentWriterOutput

class GraphState(TypedDict):
    # Inputs
    file_name: str
    file_content: str
    
    # DB tracking
    pipeline_run_id: Optional[UUID]
    
    # 1. Parsing Agent
    parsed_json_dict: Optional[Dict[str, Any]]
    parsed_doc: Optional[ParsingAgentOutput]
    parsing_metrics: Optional[Dict[str, Any]]
    
    # 2. Summary Agent (Parallel A)
    summary_doc: Optional[SummaryOutputModel]
    summary_metrics: Optional[Dict[str, Any]]
    
    # 3. Glossary Agent (Parallel B)
    glossary_doc: Optional[GlossaryOutputModel]
    glossary_metrics: Optional[Dict[str, Any]]

    # 4. Diagram Agent (Parallel C)
    diagram_doc: Optional[Any]
    diagram_metrics: Optional[Dict[str, Any]]
    diagram_pdf_path: Optional[str]

    # 5. Doc Writer Agent
    doc_writer_doc: Optional[Any]
    doc_writer_metrics: Optional[Dict[str, Any]]
    doc_writer_md_path: Optional[str]
    doc_writer_eval_path: Optional[str]

    # 6. Layout Agent
    layout_doc: Optional[Any]
    layout_metrics: Optional[Dict[str, Any]]
    layout_pdf_path: Optional[str]
    layout_eval_path: Optional[str]