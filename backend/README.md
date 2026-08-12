# ⚙️ Spec Kit Backend Architecture

## 📐 Vue d'ensemble
Le backend Spec Kit repose sur **FastAPI**, **SQLAlchemy (PostgreSQL)** et **LangGraph**. Il intègre deux sous-systèmes autonomes :
1. **Agent Pipeline (Document Generation Pipeline)** : Chaîne multi-agents LangGraph transformant du Markdown brut (`specs/`) en livrables PDF certifiés avec calcul de métriques KPI.
2. **Ticket Agent (Agent JIRA / Kanban Sync)** : Moteur de synchronisation en temps réel des tâches d'implémentation Copilot avec un tableau Kanban.

---

## 🤖 1. Agent Pipeline (Pipeline Multi-Agents & LangGraph)

### 1.1. Architecture du Graph (`app/graph/workflow.py`)
L'orchestration est pilotée par un graphe d'état LangGraph (`StateGraph`) qui définit un flux de travail déterministe et asynchrone :
- **Entrée** : Fichier Markdown source (téléversé via `/upload` ou détecté par le watcher).
- **Parsing Agent** : Point d'entrée unique. Il découpe le document en sections structurées et extrait les entités clés.
- **Trifurcation parallèle** : Après le parsing, le graphe diverge pour exécuter simultanément trois agents d'enrichissement indépendants :
    - **Summary Agent** : Génère le résumé exécutif.
    - **Glossary Agent** : Construit le glossaire technique.
    - **Diagram Agent** : Modélise les architectures en Mermaid.js.
- **Convergence** : Les sorties des trois agents sont synchronisées et injectées dans le **Doc Writer Agent** qui rédige le document Markdown unifié.
- **Certification** : L'agent **Layout** prend le relais pour le rendu PDF final stylisé et la validation de la mise en page.

### 1.2. Détail des 6 Agents & Services (`app/services/`)
Chaque agent dispose de son propre service, d'un schéma Pydantic pour la validation des sorties, et d'un module d'évaluation pour le calcul des KPI.

| Agent | Service | Schéma | Rôle Principal | Métriques KPI |
| :--- | :--- | :--- | :--- | :--- |
| **Parsing** | `parser_service.py` | `parsing_agent_schema.py` | Découpage AST/LLM et extraction de structure. | **SAR** (Schema Adherence), **SIR** (Structural Integrity), **GRI** (Graph Relational Integrity) |
| **Summary** | `summary_service.py` | `summary_agent_schema.py` | Synthèse exécutive et prunage de code. | **WCA** (Word Count Adherence), **GSC** (Graph Stack Content), **MAC** (Maturity Assessment Coherence) |
| **Glossary** | `glossary_service.py` | `glossary_agent_schema.py` | Ancrage topologique et extraction de termes. | **ATA** (Anti-Tautology), **CAP** (Contextual Anchor Precision) |
| **Diagram** | `diagram_service.py` | `diagram_agent_schema.py` | Génération Mermaid.js (Thème Modern Blue). | **SVR** (Syntax Validity), **DCR** (Diagram Element Coverage), **RCR** (Relational Completeness) |
| **Doc Writer** | `doc_writer_service.py` | `doc_writer_agent_schema.py` | Consolidation Markdown unifié. | **DSC** (Document Structure Completeness), **TPR** (Traceability Preservation) |
| **Layout** | `layout_service.py` | `layout_agent_schema.py` | Moteur de rendu PDF et stylisation. | **RSR** (Render Success), **DVR** (Diagram Visual Render), **VOR** (Visual Overflow), **SCS** (Styling Consistency) |

### 1.3. Stockage des Livrables Physiques (`outputs/`)
Le backend persiste les résultats de chaque exécution dans une structure hiérarchisée sous `outputs/{nom_projet}/` :
- `data/` : Fichiers JSON bruts produits par chaque agent (Parsing, Summary, etc.).
- `evaluations/` : Rapports de métriques KPI au format JSONB.
- `markdowns/` : Versions intermédiaires et finales du document Markdown.
- `diagrams/` : Schémas Mermaid exportés en PDF indépendants.
- `pdf/` : Document final versionné et certifié.

