# 🚀 Spec Kit

**Spec Kit** est un pipeline multi-agents avancé conçu pour la génération, l'enrichissement et la validation automatisée de spécifications d'architecture logicielle. Il transforme des documents techniques bruts en livrables structurés et certifiés.

---

## 📌 Structure & Présentation Générale

Le projet est organisé de manière modulaire pour séparer l'orchestration IA, l'interface de suivi et les mécanismes d'automatisation.

### 📂 Arborescence du Projet

- **`/backend`** : ⚙️ Pipeline d'enrichissement et d'évaluation. Propulsé par **FastAPI** et **LangGraph**, il orchestre la chaîne d'agents et gère la logique métier, incluant l'**Agent JIRA** pour la gestion automatisée des tickets.
- **`/frontend`** : 🖥️ Dashboard **React** permettant le suivi en temps réel des exécutions, la visualisation des KPIs et le téléversement de nouveaux documents.
- **`/scripts`** : 🛠️ ⚠️ *N'existe plus dans ce repo* — contenait historiquement les watchers de fichiers standalone (`spec_watcher.py`, `start_server.py`), remplacés par l'extension VS Code (voir section dédiée). Le `.vsix` packagé embarque encore sa propre copie de ces scripts.
- **`/specs`** : 📄 Dossier source des spécifications Markdown à traiter.
  - Contient des **exemples de fichiers** (`spec.md`, `requirements.md`, etc.) prêts à être traités.
  - Le **watcher surveille ce dossier** en temps réel pour déclencher le pipeline automatiquement.
  - Les **livrables générés** (JSON, PDF, diagrammes, évaluations) sont stockés dans `/outputs/` organisé par projet.
- **`/outputs`** : 📦 Dossier centralisé des livrables, organisé par projet :
  - `data/` : Données structurées JSON.
  - `markdowns/` : Fichiers enrichis.
  - `diagrams/` : Schémas générés.
  - `evaluations/` : Métriques de qualité des agents.
  - `pdf/` : Documents finaux versionnés.

---

## 🖥️ Interface Frontend

Le Frontend est une application React moderne utilisant **Material-UI** et **DataGrid** pour offrir une expérience de monitoring fluide et intuitive.

### 🔍 Fonctionnalités Clés
- **Suivi Temps Réel** : Visualisation instantanée de l'état d'avancement des agents.
- **Analyse de Performance** : Affichage des KPIs de qualité pour chaque étape du pipeline.
- **Gestion Documentaire** : Interface d'upload simplifiée pour initier de nouveaux processus.

### 📸 Aperçus
| 📑 Page Documents | ➕ Ajouter un Document |
| :---: | :---: |
| ![Documents Page](documents.png) | ![Add Document Page](form.png) |
| *Suivi des exécutions, status et viewer PDF* | *Formulaire d'upload et zone Drag & Drop (.md)* |

> 📖 Pour une documentation technique complète sur le frontend, consultez le fichier [`frontend/README.md`](frontend/README.md).

---

## 🗄️ Traçabilité & Versioning BDD (PostgreSQL)

Le système s'appuie sur une base de données PostgreSQL pour garantir l'immuabilité des versions et la traçabilité complète de chaque modification.

