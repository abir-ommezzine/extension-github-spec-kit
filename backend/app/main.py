import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.graph.workflow import create_pipeline_workflow

# 1. Création des dossiers nécessaires
os.makedirs(settings.PDF_STORAGE_DIR, exist_ok=True)

# 2. Initialisation de FastAPI
app = FastAPI(
    title="Spec Kit Extension - AgentDocx API",
    version="1.0.0",
    description="API FastAPI d'orchestration Multi-Agents LangGraph pour Spec Kit"
)

# 3. Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre si besoin (ex: ["http://localhost:4200"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Modèles Pydantic pour les requêtes
class PipelineRequest(BaseModel):
    file_path: str = Field(
        ..., 
        description="Chemin absolu du fichier Markdown (ex: /path/to/specs/doc-pipeline-001/template.md)"
    )

# 5. Endpoints de santé et d'information
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "SpecKit Extension API is running!", 
        "docs_url": "/docs"
    }

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}

# 6. Endpoint principal : Exécution du Pipeline LangGraph
@app.post("/api/v1/pipeline/run", tags=["Pipeline"])
async def run_pipeline(payload: PipelineRequest):
    """
    Déclenche le Pipeline Multi-Agents sur le fichier Markdown spécifié par Spec Kit.
    """
    target_path = Path(payload.file_path)
    
    # Vérification de l'existence du fichier
    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fichier introuvable sur le serveur : {payload.file_path}"
        )
        
    try:
        # Lecture du fichier Markdown
        with open(target_path, "r", encoding="utf-8") as f:
            file_content = f.read()

        initial_state = {
            "file_name": target_path.name,
            "file_content": file_content
        }

        # Lancement de l'orchestration LangGraph
        pipeline = create_pipeline_workflow()
        final_state = pipeline.invoke(initial_state)

        return {
            "status": "success",
            "message": "Pipeline exécuté avec succès",
            "data": final_state
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de l'exécution du pipeline : {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)