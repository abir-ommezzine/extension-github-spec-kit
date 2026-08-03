#!/usr/bin/env python3
"""
Spec Watcher for AgentDocx SpecKit
Monitors .md files in configured project path and triggers pipeline via FastAPI
Reads config from .vscode/settings.json
"""
import json
import time
import sys
import hashlib
import requests
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Force line buffering on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True, encoding='utf-8')

def log(msg):
    print(msg, flush=True)

def load_vscode_config():
    """Load agentdocx-speckit config from .vscode/settings.json"""
    settings_path = Path.cwd() / ".vscode" / "settings.json"
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
                return settings.get("agentdocx-speckit", {})
        except Exception as e:
            log(f"[WATCHER] Warning: Could not parse .vscode/settings.json: {e}")
    return {}

class MarkdownHandler(FileSystemEventHandler):
    def __init__(self, api_url, project_name, debounce_seconds=2):
        self.api_url = api_url
        self.project_name = project_name
        self.debounce_seconds = debounce_seconds
        self.last_trigger = {}
        self.file_hashes = {}
    
    def get_file_hash(self, file_path):
        """Compute SHA-256 hash of file content"""
        try:
            return hashlib.sha256(file_path.read_bytes()).hexdigest()
        except Exception:
            return None
    
    def should_process(self, file_path):
        """Check if file changed (debounce + hash comparison)"""
        now = time.time()
        file_str = str(file_path)
        
        # Debounce
        if file_str in self.last_trigger:
            if now - self.last_trigger[file_str] < self.debounce_seconds:
                return False
        
        # Hash comparison
        current_hash = self.get_file_hash(file_path)
        if current_hash is None:
            return False
        
        if file_str in self.file_hashes and self.file_hashes[file_str] == current_hash:
            return False
        
        self.last_trigger[file_str] = now
        self.file_hashes[file_str] = current_hash
        return True
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.suffix.lower() != ".md":
            return
        
        if not self.should_process(file_path):
            return
        
        log(f"[WATCHER] Change detected: {file_path.name}")
        self.trigger_pipeline(file_path)
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.suffix.lower() != ".md":
            return
        
        log(f"[WATCHER] New file: {file_path.name}")
        self.trigger_pipeline(file_path)
    
    def trigger_pipeline(self, file_path):
        """Call FastAPI to process the file"""
        try:
            # Read file content and upload as multipart/form-data
            file_content = file_path.read_bytes()
            files = {
                "file": (file_path.name, file_content, "text/markdown")
            }
            data = {
                "projectName": self.project_name
            }
            
            response = requests.post(
                f"{self.api_url}/api/v1/pipeline/upload",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                log(f"[WATCHER] Pipeline triggered for {file_path.name}: {response.json().get('status')}")
            else:
                log(f"[WATCHER] Pipeline error ({response.status_code}): {response.text}")
                
        except requests.exceptions.ConnectionError:
            log(f"[WATCHER] Error: Cannot connect to FastAPI at {self.api_url}. Is server running?")
        except Exception as e:
            log(f"[WATCHER] Error triggering pipeline: {e}")

def main():
    config = load_vscode_config()
    
    # Get config with defaults
    project_path = config.get("projectPath", "specs")
    project_name = config.get("projectName", Path.cwd().name)
    api_host = config.get("apiHost", "127.0.0.1")
    api_port = config.get("apiPort", 8000)
    debounce = config.get("debounceSeconds", 2)
    watch_patterns = config.get("watchPatterns", ["**/*.md"])
    
    # Resolve project path
    watch_dir = Path.cwd() / project_path
    api_url = f"http://{api_host}:{api_port}"
    
    log(f"[WATCHER] Starting watcher for project: {project_name}")
    log(f"[WATCHER] Watching: {watch_dir}")
    log(f"[WATCHER] API: {api_url}")
    log(f"[WATCHER] Patterns: {watch_patterns}")
    log(f"[WATCHER] Debounce: {debounce}s")
    
    if not watch_dir.exists():
        log(f"[WATCHER] Warning: Watch directory does not exist: {watch_dir}")
        log(f"[WATCHER] Creating it...")
        watch_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up file watcher
    event_handler = MarkdownHandler(api_url, project_name, debounce)
    observer = Observer()
    try:
        observer.schedule(event_handler, str(watch_dir), recursive=True)
        observer.start()
        log(f"[WATCHER] Watcher started. Press Ctrl+C to stop.")
    except Exception as e:
        log(f"[WATCHER] ERROR starting observer: {e}")
        return
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        log("\n[WATCHER] Stopping...")
    observer.join()

if __name__ == "__main__":
    main()