### 📊 Modèle de Données
```mermaid
erDiagram
    projects {
        UUID id "PK"
        VARCHAR name
        VARCHAR repo_url
        DATETIME created_at
    }
    artifacts {
        UUID id "PK"
        UUID project_id "FK"
        VARCHAR current_file_hash
        VARCHAR source_path
        VARCHAR artifact_type
        DATETIME created_at
    }
    projects ||--o{ artifacts : references
    doc_versions {
        UUID id "PK"
        UUID artifact_id "FK"
        INTEGER version_no
        VARCHAR version_label
        VARCHAR pdf_path
        VARCHAR source_file_hash
        DATETIME generated_at
        JSONB sections_summary
        VARCHAR commit_hash
        VARCHAR generated_by
        UUID pipeline_run_id "FK"
        FLOAT global_kpi_score
    }
    artifacts ||--o{ doc_versions : references
    pipeline_runs ||--o{ doc_versions : references
    pipeline_runs {
        UUID id "PK"
        UUID artifact_id "FK"
        VARCHAR current_stage
        JSONB structured_json
        TEXT summary_output
        JSONB diagram_output
        JSONB glossary_output
        TEXT written_doc
        TEXT layout_output
        JSONB parsing_eval
        JSONB summary_eval
        JSONB glossary_eval
        JSONB diagram_eval
        JSONB writer_eval
        JSONB layout_eval
        FLOAT global_kpi_score
        TEXT error_message
        DATETIME started_at
        DATETIME completed_at
    }
    artifacts ||--o{ pipeline_runs : references
    tickets {
        UUID id "PK"
        UUID project_id "FK"
        UUID artifact_id "FK"
        VARCHAR source_path
        VARCHAR title
        TEXT description
        VARCHAR status
        INTEGER position
        VARCHAR checkbox_state
        VARCHAR file_hash
        DATETIME created_at
        DATETIME updated_at
    }
    artifacts ||--o{ tickets : references
    projects ||--o{ tickets : references
    ticket_events {
        UUID id "PK"
        UUID ticket_id "FK"
        VARCHAR event_type
        VARCHAR author_type
        JSONB payload
        DATETIME created_at
    }
    tickets ||--o{ ticket_events : references
    ticket_comments {
        UUID id "PK"
        UUID ticket_id "FK"
        VARCHAR author_type
        TEXT body
        DATETIME created_at
    }
    tickets ||--o{ ticket_comments : references
```
### 📋 Description des Tables
- **`projects`** : L'entité parente regroupant tous les artefacts et exécutions d'un projet spécifique.
- **`artifacts`** : Registre des fichiers sources surveillés dans `specs/`, incluant une empreinte **SHA-256** pour détecter précisément chaque modification.
- **`pipeline_runs`** : Journalisation exhaustive de chaque exécution, stockant les métriques **JSONB** détaillées pour chacun des 6 agents du pipeline.
- **`doc_versions`** : Registre immuable gérant le versioning dynamique des documents et le lien vers les fichiers PDF certifiés.
- **`tickets` & `ticket_events`** : Système de traçabilité des tâches (User Stories, Tasks) synchronisé avec l'avancement du projet via l'Agent JIRA.


---

## 🔌 Extension VS Code SpecKit (Nouveau)