### 1.4. Ingestion Automatique
Le pipeline est déclenché via :
- **Endpoint API** : `POST /api/v1/docs/upload` (multipart) utilisé par le Frontend et l'extension VS Code.
- **Spec Watcher** : Un processus `watchdog` surveille le dossier `specs/` et déclenche automatiquement le pipeline dès qu'un fichier `.md` est modifié.

---

## 🎟️ 2. Ticket Agent (Agent JIRA / Kanban Sync)

### 2.1. Flux de Données et Architecture
Le Ticket Agent synchronise l'état d'avancement technique d'un projet avec un tableau Kanban PostgreSQL.

1. **Ingestion (`ticket_ingestion.py`)** : 
    - Analyse le fichier `specs/tasks.md` via `parse_task_lines`.
    - Crée ou rafraîchit les tickets (`T001`, `T002`, ...).
    - **Règle** : Tout ticket nouvellement ingéré est initialisé avec le statut `todo`.
2. **Déclencheur IHM** : L'ingestion est lancée via `POST /api/v1/ingest` (bouton "Ingest Tasks" du Dashboard).
3. **Watcher temps réel (`app/main.py`)** : 
    - La fonction `_watch_current_task_file()` surveille en arrière-plan le fichier `.task_runtime/current-task.json` du projet enfant défini par `TARGET_PROJECT_PATH`.
    - Toute modification de ce fichier déclenche `_sync_current_task_to_db()`.
4. **Synchronisation BDD** :
    - Le backend lit l'instantané complet `tasks` contenu dans le JSON.
    - Il localise le ticket via `_find_ticket_for_task()` (stratégie : projet $\rightarrow$ chemin $\rightarrow$ global).
    - Il met à jour le statut via `update_ticket_status()`.

### 2.2. Modèle de Données (`app/models.py`)
Le système utilise trois tables principales pour la traçabilité :
- **`Ticket`** : Stocke l'identité (`ticket_id`), le titre, la description et le statut (`todo`, `in_progress`, `done`).
- **`TicketEvent`** : Journal d'audit immuable. Enregistre chaque changement de statut avec `event_type`, `author_type` et `event_metadata` (JSONB).
- **`TicketComment`** : Permet l'ajout de commentaires contextuels par des humains ou des agents.

### 2.3. Endpoints API (`app/api/v1/endpoints/tickets.py`)
| Route | Méthode | Description |
| :--- | :--- | :--- |
| `/tickets` | `GET` | Liste tous les tickets du projet. |
| `/tickets/{id}` | `GET` | Détails d'un ticket spécifique. |
| `/tickets/{id}/status` | `PATCH` | Mise à jour manuelle du statut (ex: Drag-and-Drop Kanban). |
| `/ingest` | `POST` | Analyse `tasks.md` et synchronise la structure des tickets. |
| `/sync-current-task` | `POST` | Force le re-balayage manuel du fichier `current-task.json`. |
| `/progress` | `GET` | Calcule les métriques de progression (`total`, `done`, `pct`). |
| `/commit-refine` | `POST` | Tente de déduire un changement de statut à partir d'un message de commit. |

---

## ⚠️ Points d'Attention & Gotchas Techniques

1. **Règle absolue d'ingestion vs synchronisation** : L'endpoint `/ingest` peut créer ou modifier des titres/descriptions, mais **ne promeut jamais** un ticket vers `in_progress` ou `done`. Seule l'écriture dans `current-task.json` (pilotée par Copilot et détectée par le watcher) peut faire évoluer le statut.
2. **Postgres Enum Mapping** : Pour éviter les erreurs `InvalidTextRepresentation`, toutes les colonnes `SAEnum` dans `models.py` utilisent `values_callable=_enum_values`. Cela force SQLAlchemy à envoyer la valeur (`.value`) et non le nom de l'énumération à PostgreSQL.
3. **Nom de colonne `event_metadata`** : Dans la table `TicketEvent`, le champ de métadonnées est nommé `event_metadata` pour éviter tout conflit avec le mot-clé réservé `metadata` de SQLAlchemy.
4. **Variable `TARGET_PROJECT_PATH`** : Le watcher de fichiers est mono-projet. Il surveille uniquement le projet dont le chemin absolu est spécifié dans la variable `TARGET_PROJECT_PATH` du fichier `.env`.
