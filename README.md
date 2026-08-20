# AgentDocx SpecKit

**AgentDocx SpecKit** est une extension VS Code conçue pour piloter le pipeline de documentation **Spec Kit** et synchroniser l'avancement des tâches avec un tableau Kanban de suivi.

## 🚀 Fonctionnalités

* **Serveur FastAPI** : Démarrage/arrêt du serveur FastAPI (port 8000) depuis VS Code
* **Watcher Python** : Surveillance en temps réel du dossier `specs/` avec détection de changements
* **Pipeline Spec Kit** : Déclenchement et suivi du pipeline de documentation (LangGraph agents)
* **Dashboard React** : Lancement automatique du frontend (`npm start`), avec réparation automatique en cas d'échec (dépendances cassées, port occupé, etc.)
* **Suivi Kanban des tickets** : Synchronisation automatique de l'état des tâches (`todo` / `in_progress` / `done`) entre Copilot et un tableau Kanban, à partir de `specs/tasks.md`
* **Instructions Copilot** : Génère et resynchronise automatiquement `.github/copilot-instructions.md` dans le projet suivi, à chaque activation de l'extension
* **Sortie en temps réel** : Trois canaux de sortie dédiés (`AgentDocx Server`, `AgentDocx Watcher` et `AgentDocx Frontend`)
* **Intégration fluide** : Commandes accessibles depuis la palette de commandes (`Ctrl+Shift+P` / `Cmd+Shift+P`)
* **Démarrage automatique** : Serveur, Watcher et Frontend React lancés automatiquement au chargement de l'extension

## 🛠️ Commandes disponibles

| Commande | Intitulé | Description |
| :--- | :--- | :--- |
| `agentdocx-speckit.start_server` | `AgentDocx SpecKit: Démarrer le Serveur FastAPI` | Lance le serveur FastAPI (port 8000) |
| `agentdocx-speckit.stopServer` | `AgentDocx SpecKit: Arrêter le Serveur FastAPI` | Arrête le serveur FastAPI |
| `agentdocx-speckit.startWatcher` | `AgentDocx SpecKit: Démarrer le Watcher Python` | Lance le watcher de fichiers `specs/` |
| `agentdocx-speckit.stopWatcher` | `AgentDocx SpecKit: Arrêter le Watcher Python` | Arrête le watcher |
| `agentdocx-speckit.triggerPipeline` | `AgentDocx SpecKit: Déclencher la régénération` | Ping `/health` pour relancer le serveur si besoin et vérifier le pipeline |
| `agentdocx-speckit.startFrontend` | `AgentDocx SpecKit: Démarrer le Frontend React` | Lance `npm start` dans `frontend/` (avec réparation automatique si échec) |
| `agentdocx-speckit.stopFrontend` | `AgentDocx SpecKit: Arrêter le Frontend React` | Arrête le frontend React |

## 📦 Installation, Développement & Publication

### 🛠️ Mode Développement (Lancement rapide)
1. Clonez le dépôt dans votre répertoire local.
2. Installez les dépendances :
   ```bash
   npm install
   ```
3. Compilez l'extension :
   ```bash
   npm run compile
   ```
4. Lancez l'extension en mode développement (`F5` dans VS Code).

### 🏗️ Construction & Packaging (Génération du .vsix)
Pour générer le fichier `.vsix` distribuable, vous devez utiliser l'outil `vsce` :

1. Installer l'outil de packaging VS Code (une seule fois) :
   ```bash
   npm install -g @vscode/vsce
   ```
2. Générer le fichier `.vsix` :
   ```bash
   vsce package
   # → Génère le fichier .vsix à la racine du projet
   ```

### 🚀 Publication sur le Marketplace
Pour publier l'extension sur le VS Code Marketplace (nécessite un Personal Access Token Azure DevOps) :

```bash
vsce publish -p <VOTRE_PAT>
# ou
vsce publish  # mode interactif
```
> 📖 Pour créer un PAT : https://dev.azure.com/ → User Settings → Personal Access Tokens → New Token
> Scopes : **Marketplace > Manage (Publish, Manage)**

## 🐍 Prérequis

* VS Code `^1.80.0`
* Python 3.10+
* Node.js + npm (pour le dashboard React lancé automatiquement)
* Ollama installé et modèle `gemma4:31b-cloud` téléchargé (`ollama pull gemma4:31b-cloud`)
* `ollama serve` en cours d'exécution
* PostgreSQL (pour la persistance des tickets/Kanban)

## 📁 Structure du projet

```
agentdocx-speckit/
├── src/
│   ├── extension.ts          # Point d'entrée de l'extension
│   └── test/
│       └── extension.test.ts # Tests d'intégration
├── scripts/
│   ├── python/
│   │   ├── start_server.py   # Lancement serveur FastAPI + uvicorn
│   │   ├── spec_watcher.py   # Watcher avec debounce + retry pour specs/
│   │   └── run_pipeline_cli.py # CLI manuel pour pipeline
│   └── bash/
│       ├── start-watcher.sh
│       └── create-doc-pipeline.sh
├── dist/                     # Build output (esbuild)
├── package.json
├── tsconfig.json
├── esbuild.js
├── CHANGELOG.md
└── README.md
```

> ℹ️ Le backend FastAPI (`backend/`) et le dashboard React (`frontend/`) vivent dans le même dépôt mais ne sont **pas** empaquetés dans le `.vsix` (voir `.vscodeignore`) : l'extension les pilote via un lien symbolique/junction créé dans le projet enfant, pas en les embarquant.

## 🔄 Workflow complet

```text
[ F5 / Ctrl+Shift+P > start_server ]
    │
    ▼
[ Serveur FastAPI :8000 démarré ]
[ Watcher specs/ démarré ]
[ Frontend React démarré ]
    │
    ▼
[ Édition spec.md / requirements.md dans specs/ ]
    │
    ▼
[ Watcher détecte changement → Stabilisation → File d'attente ]
    │
    ▼
[ Pipeline LangGraph : Parsing → Summary → Glossary → Diagram → DocWriter → Layout ]
    │
    ▼
[ PDF généré dans outputs/<project>/ ]
    │
    ▼
[ Copilot suit .github/copilot-instructions.md → écrit .task_runtime/current-task.json ]
    │
    ▼
[ Backend synchronise le tableau Kanban en temps réel ]
```

## 📚 Documentation

* [README complet du projet](./README.md) — architecture, configuration multi-agents, suivi Kanban/Jira détaillé
* [Scripts Python](./scripts/README.md) - Documentation détaillée des scripts Python
* [CHANGELOG](./CHANGELOG.md) - Historique des versions

## 🤝 Contribution

1. Fork le projet
2. Créez une branche (`git checkout -b feature/amazing-feature`)
3. Committez (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing-feature`)
5. Ouvrez une Pull Request

## 📄 Licence

MIT License - voir [LICENSE](LICENSE) pour plus de détails.