> **⚠️ En cours de développement** — Non publiée sur le Marketplace pour le moment.  
> **Branche dédiée** : [`extension`](https://github.com/ahmed200346/Extension_GithubSpecKit/tree/extension) pour le code complet, tests et documentation détaillée.

L'extension VS Code **AgentDocx SpecKit** remplace le dossier `scripts/` et offre une expérience intégrée **dans une seule fenêtre VS Code** :
- **Deux canaux de logs dans la vue Output** (menu `View` → `Output` → dropdown pour basculer) :  
  - **AgentDocx Server** — logs FastAPI, progression agents (Parsing → Summary → Glossary → Diagram → DocWriter → Layout), KPIs  
  - **AgentDocx Watcher** — logs watchdog, détection fichiers, file d'attente
- **Démarrage automatique** au chargement de l'extension (F5 ou installation .vsix)
- **Progression temps réel** visible dans le frontend (DocVersion créée dès le début, statut `pending` → `completed`)
- **Commandes palette** (`Ctrl+Shift+P`) : `start_server`, `stopServer`, `startWatcher`, `stopWatcher`, `triggerPipeline`

> 📸 **Captures de l'extension** :  
> 1. **AgentDocx Watcher** — logs watchdog, détection fichiers, file d'attente  
>    ![AgentDocx Watcher](AgentDocxWatcher.png)  
> 2. **AgentDocx Server** — logs FastAPI, progression agents (Parsing → Summary → Glossary → Diagram → DocWriter → Layout), KPIs  
>    ![AgentDocx Server](AgentDocxServer.png)

### 📦 Installation de l'Extension (via .vsix)

> L'extension n'est pas encore publiée sur le Marketplace VS Code. Installez-la manuellement via le fichier `.vsix` :

1. Téléchargez le fichier `agentdocx-speckit-0.0.2.vsix` depuis la section **Releases** du dépôt ou depuis le dossier racine du repo (branche `extension`).
2. Dans VS Code : `Ctrl+Shift+P` → **Extensions: Install from VSIX...**
3. Sélectionnez le fichier `.vsix` téléchargé.
4. Redémarrez VS Code si nécessaire.

> 📸 **Installation via .vsix** :  
> ![Installation VSIX](ExtensionVSCode.png)  
> *(Capture : icône Extensions → "..." → "Install from VSIX..." → sélectionner le fichier .vsix)*

> 📸 **Captures de l'extension (onglets Output)** :  
> 1. **AgentDocx Watcher** — logs watchdog, détection fichiers, file d'attente  
>    ![AgentDocx Watcher](AgentDocxWatcher.png)  
> 2. **AgentDocx Server** — logs FastAPI, progression agents (Parsing → Summary → Glossary → Diagram → DocWriter → Layout), KPIs  
>    ![AgentDocx Server](AgentDocxServer.png)

> **ℹ️ Note importante** : Contrairement à l'ancien mode (F5 ouvrait une seconde fenêtre "Extension Development Host"), l'extension s'exécute maintenant **dans la même fenêtre VS Code**. Les logs apparaissent dans le panneau **Output** (`View > Output`) avec un dropdown pour basculer entre **AgentDocx Server** et **AgentDocx Watcher**.

---

### 🏗️ Construction & Publication de l'Extension (pour développeurs)

> Pour générer le fichier `.vsix` à partir des sources (branche `extension`) :

```bash
# 1. Installer l'outil de packaging VS Code (une seule fois)
npm install -g @vscode/vsce

# 2. Cloner la branche extension
git clone -b extension https://github.com/ahmed200346/Extension_GithubSpecKit.git
cd Extension_GithubSpecKit

# 3. Installer les dépendances et compiler
npm install
npm run compile

# 4. Générer le fichier .vsix
vsce package
# → Génère agentdocx-speckit-0.0.2.vsix à la racine
```

> **Pour publier sur le Marketplace** (nécessite un Personal Access Token Azure DevOps) :
```bash
vsce publish -p <VOTRE_PAT>
# ou
vsce publish  # mode interactif
```

> 📖 Pour créer un PAT : https://dev.azure.com/ → User Settings → Personal Access Tokens → New Token
> Scopes : **Marketplace > Manage (Publish, Manage)**

---

---

### 🧪 Guide de Test : Nouveau Projet avec l'Extension VS Code

> **Objectif** : Démarrer un **nouveau projet enfant** avec Spec Kit. L'extension VS Code gère le backend (FastAPI) et le watcher de fichiers, tandis que le backend synchronise automatiquement l'état des tâches avec la base de données et le frontend Kanban.

---

#### Architecture en bref

```
┌─────────────────────────────────────────────────────────────┐
│  PROJET SOURCE (repo de l'extension)                        │
│  new copyextension-github-spec-kit/                          │
│  ├── backend/          → FastAPI + LangGraph + Watchers      │
│  ├── frontend/         → Dashboard React (Kanban, KPIs)      │
│  ├── src/              → Code de l'extension VS Code        │
│  └── .env              → TARGET_PROJECT_PATH + LLM config    │
│                                                              │
│           ┌──────────────────────────────────┐              │
│           │  PROJET ENFANT (votre app)        │              │
│           │  mon-projet-test/                 │              │
│           │  ├── .github/                     │              │
│           │  │   └── copilot-instructions.md  │ ← généré auto│
│           │  ├── .vscode/                     │              │
│           │  │   └── settings.json            │ ← config lien │
│           │  ├── specs/                        │              │
│           │  │   └── tasks.md                  │ ← tâches     │
│           │  └── .task_runtime/                │              │
│           │       └── current-task.json        │ ← écrit par   │
│           │           (mis à jour par Copilot) │   Copilot    │
│           └──────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

**Flux de données** :
1. Copilot lit `tasks.md` → implémente une tâche → écrit `.task_runtime/current-task.json`
2. Le watcher backend détecte le changement → met à jour le ticket en BDD
3. Le frontend Kanban se met à jour en temps réel

---

#### 1. Prérequis

| Composant | Détail |
|-----------|--------|
| **Extension VS Code** | Installée via `.vsix` (voir section ci-dessus) |
| **PostgreSQL** | En cours d'exécution (ou pgAdmin4 connecté) |
| **Dépendances Python** | `pip install -r requirements.txt` dans le **repo source** |
| **Dépendances Frontend** | `cd frontend && npm install` dans le **repo source** |
| **LLM Provider** | Configuré dans `.env` du repo source (NVIDIA, Groq, Ollama, etc.) |

---

#### 2. Configuration du Repo Source (une seule fois)

##### 2.1. Fichier `.env` (à la racine du repo source)

Configurez le chemin du projet enfant et votre provider LLM :

```dotenv
# Base de données
DATABASE_URL=postgresql://speckit:speckit@localhost:5432/speckit

# ── PROJET ENFANT ──────────────────────────────────────────────
# Chemin ABSOLU vers le projet sur lequel vous travaillez
# (c'est là que le backend va watcher .task_runtime/current-task.json)
TARGET_PROJECT_PATH=C:\Users\MSI\Bureau\mon-projet-test

# ── LLM PROVIDER ───────────────────────────────────────────────
# ⚠️ Aujourd'hui, seul Ollama est réellement lu par le code
# (backend/app/core/llm_client.py ne consomme que OLLAMA_BASE_URL / OLLAMA_MODEL).
# Les blocs NVIDIA / Groq ci-dessous sont commentés : ils ne sont PAS câblés dans
# le code actuel, et servent uniquement de gabarit de syntaxe si vous ajoutez un
# jour le support d'un autre provider (dans backend/app/core/llm_client.py et
# backend/app/config.py, en ajoutant les champs correspondants à la classe Settings).

# Ollama (actif — local, gratuit)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:31b-cloud

# NVIDIA NIM (OpenAI-compatible) — gabarit, non câblé
# NVIDIA_API_KEY=nvapi-votre-cle-ici
# NVIDIA_MODEL=z-ai/glm-5.2
# NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Groq (alternative rapide) — gabarit, non câblé
# GROQ_API_KEY=gsk_votre-cle-ici
# GROQ_MODEL=llama-3.3-70b-versatile
# GROQ_BASE_URL=https://api.groq.com/openai/v1
```

> ⚠️ **À chaque changement de projet enfant**, mettez à jour `TARGET_PROJECT_PATH` dans ce fichier `.env`.

> ⚠️ **`TARGET_PROJECT_PATH` (.env) et `SPECKIT_WORKSPACE` (variable d'environnement injectée par l'extension) sont deux mécanismes indépendants** qui ne se synchronisent pas automatiquement :
> - `SPECKIT_WORKSPACE` — utilisé uniquement par `start_server.py` pour localiser le dossier `backend/app` à charger.
> - `TARGET_PROJECT_PATH` — utilisé par le backend pour savoir quel `.task_runtime/current-task.json` surveiller.
>
> En pratique les deux doivent pointer vers le **même** projet enfant, mais vous devez les maintenir cohérents vous-même.

#### 2.0. Base de données PostgreSQL (une seule fois)

Créez l'utilisateur et la base attendus par `DATABASE_URL` ci-dessus (adaptez si vous utilisez d'autres identifiants) :

```sql
-- Dans psql, connecté en superuser (ex: postgres)
CREATE USER speckit WITH PASSWORD 'speckit';
CREATE DATABASE speckit OWNER speckit;
```

Les tables sont créées automatiquement au démarrage du backend (`Base.metadata.create_all`), aucune migration manuelle n'est nécessaire.

#### 2.0.1. Ollama (une seule fois)

Le pipeline d'agents nécessite un serveur Ollama local avec le modèle configuré disponible :

```bash
ollama serve
ollama pull gemma4:31b-cloud   # ou tout autre modèle, en cohérence avec OLLAMA_MODEL dans .env
```

##### 2.2. Démarrage du Frontend (optionnel mais recommandé)

```bash
cd frontend
npm start
```
Le dashboard sera accessible sur `http://localhost:3000`.

---

#### 3. Création du Projet Enfant

```bash
mkdir mon-projet-test && cd mon-projet-test
```

##### 3.1. Lier le projet enfant au backend du repo source

**Étape obligatoire** : créez, **à la racine du projet enfant**, un lien symbolique/junction nommé `backend` pointant vers le `backend/` du **repo source** :

**Windows (terminal PowerShell ou Invite de commandes — `mklink /J` crée une jonction, ce qui ne nécessite ni droits admin ni mode développeur, contrairement à un lien symbolique `/D`) :**
```powershell
cmd /c mklink /J "C:\chemin\vers\mon-projet-test\backend" "C:\chemin\vers\new copyextension-github-spec-kit\backend"
```
> ⚠️ Si votre terminal VS Code est **Git Bash**, le flag `/J` peut être mal interprété par la conversion de chemins MSYS — utilisez plutôt un terminal PowerShell ou Invite de commandes pour cette commande.

**Linux/macOS :**
```bash
ln -s /chemin/vers/new-copyextension-github-spec-kit/backend /chemin/vers/mon-projet-test/backend
```

C'est ce lien, et lui seul, qui détermine quel code backend s'exécute. Vérifiez qu'il pointe vers le clone que vous éditez réellement — **si vous avez plusieurs clones du repo sur votre machine, un lien qui pointe vers le mauvais clone donnera l'impression que vos modifications n'ont aucun effet**, sans aucune erreur visible (voir 🔧 Dépannage).

<details>
<summary>Pourquoi un lien symbolique et pas un simple champ de config ?</summary>

Le script `start_server.py` bundlé dans le `.vsix` cherche un dossier `backend/app` valide **dans cet ordre**, sans lire aucune configuration VS Code :
1. `<projet enfant>/backend/app` ← c'est le lien que vous venez de créer qui est trouvé ici
2. `<dossier de l'extension installée>/backend/app`
3. Recherche ascendante depuis l'emplacement du script

Vous verrez parfois une clé `backendPath` documentée dans `.vscode/settings.json` — **elle n'a aucun effet** : `src/extension.ts` ne contient aucun appel à `vscode.workspace.getConfiguration`, donc rien ne la lit jamais. Ignorez-la si vous la voyez ailleurs.
</details>

**Optionnel** : vous pouvez tout de même créer ce fichier à la racine du projet enfant à titre de documentation du projet (nom, port API...) — mais aucune de ces valeurs n'est lue par l'extension aujourd'hui, ce fichier n'a donc aucun effet fonctionnel. Vous pouvez l'omettre sans conséquence.

```json
{
  "agentdocx-speckit": {
    "projectPath": "specs",
    "projectName": "mon-projet-test",
    "apiPort": 8000,
    "reload": false
  }
}
```

##### 3.2. Dossier `specs/` et fichier `tasks.md`

```bash
mkdir specs
```

Créez votre fichier de tâches dans `specs/tasks.md` (format Spec Kit standard avec `## T001`, `## T002`, etc.).

##### 3.3. Génération automatique de `.github/copilot-instructions.md`

> ✅ **Automatique** — Aucune action manuelle requise.

Lorsque vous ouvrez le projet enfant dans VS Code, l'extension **génère automatiquement** (et **régénère à chaque activation**, donc à chaque rechargement de fenêtre) le fichier `.github/copilot-instructions.md` à partir du fichier source situé dans le repo de l'extension. Ce fichier instruit GitHub Copilot à :

1. Lire `tasks.md` pour trouver la tâche à implémenter
2. Écrire `.task_runtime/current-task.json` **avant** de commencer, avec `status: "in_progress"` pour la tâche en cours **et un instantané complet du statut de toutes les tâches** de `tasks.md` (`tasks: {...}`)
3. Mettre à jour ce même fichier après completion, avec `status: "done"` et le même instantané complet mis à jour

**Format du fichier généré** (identique à chaque projet) :
```json
{
  "task_id": "T001",
  "file": "src/app.js",
  "status": "in_progress",
  "project_name": "mon-projet-test",
  "updated_at": "2026-08-11T10:30:00.000000+00:00",
  "tasks": {
    "T001": "in_progress",
    "T002": "todo",
    "T003": "todo"
  }
}
```

> ⚠️ **Le champ `tasks` (instantané complet) est ce qui permet au statut de "rattraper" son retard** si le backend n'était pas démarré pendant que Copilot travaillait sur plusieurs tâches d'affilée : à la prochaine écriture du fichier, `tasks` contient le statut réel de toutes les tâches et le backend les synchronise en une fois. Sans ce champ, seule la dernière tâche touchée serait mise à jour.

> ⚠️ **`/ingest` (ou le bouton "Ingest Tasks" du frontend) ne change JAMAIS le statut d'un ticket.** Il ne fait que rafraîchir le titre, la description et l'état visuel de la case à cocher (`checkbox_state`, affichage uniquement) depuis `tasks.md`. **Seul `.task_runtime/current-task.json`**, lu par le watcher backend, peut faire passer un ticket de `todo` à `in_progress` ou `done`. Si vos tickets restent bloqués en `todo` alors que `tasks.md` montre des cases cochées, vérifiez que `current-task.json` existe et contient bien un objet `tasks` à jour — pas que vous avez ré-ingéré.

---

#### 4. Démarrage dans VS Code

```bash
code .
```

L'extension démarre automatiquement au chargement :

| Canal Output | Rôle | Ce que vous verrez |
|--------------|------|---------------------|
| **AgentDocx Server** | FastAPI + LangGraph | Logs du serveur, progression des agents, KPIs |
| **AgentDocx Watcher** | Watcher de fichiers | Détection de changements dans `specs/`, file d'attente |

Vérifiez les logs : `View` → `Output` → dropdown `AgentDocx Server` / `AgentDocx Watcher`

---

#### 5. Workflow Complet : Du Spec au Kanban

##### Étape 1 — Ingérer les tâches en BDD
Le watcher détecte `specs/tasks.md` → le backend ingère les tickets dans la base PostgreSQL.

##### Étape 2 — Copilot implémente les tâches
1. Ouvrez GitHub Copilot Chat dans le projet enfant
2. Copilot lit `.github/copilot-instructions.md` (généré automatiquement)
3. Copilot lit `specs/tasks.md` et commence à implémenter `T001`
4. **Avant** de coder : Copilot écrit `.task_runtime/current-task.json` avec `status: "in_progress"`
5. **Après** avoir fini : Copilot met à jour le fichier avec `status: "done"`

##### Étape 3 — Synchronisation automatique (Backend Watcher)
Le watcher backend (dans `app/main.py`) surveille `.task_runtime/current-task.json` :
- Détecte le changement → lit le `task_id` et le `status`
- Met à jour le ticket correspondant en BDD (`TicketStatus.in_progress` → `TicketStatus.done`)
- Le frontend Kanban se met à jour en temps réel

##### Étape 4 — Générer les PDFs
Pour déclencher la génération de documents PDF à partir des specs :
1. Palette de commandes (`Ctrl+Shift+P`) → `AgentDocx SpecKit: Trigger Pipeline`
2. Ou : modifiez un fichier `.md` dans `specs/` → le watcher détecte le changement
3. Le pipeline s'exécute : Parsing → Summary → Glossary → Diagram → DocWriter → Layout → PDF
4. Les livrables sont stockés dans `outputs/<projectName>/pdf/`

---

#### 6. Vérification des résultats

| Où | Quoi |
|----|------|
| **Logs Server** | Progression agents (Parsing → Summary → Glossary → Diagram → DocWriter → Layout) |
| **Frontend** | Onglet Documents → nouvelle entrée avec KPIs ; Onglet Kanban → tickets mis à jour |
| **Outputs** | `outputs/<projectName>/pdf/` → PDFs générés et versionnés |
| **BDD** | Table `tickets` → statuts synchronisés avec `current-task.json` |

---

### 📁 Structure attendue du projet enfant

```
mon-projet-test/
├── .github/
│   └── copilot-instructions.md   # ← Généré automatiquement par l'extension
├── .vscode/
│   └── settings.json             # ← Configuration obligatoire (lien vers le backend)
├── specs/
│   └── tasks.md                  # ← Vos tâches (T001, T002, ...)
├── .task_runtime/
│   └── current-task.json         # ← Écrit/mis à jour par Copilot pendant l'implémentation
├── src/                          # Votre code applicatif (optionnel)
└── package.json                  # Votre projet (optionnel)
```

---

### 🔧 Dépannage courant

| Problème | Solution |
|----------|----------|
| `Script Watcher introuvable` / `Script Python introuvable` dans les logs | Ces commandes lancent `scripts/python/spec_watcher.py` et `start_server.py`, qui **n'existent plus dans le repo source** (supprimés, jamais remplacés dans `src/extension.ts`). Utilisez le `.vsix` packagé (qui les bundle toujours) plutôt que F5 depuis le repo source, ou démarrez le backend manuellement (`uvicorn app.main:app`). |
| **J'ai modifié le code backend mais rien ne change** | Le plus probable : le `backend/` du projet enfant est un lien symbolique/junction qui pointe vers un **autre clone** du repo que celui que vous éditez. Vérifiez avec `Get-Item backend \| Select Target` (PowerShell) que la cible est bien le repo que vous modifiez, puis redémarrez le backend. C'est arrivé en pratique : plusieurs clones du même repo sur la machine, un seul lien, pointant vers le mauvais. |
| Server erreur "No module named app" | Le lien `backend` du projet enfant ne pointe pas vers un dossier contenant `app/main.py` — recréez-le (voir §3.1) |
| `NameError: name 'Enum' is not defined` | Vérifiez que `backend/app/models.py` utilise `from enum import Enum` (pas `import enum`) |
| `invalid input value for enum artifact_type_enum: "..."` | Un des enums Python (ex. `ArtifactType.data_model = "data-model"`) a un `.name` différent de sa `.value`. Toutes les colonnes `SAEnum(...)` dans `models.py` doivent passer `values_callable=_enum_values` pour que SQLAlchemy envoie `.value` (et non `.name`) à Postgres. |
| `'payload' is an invalid keyword argument for TicketEvent` | Le modèle `TicketEvent` expose une colonne `event_metadata`, pas `payload`. Si vous voyez cette erreur, `backend/app/services/ticket_ingestion.py` n'est pas à jour (vérifiez que vous éditez/exécutez le bon clone — voir l'entrée ci-dessus). |
| Port 8000 occupé | Changez `apiPort` dans `settings.json`, ou libérez le port (`Get-NetTCPConnection -LocalPort 8000` en PowerShell pour identifier le process) |
| **Tickets restent en `todo` malgré des cases cochées dans `tasks.md`** | Normal si `.task_runtime/current-task.json` est vide/absent — `/ingest` ne change jamais le statut, seul ce fichier le fait (voir §3.3). Vérifiez aussi `TARGET_PROJECT_PATH` dans `.env` du repo source → doit pointer vers le projet enfant. |
| `copilot-instructions.md` non généré | Rechargez la fenêtre VS Code (`Ctrl+Shift+P` → `Developer: Reload Window`) |
| Pipeline 404/422 | L'extension utilise `/upload` (multipart), pas `/run` (JSON) |
| Pas de logs dans Output | Rechargez fenêtre : `Ctrl+Shift+P` → `Developer: Reload Window` |
| Dossier `specs/` créé dans le repo source | ✅ Corrigé — les uploads utilisent maintenant le dossier temporaire du système |

