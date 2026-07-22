from langgraph.graph import StateGraph, START, END
from app.graph.state import GraphState
from app.graph.nodes import (
    parsing_node, 
    summary_node, 
    glossary_node, 
    diagram_node,
    doc_writer_node
)

def create_pipeline_workflow():
    """
    Assemble le workflow LangGraph avec trifurcation parallèle et convergence finale.
    
                 [START]
                    │
              [parsing_agent]
                ┌───┼───┐  (Trifurcation parallèle)
                ▼   ▼   ▼
          [summary] [glossary] [diagram]
                └───┼───┘  (Convergence)
                    ▼
            [doc_writer_agent]
                    │
                  [END]
    """
    workflow = StateGraph(GraphState)
    
    # 1. Ajout des Noeuds
    workflow.add_node("parsing_agent", parsing_node)
    workflow.add_node("summary_agent", summary_node)
    workflow.add_node("glossary_agent", glossary_node)
    workflow.add_node("diagram_agent", diagram_node)
    workflow.add_node("doc_writer_agent", doc_writer_node)
    
    # 2. Edge initial
    workflow.add_edge(START, "parsing_agent")
    
    # 3. Parallélisation : 'parsing_agent' pointe vers summary, glossary ET diagram
    workflow.add_edge("parsing_agent", "summary_agent")
    workflow.add_edge("parsing_agent", "glossary_agent")
    workflow.add_edge("parsing_agent", "diagram_agent")
    
    # 4. Convergence : Les 3 agents parallèles convergent vers 'doc_writer_agent'
    workflow.add_edge("summary_agent", "doc_writer_agent")
    workflow.add_edge("glossary_agent", "doc_writer_agent")
    workflow.add_edge("diagram_agent", "doc_writer_agent")
    
    # 5. Fin
    workflow.add_edge("doc_writer_agent", END)
    
    return workflow.compile()
# # app/graph/workflow.py
# from langgraph.graph import StateGraph, START, END
# from app.graph.state import GraphState
# from app.graph.nodes import parsing_node, summary_node, glossary_node, diagram_node

# def create_pipeline_workflow():
#     """
#     Assemble le workflow LangGraph avec trifurcation parallèle.
    
#                  [START]
#                     │
#               [parsing_agent]
#                 ┌───┼───┐  (Trifurcation parallèle)
#                 ▼   ▼   ▼
#           [summary] [glossary] [diagram]
#                 └───┼───┘  (Convergence)
#                     ▼
#                   [END]
#     """
#     workflow = StateGraph(GraphState)
    
#     # 1. Ajout des Noeuds
#     workflow.add_node("parsing_agent", parsing_node)
#     workflow.add_node("summary_agent", summary_node)
#     workflow.add_node("glossary_agent", glossary_node)
#     workflow.add_node("diagram_agent", diagram_node)
    
#     # 2. Edge initial
#     workflow.add_edge(START, "parsing_agent")
    
#     # 3. Parallélisation : 'parsing_agent' pointe vers summary, glossary ET diagram
#     workflow.add_edge("parsing_agent", "summary_agent")
#     workflow.add_edge("parsing_agent", "glossary_agent")
#     workflow.add_edge("parsing_agent", "diagram_agent")
    
#     # 4. Convergence vers la fin
#     workflow.add_edge("summary_agent", END)
#     workflow.add_edge("glossary_agent", END)
#     workflow.add_edge("diagram_agent", END)
    
#     return workflow.compile()
