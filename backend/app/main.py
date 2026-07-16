# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
import os

# Création automatique du dossier de stockage des PDF
os.makedirs(settings.PDF_STORAGE_DIR, exist_ok=True)

app = FastAPI(title="Spec Kit Extension - AgentDocx API")

# Configuration CORS pour le futur Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre en production (ex: ["http://localhost:4200"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "AgentDocx API is running"}