---

### 🔄 Workflow multi-projets

> ⚠️ **Le lien `backend` (junction/symlink, §3.1) ne résout PAS le multi-projets.** Il détermine uniquement quel *code* backend s'exécute — pas quel projet est surveillé. La preuve : `BASE_DIR` dans `backend/app/config.py` est calculé via `Path(__file__).resolve()`, qui **traverse la jonction jusqu'au repo source physique**, quel que soit le projet enfant depuis lequel le serveur a été démarré. Concrètement : `Path("<n'importe quel projet enfant>/backend/app/config.py").resolve()` renvoie toujours `<repo source>/backend/app/config.py`. Donc **tous les projets enfants liés au même repo source partagent le même `.env`, donc le même `TARGET_PROJECT_PATH`**.

Chaque projet enfant a **sa propre config** dans son `.vscode/settings.json`, mais le **repo source ne peut watcher qu'un seul projet enfant à la fois** (via `TARGET_PROJECT_PATH` dans son `.env` unique).

**Option A — Séquentiel (le plus simple)** : basculez `TARGET_PROJECT_PATH` selon le projet sur lequel vous travaillez activement.

```
# Repo source .env (UN seul projet actif à la fois)
TARGET_PROJECT_PATH=C:\Users\MSI\Bureau\projet-A

projet-A/backend  →  (junction vers le repo source)
projet-A/specs/tasks.md
projet-A/.task_runtime/current-task.json

projet-B/backend  →  (junction vers le MÊME repo source)
projet-B/specs/tasks.md
projet-B/.task_runtime/current-task.json
```

