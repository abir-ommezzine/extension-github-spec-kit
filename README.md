# 🚀 Spec Kit

**Spec Kit** est un pipeline multi-agents avancé conçu pour la génération, l'enrichissement et la validation automatisée de spécifications d'architecture logicielle. Il transforme des documents techniques bruts en livrables structurés et certifiés.

---

## 📌 Structure & Présentation Générale

Le projet est organisé de manière modulaire pour séparer l'orchestration IA, l'interface de suivi et les mécanismes d'automatisation.

### 📂 Arborescence du Projet

- **`/backend`** : ⚙️ Pipeline d'enrichissement et d'évaluation. Propulsé par **FastAPI** et **LangGraph**, il orchestre la chaîne d'agents et gère la logique métier, incluant l'**Agent JIRA** pour la gestion automatisée des tickets.
- **`/frontend`** : 🖥️ Dashboard **React** permettant le suivi en temps réel des exécutions, la visualisation des KPIs et le téléversement de nouveaux documents.
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

## 📋 Agent JIRA (Kanban Ticket Sync)

L'**Agent JIRA** assure une synchronisation bidirectionnelle et automatique entre l'état d'avancement technique du projet (via Copilot) et un tableau Kanban de suivi (To Do / In Progress / Done).

### 🔄 Flux de Synchronisation

#### 1. Ingestion des Tâches (`POST /api/v1/ingest`)
L'ingestion permet d'initialiser ou de rafraîchir la liste des tickets en base de données à partir du fichier de spécifications.
- **Déclenchement** : Via le bouton **"Ingest Tasks"** du Dashboard React après avoir sélectionné le projet, ou automatiquement lors de la sélection.
- **Processus** : Le backend analyse `specs/tasks.md` $\rightarrow$ crée les tickets (`T001`, `T002`, ...) avec le statut initial `todo`.

![Dashboard Ingestion](DashboardVide.png)
*Utilisation du bouton "Ingest Tasks" pour synchroniser les tâches de `tasks.md` vers le Kanban.*

- **⚠️ Règle d'Or (Ingestion)** : L'ingestion met à jour les titres, descriptions et l'état des cases à cocher, mais **ne modifie JAMAIS** le statut d'un ticket existant vers `in_progress` ou `done`.

#### 2. Synchronisation de Statut en Temps Réel
Le passage d'un ticket à l'état "en cours" ou "terminé" est strictement piloté par l'activité de Copilot.
- **Mécanisme** : Un watcher backend (`_watch_current_task_file`) surveille en continu le fichier `.task_runtime/current-task.json` dans le projet enfant.
- **Mise à jour** : Seule la détection d'un changement dans ce fichier peut faire évoluer le statut d'un ticket vers `in_progress` ou `done`.

![Dashboard Synchronisation](DashboardRempli.png)
*Visualisation du tableau Kanban synchronisé en temps réel avec l'activité de Copilot.*


### 🤖 Contrat Copilot (`.github/copilot-instructions.md`)
Pour garantir cette synchronisation, GitHub Copilot suit un protocole strict défini dans les instructions du projet enfant :
- **Avant chaque tâche** : Copilot écrit un instantané JSON complet dans `.task_runtime/current-task.json` avec `status: "in_progress"`. **Cette écriture ne doit jamais être sautée** — un ticket qui passe directement de `todo` à `done` sans passer par `in_progress` signifie que Copilot a sauté cette étape, pas que le système a un bug.
- **Après chaque tâche** : Copilot met à jour le fichier avec `status: "done"`.
- **État Global** : Chaque écriture inclut un objet `tasks: { "T001": "done", ... }` permettant de synchroniser l'intégralité du tableau même après une déconnexion.
- **Case à cocher = preuve de complétion, jamais anticipée** : Copilot ne doit cocher `[x]` une tâche dans `tasks.md` que lorsqu'elle est réellement terminée — jamais simplement parce qu'il passe à la tâche suivante. Une case cochée trop tôt fait apparaître un ticket comme `"done"` sur le Kanban alors que le travail n'est pas fini ; c'est arrivé en pratique et a nécessité une correction manuelle en base.

Ces deux règles sont désormais explicitement écrites en tête de `.github/copilot-instructions.md` (sections dédiées avec ⚠️), suite à des régressions observées en conditions réelles.

#### 🔁 Deux mécanismes de synchronisation de ce fichier vers le projet enfant

