import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base


import app.models  

# Import du router pipeline (qui contient la logique BDD & LangGraph)
from app.api.v1.endpoints import pipeline

# 1. Création automatique des tables BDD si elles n'existent pas
Base.metadata.create_all(bind=engine)

# 2. Protection création du dossier de sortie PDF
pdf_dir = getattr(settings, "PDF_STORAGE_DIR", "outputs/documents")
os.makedirs(pdf_dir, exist_ok=True)

# 3. Initialisation UNIQUE de FastAPI
app = FastAPI(
    title="Spec Kit Extension - AgentDocx API",
    version="1.0.0",
    description="API FastAPI d'orchestration Multi-Agents LangGraph pour Spec Kit"
)

# 4. Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Inclusion du Router Pipeline (Incorpore /status, /run et la BDD)
app.include_router(pipeline.router, prefix="/api/v1/pipeline", tags=["Pipeline"])


# 6. Endpoints de santé (Health Checks)
@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "SpecKit Extension API is running!", 
        "docs_url": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
# import os
# from pathlib import Path
# from fastapi import FastAPI, HTTPException, status
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field

# from app.config import settings
# from app.graph.workflow import create_pipeline_workflow
# from app.utils.path_builder import build_pipeline_paths
# from fastapi import FastAPI
# from app.database import engine, Base

# import app.models  

# Base.metadata.create_all(bind=engine)

# app = FastAPI(title="Spec-Driven Pipeline API")

# # Vos routers...
# from app.api.v1.endpoints import pipeline
# app.include_router(pipeline.router, prefix="/pipeline", tags=["Pipeline"])
# # 1. Protection création de dossier (évite un crash si PDF_STORAGE_DIR n'existe pas dans settings)
# pdf_dir = getattr(settings, "PDF_STORAGE_DIR", "outputs/documents")
# os.makedirs(pdf_dir, exist_ok=True)

# # 2. Initialisation de FastAPI
# app = FastAPI(
#     title="Spec Kit Extension - AgentDocx API",
#     version="1.0.0",
#     description="API FastAPI d'orchestration Multi-Agents LangGraph pour Spec Kit"
# )

# # 3. Configuration CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 4. État global du pipeline
# PIPELINE_STATUS = {
#     "is_running": False,
#     "current_file": None
# }

# # 5. Modèles Pydantic pour les requêtes
# class PipelineRequest(BaseModel):
#     file_path: str = Field(
#         ..., 
#         description="Chemin absolu du fichier Markdown (ex: /path/to/specs/001-feature/spec.md)"
#     )

# # 6. Endpoints de santé
# @app.get("/", tags=["Health"])
# async def root():
#     return {
#         "message": "SpecKit Extension API is running!", 
#         "docs_url": "/docs"
#     }

# @app.get("/health", tags=["Health"])
# async def health():
#     return {"status": "ok", "version": "1.0.0"}

# # 7. Endpoints du Pipeline

# @app.get("/api/v1/pipeline/status", tags=["Pipeline"])
# async def get_pipeline_status():
#     """Vérifie si le pipeline est déjà en cours d'exécution (consulté par le Watcher)."""
#     return PIPELINE_STATUS


# @app.post("/api/v1/pipeline/run", tags=["Pipeline"])
# async def run_pipeline(payload: PipelineRequest):
#     """Déclenche le Pipeline Multi-Agents LangGraph et génère les outputs à la racine StageTalan/outputs/."""
#     global PIPELINE_STATUS

#     # Protection contre les exécutions concurrentes
#     if PIPELINE_STATUS["is_running"]:
#         raise HTTPException(
#             status_code=status.HTTP_429_TOO_MANY_REQUESTS,
#             detail=f"Pipeline déjà en cours d'exécution sur : {PIPELINE_STATUS['current_file']}"
#         )

#     target_path = Path(payload.file_path)
    
#     # Vérification de l'existence du fichier
#     if not target_path.exists():
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Fichier introuvable sur le disque : {payload.file_path}"
#         )

#     # Verrouillage
#     PIPELINE_STATUS["is_running"] = True
#     PIPELINE_STATUS["current_file"] = payload.file_path

#     try:
#         # Construction des chemins de sortie vers StageTalan/outputs/
#         paths = build_pipeline_paths(payload.file_path)
#         file_content = target_path.read_text(encoding="utf-8")

#         initial_state = {
#             "file_name": payload.file_path,
#             "file_content": file_content,
#             "prefix": paths["prefix"]
#         }

#         # Lancement de l'orchestration LangGraph
#         pipeline = create_pipeline_workflow()
#         final_state = await pipeline.ainvoke(initial_state)

#         return {
#             "status": "success",
#             "message": "Pipeline exécuté avec succès",
#             "pdf_path": str(paths["final_pdf"]),
#             "data": final_state
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erreur lors de l'exécution du pipeline : {str(e)}"
#         )

#     finally:
#         # Déverrouillage systématique
#         PIPELINE_STATUS["is_running"] = False
#         PIPELINE_STATUS["current_file"] = None


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
# import os
# from pathlib import Path
# from fastapi import FastAPI, HTTPException, status
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel, Field

# from app.config import settings
# from app.graph.workflow import create_pipeline_workflow

# # 1. Création des dossiers nécessaires
# os.makedirs(settings.PDF_STORAGE_DIR, exist_ok=True)

# # 2. Initialisation de FastAPI
# app = FastAPI(
#     title="Spec Kit Extension - AgentDocx API",
#     version="1.0.0",
#     description="API FastAPI d'orchestration Multi-Agents LangGraph pour Spec Kit"
# )

# # 3. Configuration CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # À restreindre si besoin (ex: ["http://localhost:4200"])
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 4. Modèles Pydantic pour les requêtes
# class PipelineRequest(BaseModel):
#     file_path: str = Field(
#         ..., 
#         description="Chemin absolu du fichier Markdown (ex: /path/to/specs/doc-pipeline-001/template.md)"
#     )

# # 5. Endpoints de santé et d'information
# @app.get("/", tags=["Health"])
# async def root():
#     return {
#         "message": "SpecKit Extension API is running!", 
#         "docs_url": "/docs"
#     }

# @app.get("/health", tags=["Health"])
# async def health():
#     return {"status": "ok", "version": "1.0.0"}

# # 6. Endpoint principal : Exécution du Pipeline LangGraph
# @app.post("/api/v1/pipeline/run", tags=["Pipeline"])
# async def run_pipeline(payload: PipelineRequest):
#     """
#     Déclenche le Pipeline Multi-Agents sur le fichier Markdown spécifié par Spec Kit.
#     """
#     target_path = Path(payload.file_path)
    
#     # Vérification de l'existence du fichier
#     if not target_path.exists():
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"Fichier introuvable sur le serveur : {payload.file_path}"
#         )
        
#     try:
#         # Lecture du fichier Markdown
#         with open(target_path, "r", encoding="utf-8") as f:
#             file_content = f.read()

#         initial_state = {
#             "file_name": target_path.name,
#             "file_content": file_content
#         }

#         # Lancement de l'orchestration LangGraph
#         pipeline = create_pipeline_workflow()
#         final_state = pipeline.invoke(initial_state)

#         return {
#             "status": "success",
#             "message": "Pipeline exécuté avec succès",
#             "data": final_state
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erreur lors de l'exécution du pipeline : {str(e)}"
#         )

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)