> Pour passer au projet B : modifiez `TARGET_PROJECT_PATH` dans le `.env` du repo source, puis redémarrez le serveur. Les tickets du projet A restent en base et restent consultables/sélectionnables dans le frontend — ils ne reçoivent simplement plus de mises à jour de statut en temps réel tant que vous n'y revenez pas.

**Option B — Surveillance simultanée réelle** : nécessite un **clone physique séparé** du backend par projet enfant (pas une simple jonction vers un clone partagé), chacun avec son propre `.env` (`TARGET_PROJECT_PATH` différent) et son propre port. Chaque projet enfant lie alors son dossier `backend` vers **son propre clone dédié** plutôt que vers un clone commun :

```
projet-A/backend  →  C:\...\clone-A\backend   (.env : TARGET_PROJECT_PATH=projet-A, port 8000)
projet-B/backend  →  C:\...\clone-B\backend   (.env : TARGET_PROJECT_PATH=projet-B, port 8001)
```

Plus lourd à maintenir (garder N clones synchronisés), mais c'est la seule façon d'avoir deux backends qui surveillent réellement deux projets en parallèle avec le code actuel.

---

## 🚀 Quick Start (Guide de Lancement)

Suivez ces étapes pour mettre en place l'environnement Spec Kit sur votre machine.

