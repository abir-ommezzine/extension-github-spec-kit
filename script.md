# Scénario Vidéo de Démonstration - Solution ExtensionSpeckit (Projet Sales Management)

## Phase 0 : Installation & Configuration de l'Environnement

### 0.1. Installation du dépôt source (une seule fois)

```bash
# 1. Cloner le dépôt source
git clone https://github.com/ahmed200346/Extension_GithubSpecKit.git
cd Extension_GithubSpecKit

# 2. Backend : environnement virtuel Python + dépendances
python -m venv env
env\Scripts\activate          # Windows
# source env/bin/activate     # Linux / Mac
pip install -r requirements.txt
```

* **Base de données PostgreSQL** (une seule fois, dans `psql` connecté en superuser) :
  ```sql
  CREATE USER speckit WITH PASSWORD 'speckit';
  CREATE DATABASE speckit OWNER speckit;
  ```
  Les tables sont créées automatiquement au premier démarrage du backend — aucune migration manuelle requise.

* **Ollama** (LLM local utilisé par le pipeline d'agents) :
  ```bash
  ollama serve
  ollama pull gemma4:31b-cloud
  ```

* **Fichier `.env`** à la racine du dépôt source :
  ```dotenv
  DATABASE_URL=postgresql://speckit:speckit@localhost:5432/speckit
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=gemma4:31b-cloud
  # TARGET_PROJECT_PATH sera renseigné une fois le projet enfant créé (voir 0.2)
  ```

* **Frontend React** :
  ```bash
  cd frontend
  npm install
  npm start
  ```
  Dashboard accessible sur `http://localhost:3000`.

* **Installation de l'extension VS Code** : `Ctrl+Shift+P` → **Extensions: Install from VSIX...** → sélectionner `agentdocx-speckit-0.0.2.vsix`.

### 0.2. Création et démarrage du projet enfant (« Sales Management »)

```bash
mkdir sales-item-management && cd sales-item-management
specify init .
```

* **Lien vers le backend** : créer une jonction/lien symbolique `backend` à la racine du projet enfant, pointant vers le `backend/` du dépôt source cloné en 0.1 :
  ```powershell
  cmd /c mklink /J "C:\chemin\vers\sales-item-management\backend" "C:\chemin\vers\Extension_GithubSpecKit\backend"
  ```

* **Ciblage du projet** : mettre à jour `TARGET_PROJECT_PATH` dans le `.env` du dépôt source pour pointer vers `sales-item-management`, puis redémarrer le backend.

* **Ouverture dans VS Code** : `code .` depuis `sales-item-management`.
  * L'extension démarre automatiquement le serveur FastAPI et le watcher.
  * Le fichier `.github/copilot-instructions.md` est généré automatiquement.
  * Le **Watcher** détecte le fichier `constitution.md` (template vide généré par `specify init`) et présente le nom du workspace au développeur.

* **Présentation du Pipeline** : explication rapide du workflow des 6 agents automatisant le traitement des fichiers Markdown (`spec.md`, `constitution.md`, etc.) en PDF.
* **Suivi des exécutions** : affichage des logs en temps réel dans les canaux Output `AgentDocx Server` et `AgentDocx Watcher` pour suivre l'avancement des processus backend.

---

## Phase 1 : Définition de la Constitution

### Prompt 1 :
```text
/speckit-constitution Créez des règles pour un code valide et structuré en HTML, CSS et JS pour un projet de gestion d'articles à vendre : syntaxe correcte, respect des best practices pour chaque langage, et structure de fichiers claire pour implémenter ce projet
```

* **Génération initiale** : affichage du PDF généré en cliquant sur le bouton **Open**. Ouverture du fichier `constitution.md` (situé dans `.specify/memory/`).
* **Vérification visuelle** : aperçu synthétique du PDF généré pour confirmer la prise en compte des bonnes pratiques de développement, avant même l'écriture de la première spécification.

---

## Phase 2 : Spécification Initiale et Structure du PDF

### Prompt 2 :
```text
/speckit-specify je veux créer projet de gestion d'article à vendre avec page HTML ,design CSS moderne et en utilisant JS pour des scripts pour mettre site dynamique et interactive
```

* **Génération initiale** :
    * Affichage du PDF généré en cliquant sur le bouton **Open**. Ouverture du fichier `spec.md` (volontairement succinct en raison de la concision du prompt initial).
* **Association du projet à la Constitution** :
    * Le nom du projet source (`001-sales-item-management`, sous le dossier `specs`) est désormais déterminé — la `constitution.md` créée en Phase 1 s'y associe dynamiquement.
    * Vérification sur la page **Documents** de l'interface Frontend pour valider l'actualisation du *Project Name* dans la constitution.
* **Explication de la structure du PDF généré** :
    * **Executive Summary & Architecture Overview** : Résumé du contexte du projet avec l'énumération des frameworks et outils requis. Intègre la section *Maturity Assessment* indiquant les limites du contexte et les points non encore détaillés dans le fichier `.md`.
    * **Architecture Workflows** : Visualisation de l'architecture logicielle avec diagrammes explicatifs, définition des tables relationnelles et génération des *User Stories* (actions cibles, impacts sur la base de données, déclenchement d'événements) produites par l'**Agent Diagramme**.
    * **Detailed Technical Specifications & Business Rules** : Analyse approfondie des éléments du fichier `.md` et de leurs interconnexions requises pour l'exécution des *User Stories*.
    * **Project Governance & Structural Gaps** : Section d'aide au développement listant les zones non spécifiées ou les contraintes contextuelles (*Structural Gaps* extraits par l'**Agent Parsing**).
    * **Technical & Domain Glossary** : Tableau explicatif des termes techniques et fonctionnels, généré par l'**Agent Glossary**.
* **Indicateurs de performance** : Affichage du tableau KPI résumant brièvement les métriques clés de chaque agent.
* **Gestion de l'historique** : Démonstration du suivi des versions (mise à jour du fichier `spec.md` générant une Version 2 du PDF).

---

## Phase 3 : Enrichissement des Spécifications

### Prompt 3 :
```text
/speckit-specify Update le spec dans le dossier 001-sales-item-management en ajoutant une fonctionnalité de recherche et de filtrage des articles par catégorie et par disponibilité, avec un tri dynamique côté client géré en JavaScript
```

* **Analyse du PDF mis à jour (V2)** :
    * Lecture du PDF enrichi comportant une section *Executive Summary & Architecture Overview* détaillée et des schémas complétés dans *Architecture Workflows*, intégrant la nouvelle fonctionnalité de recherche/filtrage.
* **Exécution rapide** : progression directe du traitement, le workflow des 6 agents ayant déjà été détaillé lors du Prompt 2.

---

## Phase 4 : Planification Technique

### Prompt 4 :
```text
/speckit-plan Créez le plan technique detaillé pour le projet 001-sales-item-management
```

* **Validation du flux** : Saisie de la commande et consultation de la page **Documents** sur le Frontend pour confirmer la finalisation du traitement.
* **Analyse des livrables** :
    * Ouverture du PDF `data-model` généré pour visualiser la modélisation des tables relationnelles du module Sales.
    * Lecture du PDF d'artefacts détaillant les règles métiers dans *Detailed Technical Specifications & Business Rules*.

---

## Phase 5 : Génération des Tâches

### Prompt 5 :
```text
/speckit-tasks Générer les tasks pour cet projet mais en ajoutant contraints qui sont mentionnées dans constitution.md pour best pratices pour chaque language à utiliser dans la tache
```