#!/usr/bin/env python3
"""
FastAPI Server Launcher for AgentDocx SpecKit
Reads config from .vscode/settings.json
"""
import json
import os
import socket
import sys
from pathlib import Path

def load_vscode_config():
    """Load agentdocx-speckit config from .vscode/settings.json"""
    workspace = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SPECKIT_WORKSPACE")
    print(f"[SERVER] Workspace: {workspace}", flush=True)
    if workspace:
        settings_path = Path(workspace) / ".vscode" / "settings.json"
    else:
        settings_path = Path.cwd() / ".vscode" / "settings.json"
    print(f"[SERVER] Looking for config at: {settings_path}", flush=True)
    print(f"[SERVER] Config exists: {settings_path.exists()}", flush=True)
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
                return settings.get("agentdocx-speckit", {})
        except Exception as e:
            print(f"[SERVER] Warning: Could not parse .vscode/settings.json: {e}")
    return {}

def find_available_port(host, preferred_port, max_attempts=100):
    """
    Try to bind the preferred port; if busy, scan upwards for the first free port.
    Returns the chosen port.
    """
    for port in range(preferred_port, preferred_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"No free port found between {preferred_port} and {preferred_port + max_attempts - 1}"
    )

def backend_already_running(host, port, timeout=1):
    """Return True if a backend already responds on the given port."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://{host}:{port}/health", timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False

def main():
    config = load_vscode_config()
    
    # Get config with defaults (apiPort matches the extension schema & watcher)
    host = config.get("host", "127.0.0.1")
    preferred_port = config.get("apiPort", config.get("port", 8000))
    reload = config.get("reload", True)
    backend_path = config.get("backendPath", "backend")
    
    # If a backend already runs on the preferred port, do not start a second one.
    if backend_already_running(host, preferred_port):
        print(f"[SERVER] Backend already running on {host}:{preferred_port}. Skipping server start.", flush=True)
        sys.exit(0)
    
    # Add backend to Python path
    backend_dir = Path(backend_path) if Path(backend_path).is_absolute() else Path.cwd() / backend_path
    if backend_dir.exists():
        sys.path.insert(0, str(backend_dir))
    
    os.environ["PYTHONPATH"] = str(backend_dir) + os.pathsep + os.environ.get("PYTHONPATH", "")
    os.chdir(backend_dir)
    
    # Auto-select an available port when the preferred one is busy
    try:
        port = find_available_port(host, preferred_port)
    except RuntimeError as e:
        print(f"[SERVER] Error: {e}")
        sys.exit(1)
    
    if port != preferred_port:
        print(f"[SERVER] Port {preferred_port} is busy, using port {port} instead.")
    print(f"[SERVER] Starting FastAPI on {host}:{port} (reload={reload})")
    print(f"[SERVER] Backend path: {backend_dir}")
    
    # Import and run uvicorn
    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except ImportError:
        print("[SERVER] Error: uvicorn not installed. Run: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"[SERVER] Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()