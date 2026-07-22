# app/graph/workflow.py
from langgraph.graph import StateGraph, START, END
from app.graph.state import GraphState
from app.graph.nodes import (
    parsing_node, 
    summary_node, 
    glossary_node, 
    diagram_node,
    document_writer_node
)

def create_pipeline_workflow():
    """
    Workflow SEQUENTIEL pour respecter les rate limits Groq free tier (12K TPM).
    
    START -> Parsing -> Summary -> Glossary -> Diagram -> Document Writer -> END
    
    Chaque agent recoit les donnees du state partage:
    - Summary/Glossary/Diagram: lisent parsed_json_dict et parsed_doc
    - Document Writer: lit tous les outputs (summary_doc, glossary_doc, diagram_doc, parsed_doc)
    """
    workflow = StateGraph(GraphState)
    
    workflow.add_node("parsing_agent", parsing_node)
    workflow.add_node("summary_agent", summary_node)
    workflow.add_node("glossary_agent", glossary_node)
    workflow.add_node("diagram_agent", diagram_node)
    workflow.add_node("document_writer", document_writer_node)
    
    # Sequential chain
    workflow.add_edge(START, "parsing_agent")
    workflow.add_edge("parsing_agent", "summary_agent")
    workflow.add_edge("summary_agent", "glossary_agent")
    workflow.add_edge("glossary_agent", "diagram_agent")
    workflow.add_edge("diagram_agent", "document_writer")
    workflow.add_edge("document_writer", END)
    
    return workflow.compile()