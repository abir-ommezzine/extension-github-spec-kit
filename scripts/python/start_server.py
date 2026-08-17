import os
import sys
from pathlib import Path

# 1. Configurer l'encodage et l'affichage immédiat des logs (Windows)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True, encoding='utf-8')

# 2. LOCALISATION ET NAVIGATION DEPUIS StageTalan
CURRENT_FILE = Path(__file__).resolve() # .../StageTalan/agentdocx-speckit/scripts/python/start_server.py
SCRIPT_DIR = CURRENT_FILE.parent        # .../scripts/python
RACINE_DIR = CURRENT_FILE.parents[3] # .../StageTalan
AGENTDOCX_DIR = CURRENT_FILE.parents[2]   # .../agentdocx-speckit

# 🎯 Support de la variable d'environnement SPECKIT_WORKSPACE (définie par l'extension VS Code)
SPECKIT_WORKSPACE = os.environ.get("SPECKIT_WORKSPACE")
if SPECKIT_WORKSPACE:
    RACINE_DIR = Path(SPECKIT_WORKSPACE)
    print(f"[VERIF] Workspace depuis extension VS Code : {RACINE_DIR}", flush=True)

print(f"[VERIF] Dossier StageTalan : {RACINE_DIR}", flush=True)

# Détection stricte : backend situé sous StageTalan (ou secours sous agentdocx-speckit)
if (RACINE_DIR / "backend" / "app").exists():
    TARGET_BACKEND = RACINE_DIR / "backend"
    print(f"[VERIF OK] Dossier 'app' trouvé sous StageTalan : {TARGET_BACKEND / 'app'}", flush=True)
elif (AGENTDOCX_DIR / "backend" / "app").exists():
    TARGET_BACKEND = AGENTDOCX_DIR / "backend"
    print(f"[VERIF OK] Dossier 'app' trouvé sous agentdocx-speckit : {TARGET_BACKEND / 'app'}", flush=True)
else:
    # Recherche ascendante globale par sécurité
    TARGET_BACKEND = None
    for p in CURRENT_FILE.parents:
        if (p / "backend" / "app").exists():
            TARGET_BACKEND = p / "backend"
            print(f"[VERIF OK] Recherche ascendante trouve : {TARGET_BACKEND}", flush=True)
            break

if not TARGET_BACKEND:
    print(f"[ERREUR CRITIQUE] Impossible de localiser le dossier backend sous {RACINE_DIR}", flush=True)
    sys.exit(1)

str_backend_dir = str(TARGET_BACKEND)
str_script_dir = str(SCRIPT_DIR)

# Force l'injection du dossier StageTalan/backend dans sys.path[0]
if str_backend_dir in sys.path:
    sys.path.remove(str_backend_dir)
sys.path.insert(0, str_backend_dir)

if str_script_dir not in sys.path:
    sys.path.insert(0, str_script_dir)

# Variables d'environnement pour Uvicorn et processus enfants Windows
os.environ["PYTHONPATH"] = str_backend_dir + os.pathsep + str_script_dir + os.pathsep + os.environ.get("PYTHONPATH", "")
os.chdir(str_backend_dir)

print(f"[StartServer] sys.path[0] pointé sur : {sys.path[0]}", flush=True)

# 3. DEMARRAGE UVICORN
#
# IMPORTANT : on lance directement l'application réelle définie dans
# app/main.py (app.main:app). Cette application inclut TOUS les routers,
# y compris tickets.router (endpoints /api/v1/tickets, /ingest, /progress,
# /sync-current-task, ...) nécessaires au tableau Kanban.
#
# Une ancienne version de ce script construisait sa propre instance FastAPI
# minimaliste ici (uniquement pipeline.router), ce qui faisait que le Kanban
# recevait des 404 quel que soit l'état réel du code backend. Ne PAS
# recréer d'instance FastAPI locale dans ce fichier : app.main est la seule
# source de vérité pour les routes exposées par le serveur.
if __name__ == "__main__":
    import uvicorn

    print(f"[StartServer] Démarrage du serveur Uvicorn via app.main:app...", flush=True)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        app_dir=str_backend_dir,
        reload_dirs=[str_backend_dir, str_script_dir]
    )