### ⚠️ Prérequis Base de Données
Avant de démarrer les services, assurez-vous impérativement que :
- **PostgreSQL** est lancé en arrière-plan.
- OU que **pgAdmin4** est ouvert avec une connexion active à la base de données du projet.

---

### 🛠️ Méthode 1 : Scripts Standalone (⚠️ Non fonctionnelle actuellement)

> **⚠️ `scripts/python/spec_watcher.py` et `scripts/python/start_server.py` ont été supprimés du repo source** (le dossier `/scripts` n'existe plus). Cette méthode est documentée ci-dessous pour référence historique, mais l'Étape 3 échouera telle quelle. En attendant que ces scripts soient restaurés ou remplacés, utilisez la **Méthode 2**, ou démarrez le backend manuellement avec `uvicorn` (Étape 1 ci-dessous, qui fonctionne indépendamment du dossier `/scripts`) — il n'y a alors simplement pas de watcher de fichiers `.md` automatique tant que ce point n'est pas résolu.

#### Prérequis Base de Données
- PostgreSQL lancé (ou pgAdmin4 connecté)

#### Procédure de Lancement

**Étape 0 : Environnement Virtuel Python & Dépendances**
```bash
# Créer l'environnement virtuel
python -m venv env

# Activer l'environnement
# Sur Windows : env\Scripts\activate
# Sur Linux/Mac : source env/bin/activate

# Installer les dépendances
pip install -r requirements.txt
```

**Étape 1 : Démarrer le Backend FastAPI** (Terminal 1)
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Étape 2 : Démarrer l'interface Frontend React** (Terminal 2)
```bash
cd frontend
npm install
npm start
```
> 💡 Si erreurs (dépendances, Node.js, `cross-env`, ports) → voir `configFrontEnd.pdf` à la racine.

**Étape 3 : Lancer le Watcher Temps Réel** (Terminal 3)
```bash
python scripts/python/spec_watcher.py
```
> ⚠️ Ce script n'existe plus dans le repo source (voir avertissement en haut de cette section). Sans lui, les modifications de fichiers `.md` ne déclenchent pas automatiquement le pipeline de génération PDF — le reste (backend, frontend, Kanban, sync `current-task.json`) fonctionne normalement sans cette étape.

**Étape 4 : Exécuter Spec Kit via Claude Code** (Terminal 4)
```bash
ollama launch claude
```
*Utilisez les commandes Spec Kit (ex: `/speckit-specify`, `/doc-pipeline`) pour générer vos spécifications.*

---

### 🛠️ Méthode 2 : Extension VS Code (Installation .vsix — Recommandé)

> **Remplace** entièrement le dossier `scripts/` par une extension VS Code intégrée.
> **Installation** : Voir la section [📦 Installation de l'Extension (via .vsix)](#-installation-de-lextension-via-vsix).

#### Architecture
- **Dossiers Utilisés** : `/backend` et `/frontend`.
- **Remplacement** : L'extension gère tout ce qui était auparavant dans `/scripts` (plus besoin de lancer manuellement le watcher).
- **Interface** : Tout est centralisé dans une seule fenêtre VS Code (canaux `AgentDocx Server` et `AgentDocx Watcher` dans l'onglet Output).

#### Procédure de Lancement

**Étape 0 : Environnement Python & Dépendances**
L'extension nécessite les dépendances du projet installées à la racine :
```bash
# Créer l'environnement virtuel
python -m venv env
# Activer l'environnement (Windows: env\Scripts\activate | Linux/Mac: source env/bin/activate)

# Installer les dépendances globales depuis la racine (même niveau que frontend et backend)
pip install -r requirements.txt
```

**Étape 1 : Frontend React** (Terminal 1)
```bash
cd frontend
npm install
npm start
```

**Étape 2 : Activation de l'Extension**
L'extension est installée via le fichier `.vsix` (disponible dans les **Releases** ou sur la branche `extension`). Elle démarre **automatiquement** le serveur et le watcher au chargement de VS Code.
- Vérifiez les logs dans : `View` $\rightarrow$ `Output` $\rightarrow$ sélectionnez `AgentDocx Server` ou `AgentDocx Watcher`.

**Étape 3 : Claude Code** (Terminal 2)
```bash
ollama launch claude
```
*Commandes disponibles : `/speckit-specify`, `/doc-pipeline`, `/speckit-plan`, etc.*

---

## 🔄 Résumé : Quelle méthode choisir ?

| Critère | Méthode 1 (Scripts) | Méthode 2 (Extension .vsix) |
|---------|---------------------|---------------------------|
| **Statut** | Production | Recommandé (via .vsix) |
| **Terminaux** | 4 | 2 (Frontend + Claude) + Extension |
| **Logs** | Unifiés dans terminaux | Séparés : `AgentDocx Watcher` / `AgentDocx Server` |
| **Progression v2+** | Visible seulement à la fin | Temps réel (DocVersion `pending` → `completed`) |
| **Installation** | Standard (Python) | VSIX + Root requirements |

> Pour les détails complets sur l'extension : voir branche [`extension`](https://github.com/ahmed200346/Extension_GithubSpecKit/tree/extension) et documentation dans `agentdocx-speckit/README.md`.

---

### 📚 Ressources Complémentaires
- `configFrontEnd.pdf` — Dépannage et configuration Frontend
- Branche [`extension`](https://github.com/ahmed200346/Extension_GithubSpecKit/tree/extension) — code complet et documentation de l'extension VS Code
- `.github/copilot-instructions.md` — Source du fichier généré dans chaque projet enfant ; toute modification ici se propage à tous les projets enfants à la prochaine activation de l'extension

---

<<<<<<< HEAD
*Dernière mise à jour : 2026-08-11 — Spec Kit v0.0.2 (Extension en développement)*
=======
*Dernière mise à jour : 2026-07-31 — Spec Kit v0.0.2 (Extension en développement)*

>>>>>>> 05fc91d2d3321776bfce387b46f916daa12ec7d7