1. **Backend (fiable, recommandé)** — `_sync_copilot_instructions()` dans `backend/app/main.py` recopie `.github/copilot-instructions.md` du repo source vers `TARGET_PROJECT_PATH` **à chaque démarrage du backend**. Comme il tourne toujours depuis le code source à jour (voir l'avertissement sur `start_server.py` ci-dessus), c'est la copie qui reflète le plus fidèlement vos éditions.
2. **Extension VS Code (secondaire, best-effort)** — copie le fichier depuis le dossier de l'extension **installée** à chaque activation. Si vous avez modifié `.github/copilot-instructions.md` dans le repo source sans reconstruire/réinstaller le `.vsix`, cette copie peut être obsolète, voire absente (le `.vsix` ne contient pas toujours de dossier `.github/`).

En cas de doute sur la fraîcheur du fichier réellement lu par Copilot dans le projet enfant, comparez-le directement avec celui du repo source, ou redémarrez simplement le backend (mécanisme 1) pour forcer une resynchronisation immédiate.

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
- **`tickets`, `ticket_events` & `ticket_comments`** : Système de traçabilité complète des tâches (User Stories, Tasks), incluant l'historique des événements et les commentaires, synchronisé avec l'avancement du projet via l'Agent JIRA.


---

## 🔌 Extension VS Code SpecKit (Nouveau)

> **⚠️ En cours de développement** — Non publiée sur le Marketplace pour le moment.  
> **Branche dédiée** : [`extension`](https://github.com/ahmed200346/Extension_GithubSpecKit/tree/extension) pour le code complet, tests et documentation détaillée.

> ## 🚨 Le bouton "Start FastAPI Server" de l'extension ne sait PAS servir le Kanban/tickets
>
> Le script `start_server.py` bundlé dans le `.vsix` **ne fait pas** `from app.main import app`. Il construit sa propre application FastAPI minimaliste en dur, qui n'inclut que `pipeline.router` — jamais `tickets.router`. Résultat : `GET /api/v1/tickets` (et `/ingest`, `/progress`, `/sync-current-task`, ...) renvoient **404**, peu importe combien de fois vous redémarrez le serveur via l'extension, peu importe si le code backend est à jour. Ce script date d'avant l'existence du tableau Kanban et n'a jamais été mis à jour pour l'inclure.
>
> **Solution : ne pas utiliser cette commande pour le backend.** Lancez le vrai serveur manuellement, depuis un terminal, à la racine du dossier `backend/` du **repo source** (celui vers lequel pointe la jonction `backend` du projet enfant — voir §3.1) :
> ```bash
> cd backend
> python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
> ```
> Cela lance votre `app/main.py` réel, avec absolument toutes les fonctionnalités (tickets, ingestion, sync `current-task.json`, providers LLM...). Vous pouvez vérifier à tout moment que les bonnes routes sont chargées via `http://127.0.0.1:8000/openapi.json`.
>
> La commande **"Start Spec Watcher"** de l'extension, elle, fonctionne correctement (elle ne touche pas au Kanban) — vous pouvez continuer à l'utiliser pour le déclenchement automatique du pipeline PDF sur changement de fichier `.md`.

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

#### 2. Configuration du Repo Source (une seule fois)

Cette étape prépare l'infrastructure nécessaire au fonctionnement du backend et des agents.

##### 2.1. 🐘 Base de Données PostgreSQL
Créez l'utilisateur et la base de données attendus. Connectez-vous à votre instance PostgreSQL (via `psql` ou pgAdmin4) et exécutez :

```sql
-- Connexion en superuser (ex: postgres)
CREATE USER speckit WITH PASSWORD 'speckit';
CREATE DATABASE speckit OWNER speckit;
```
*Les tables sont créées automatiquement au démarrage du backend, aucune migration manuelle n'est requise.*

##### 2.2. 🦙 LLM Local (Ollama)
Le pipeline d'agents s'appuie sur Ollama. Assurez-vous que le serveur est lancé et que le modèle est téléchargé :

```bash
ollama serve
ollama pull gemma4:31b-cloud
```

##### 2.3. ⚙️ Fichier de Configuration `.env`
Créez un fichier `.env` à la racine du repo source pour lier le backend au projet enfant et configurer le LLM :

```dotenv
# 🗄️ Base de données
DATABASE_URL=postgresql://speckit:speckit@localhost:5432/speckit

# 🎯 PROJET ENFANT
# Chemin ABSOLU vers le projet surveillé (ex: C:\Users\Nom\Documents\mon-app)
TARGET_PROJECT_PATH=C:\Users\MSI\Bureau\mon-projet-test

# 🧠 LLM PROVIDER — sélectionne le provider actif via LLM_PROVIDER
# Valeurs possibles : ollama, openai, anthropic, groq, nvidia, huggingface, openai_compatible
LLM_PROVIDER=ollama

# Ollama (local, gratuit) — actif si LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:31b-cloud

# NVIDIA NIM (OpenAI-compatible) — actif si LLM_PROVIDER=nvidia
# NVIDIA_API_KEY=nvapi-votre-cle-ici
# NVIDIA_MODEL=z-ai/glm-5.2
# NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

# Groq (alternative rapide) — actif si LLM_PROVIDER=groq
# GROQ_API_KEY=gsk_votre-cle-ici
# GROQ_MODEL=llama-3.3-70b-versatile
# GROQ_BASE_URL=https://api.groq.com/openai/v1
```

> [!IMPORTANT]
> **TARGET_PROJECT_PATH** : C'est la variable la plus critique. Elle indique au backend quel dossier surveiller pour détecter les changements dans `.task_runtime/current-task.json`. À chaque changement de projet, mettez à jour ce chemin.

> ⚙️ **NVIDIA NIM peut être lent au premier appel (cold start) ou sur des payloads volumineux** (les agents Summary/Glossary/Diagram envoient plus de contexte que l'agent Parsing). Le provider NVIDIA utilise un timeout de 420s avec retry automatique (backoff exponentiel) sur timeout et rate-limit — si vous voyez quand même `openai.APITimeoutError`, c'est que la requête a dépassé cette marge trois fois de suite ; réessayez ou envisagez un modèle NVIDIA plus léger que celui configuré par défaut.

##### 2.4. 🖥️ Démarrage du Frontend (Optionnel)
Pour suivre l'avancement en temps réel via le Dashboard :

```bash
cd frontend
npm install
npm start
```
L'interface sera accessible sur `http://localhost:3000`.

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

L'extension démarre automatiquement le watcher au chargement — pour le **serveur backend**, utilisez la commande manuelle décrite dans l'avertissement 🚨 en haut de la section [Extension VS Code SpecKit](#-extension-vs-code-speckit-nouveau), pas le bouton de l'extension :

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

| Canal / Terminal | Rôle | Ce que vous verrez |
|--------------|------|---------------------|
| **Terminal `uvicorn`** | FastAPI + LangGraph + Tickets/Kanban | Logs du serveur, progression des agents, sync `current-task.json`, KPIs |
| **AgentDocx Watcher** (Output de l'extension) | Watcher de fichiers | Détection de changements dans `specs/`, file d'attente |

Vérifiez les logs du serveur dans le terminal, et ceux du watcher dans `View` → `Output` → dropdown `AgentDocx Watcher`.

---

#### 5. Workflow Complet : Du Spec au Kanban

##### Étape 1 — Ingérer les tâches en BDD
Le watcher détecte `specs/tasks.md` → le backend ingère les tickets dans la base PostgreSQL.

##### Étape 2 — Copilot implémente les tâches
1. Ouvrez GitHub Copilot Chat dans le projet enfant
2. Copilot lit `.github/copilot-instructions.md` (généré automatiquement)
3. Copilot lit `specs/tasks.md` et commence à implémenter `T001`
4. **Avant** de coder : Copilot écrit `.task_runtime/current-task.json` avec `status: "in_progress"` — cette écriture est obligatoire, même pour une tâche triviale ; c'est elle qui fait apparaître la tâche dans la colonne "En cours"
5. **Après** avoir fini, et seulement une fois le travail réellement terminé : Copilot coche la case `[x]` correspondante dans `tasks.md`, puis met à jour le fichier avec `status: "done"`

> En cas d'écart observé (tâche qui passe directement à `"done"`, ou marquée `"done"` alors qu'elle ne l'est pas) : ce n'est pas un bug du watcher, c'est Copilot qui n'a pas suivi le protocole. Voir 🔧 Dépannage ci-dessous pour la correction manuelle.

##### Étape 3 — Synchronisation automatique (Backend Watcher)
Le watcher backend (dans `app/main.py`, lancé par la commande `uvicorn` manuelle de l'étape 4 — **pas** par le bouton de l'extension) surveille `.task_runtime/current-task.json` :
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

### 🔧 Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `404 Not Found` sur `/api/v1/tickets`, `/ingest`, `/progress`, etc., peu importe les redémarrages | Le backend tourne via le bouton "Start FastAPI Server" de l'extension, dont le `start_server.py` bundlé n'inclut jamais `tickets.router` (voir l'avertissement 🚨 en haut de la section Extension VS Code) | Lancez le backend manuellement : `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. Vérifiez via `http://127.0.0.1:8000/openapi.json` que `/api/v1/tickets` apparaît dans la liste des routes. |
| Vous avez redémarré/rechargé et **rien ne change**, y compris après un `git pull` | Un ancien process Python tient toujours le port 8000 — le nouveau démarrage échoue silencieusement en arrière-plan (`only one usage of each socket address`) et l'ancien continue de répondre | PowerShell : `Get-NetTCPConnection -LocalPort 8000 -State Listen \| Select OwningProcess`, puis `Stop-Process -Id <PID> -Force`. Relancez ensuite le serveur. |
| Un ticket passe directement de `todo` à `done`, sans jamais s'afficher en `in_progress` | Copilot a sauté l'écriture "avant de commencer" de `current-task.json` (voir §Contrat Copilot) | Comportement à corriger côté prompt/Copilot pour la suite ; pour l'instant sur le board, c'est cosmétique si la tâche est réellement terminée. |
| Un ticket est marqué `done` alors que le travail n'est pas fini | Copilot a coché la case `[x]` dans `tasks.md` avant d'avoir réellement terminé la tâche | Décochez la case dans `tasks.md`, corrigez `current-task.json` (le champ `tasks` pour cette tâche), puis forcez une resynchronisation : `POST /api/v1/sync-current-task`. |
| `openai.APITimeoutError` en plein pipeline (souvent sur Summary/Glossary/Diagram, plus rarement Parsing) | Provider NVIDIA (ou un autre provider distant) trop lent pour un payload volumineux | Le client réessaie automatiquement (backoff exponentiel, timeout 420s pour NVIDIA) — si ça persiste après 3 tentatives, réessayez plus tard ou changez de modèle. |
| `.github/copilot-instructions.md` absent ou visiblement obsolète dans le projet enfant | La copie faite par l'extension (best-effort, depuis le `.vsix` installé) peut être manquante ou périmée | Redémarrez le backend — `_sync_copilot_instructions()` le régénère depuis le repo source à chaque démarrage (voir §Contrat Copilot). |
| `invalid input value for enum ..._enum` (Postgres) | Un membre d'enum Python dont `.name` diffère de `.value` (ex. `ArtifactType.data_model = "data-model"`) sans `values_callable` sur la colonne SQLAlchemy | Toutes les colonnes `Enum(...)` dans `models.py` doivent passer `values_callable=_enum_values`. |
| `'payload' is an invalid keyword argument for TicketEvent` | Code obsolète qui construit encore `TicketEvent(..., payload=...)` — la colonne réelle s'appelle `event_metadata` | Vérifiez que vous exécutez bien le bon clone du backend (voir la ligne suivante) et que `ticket_ingestion.py` est à jour. |
| Vos modifications au code semblent n'avoir "aucun effet" | Le dossier `backend/` du projet enfant est une jonction qui pointe vers un **autre clone** que celui que vous éditez | `Get-Item backend \| Select FullName, LinkType, Target` (PowerShell) pour vérifier la cible réelle de la jonction. |

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
L'extension est installée via le fichier `.vsix` (disponible dans les **Releases** ou sur la branche `extension`). Elle démarre **automatiquement** le watcher au chargement de VS Code.
- Vérifiez les logs dans : `View` $\rightarrow$ `Output` $\rightarrow$ sélectionnez `AgentDocx Watcher`.
- ⚠️ **Ne comptez pas sur le bouton "Start FastAPI Server" pour le backend** — voir l'avertissement 🚨 détaillé dans la section [Extension VS Code SpecKit](#-extension-vs-code-speckit-nouveau). Démarrez-le manuellement : `cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.

**Étape 3 : Claude Code** (Terminal 2)
```bash
ollama launch claude
```
*Commandes disponibles : `/speckit-specify`, `/doc-pipeline`, `/speckit-plan`, etc.*

---

### 📚 Ressources Complémentaires
- `configFrontEnd.pdf` — Dépannage et configuration Frontend
- Branche [`extension`](https://github.com/ahmed200346/Extension_GithubSpecKit/tree/extension) — code complet et documentation de l'extension VS Code
- `.github/copilot-instructions.md` — Source du fichier généré dans chaque projet enfant ; toute modification ici se propage au prochain démarrage du backend (fiable) ou à la prochaine activation de l'extension (best-effort, voir §Contrat Copilot)

---


