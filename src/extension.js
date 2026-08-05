"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const fs = __importStar(require("fs"));
const child_process = __importStar(require("child_process"));
const http = __importStar(require("http"));
let serverProcess;
let watcherProcess;
// 💡 Deux canaux de sortie distincts pour une traçabilité optimale
let serverOutputChannel;
let watcherOutputChannel;
function getPythonExecutable() {
    return process.platform === 'win32' ? 'python' : 'python3';
}
function activate(context) {
    // Initialisation des deux canaux d'affichage
    serverOutputChannel = vscode.window.createOutputChannel("AgentDocx Server");
    watcherOutputChannel = vscode.window.createOutputChannel("AgentDocx Watcher");
    serverOutputChannel.appendLine("[INIT] Canal Serveur FastAPI prêt.");
    watcherOutputChannel.appendLine("[INIT] Canal Watcher Python prêt.");
    // Détermination du dossier backend s'il existe
    const backendPath = path.join(context.extensionPath, 'backend');
    const executionCwd = fs.existsSync(backendPath) ? backendPath : context.extensionPath;
    // Options pour child_process.spawn avec CWD et PYTHONPATH configurés
    const spawnOptions = {
        cwd: executionCwd,
        env: {
            ...process.env,
            PYTHONIOENCODING: 'utf-8',
            PYTHONPATH: executionCwd + path.delimiter + (process.env.PYTHONPATH || '')
        }
    };
    // =========================================================================
    // 1. Commande : Démarrer le Serveur FastAPI
    // =========================================================================
    const startServerCmd = vscode.commands.registerCommand('agentdocx-speckit.start_server', () => {
        serverOutputChannel.show(true);
        if (serverProcess) {
            serverOutputChannel.appendLine("[SERVEUR] Le serveur FastAPI est déjà en cours d'exécution.");
            return;
        }
        const scriptPath = path.join(context.extensionPath, 'scripts', 'python', 'start_server.py');
        if (!fs.existsSync(scriptPath)) {
            vscode.window.showErrorMessage(`Script Python introuvable : ${scriptPath}`);
            serverOutputChannel.appendLine(`[ERREUR SERVEUR] Fichier non trouvé : ${scriptPath}`);
            return;
        }
        const pythonCmd = getPythonExecutable();
        serverOutputChannel.appendLine(`[SERVEUR] Démarrage de FastAPI (${pythonCmd} ${scriptPath})...`);
        serverProcess = child_process.spawn(pythonCmd, [scriptPath], spawnOptions);
        serverProcess.stdout?.on('data', (data) => {
            serverOutputChannel.appendLine(`[STDOUT] ${data.toString().trim()}`);
        });
        serverProcess.stderr?.on('data', (data) => {
            serverOutputChannel.appendLine(`[STDERR] ${data.toString().trim()}`);
        });
        serverProcess.on('close', (code) => {
            serverOutputChannel.appendLine(`[SERVEUR] Processus arrêté avec le code ${code}`);
            serverProcess = undefined;
        });
        serverProcess.on('error', (err) => {
            vscode.window.showErrorMessage(`Erreur lors du lancement de FastAPI : ${err.message}`);
            serverOutputChannel.appendLine(`[ERREUR] ${err.message}`);
            serverProcess = undefined;
        });
    });
    // =========================================================================
    // 2. Commande : Arrêter le Serveur FastAPI
    // =========================================================================
    const stopServerCmd = vscode.commands.registerCommand('agentdocx-speckit.stopServer', () => {
        serverOutputChannel.show(true);
        if (!serverProcess) {
            vscode.window.showInformationMessage("Aucun serveur FastAPI n'est en cours d'exécution.");
            return;
        }
        serverProcess.kill();
        serverProcess = undefined;
        serverOutputChannel.appendLine("[SERVEUR] Serveur FastAPI arrêté.");
        vscode.window.showInformationMessage("Serveur FastAPI arrêté.");
    });
    // =========================================================================
    // 3. Commande : Démarrer le Watcher Python
    // =========================================================================
    const startWatcherCmd = vscode.commands.registerCommand('agentdocx-speckit.startWatcher', () => {
        watcherOutputChannel.show(true);
        if (watcherProcess) {
            watcherOutputChannel.appendLine("[WATCHER] Le Watcher Python est déjà en cours d'exécution.");
            return;
        }
        const scriptPath = path.join(context.extensionPath, 'scripts', 'python', 'spec_watcher.py');
        if (!fs.existsSync(scriptPath)) {
            vscode.window.showErrorMessage(`Script Watcher introuvable : ${scriptPath}`);
            watcherOutputChannel.appendLine(`[ERREUR WATCHER] Fichier non trouvé : ${scriptPath}`);
            return;
        }
        const pythonCmd = getPythonExecutable();
        watcherOutputChannel.appendLine(`[WATCHER] Démarrage du Watcher (${pythonCmd} ${scriptPath})...`);
        watcherProcess = child_process.spawn(pythonCmd, [scriptPath], spawnOptions);
        watcherProcess.stdout?.on('data', (data) => {
            watcherOutputChannel.appendLine(`[STDOUT] ${data.toString().trim()}`);
        });
        watcherProcess.stderr?.on('data', (data) => {
            watcherOutputChannel.appendLine(`[STDERR] ${data.toString().trim()}`);
        });
        watcherProcess.on('close', (code) => {
            watcherOutputChannel.appendLine(`[WATCHER] Processus Watcher arrêté avec le code ${code}`);
            watcherProcess = undefined;
        });
        watcherProcess.on('error', (err) => {
            vscode.window.showErrorMessage(`Erreur lors du lancement du Watcher : ${err.message}`);
            watcherOutputChannel.appendLine(`[ERREUR] ${err.message}`);
            watcherProcess = undefined;
        });
    });
    // =========================================================================
    // 4. Commande : Arrêter le Watcher Python
    // =========================================================================
    const stopWatcherCmd = vscode.commands.registerCommand('agentdocx-speckit.stopWatcher', () => {
        watcherOutputChannel.show(true);
        if (!watcherProcess) {
            vscode.window.showInformationMessage("Aucun Watcher Python n'est en cours d'exécution.");
            return;
        }
        watcherProcess.kill();
        watcherProcess = undefined;
        watcherOutputChannel.appendLine("[WATCHER] Watcher Python arrêté.");
        vscode.window.showInformationMessage("Watcher Python arrêté.");
    });
    // =========================================================================
    // 5. Commande : Déclencher la Régénération
    // =========================================================================
    const triggerPipelineCmd = vscode.commands.registerCommand('agentdocx-speckit.triggerPipeline', async () => {
        serverOutputChannel.show(true);
        serverOutputChannel.appendLine("[PIPELINE] Envoi de la demande de régénération à FastAPI...");
        if (!serverProcess) {
            serverOutputChannel.appendLine("[PIPELINE] Serveur éteint. Démarrage automatique...");
            await vscode.commands.executeCommand('agentdocx-speckit.start_server');
            await new Promise((resolve) => setTimeout(resolve, 2000));
        }
        const requestOptions = {
            hostname: '127.0.0.1',
            port: 8000,
            path: '/health',
            method: 'GET'
        };
        const req = http.request(requestOptions, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                serverOutputChannel.appendLine(`[PIPELINE REPONSE ${res.statusCode}] : ${data}`);
                vscode.window.showInformationMessage("Pipeline contacté avec succès !");
            });
        });
        req.on('error', (err) => {
            serverOutputChannel.appendLine(`[PIPELINE ERREUR] ${err.message}`);
            vscode.window.showErrorMessage(`Erreur lors de l'appel au serveur FastAPI : ${err.message}`);
        });
        req.end();
    });
    context.subscriptions.push(startServerCmd, stopServerCmd, startWatcherCmd, stopWatcherCmd, triggerPipelineCmd, serverOutputChannel, watcherOutputChannel);
    // Démarrage automatique au chargement
    vscode.commands.executeCommand('agentdocx-speckit.start_server');
    vscode.commands.executeCommand('agentdocx-speckit.startWatcher');
    // =========================================================================
    // 6. Copilot Instructions — génère .github/copilot-instructions.md
    // =========================================================================
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
        const config = vscode.workspace.getConfiguration('agentdocx-speckit');
        const projectName = config.get('projectName', workspaceFolder.name);
        const apiPort = config.get('apiPort', 8000);
        // Créer/mettre à jour .github/copilot-instructions.md
        const githubDir = path.join(workspaceFolder.uri.fsPath, '.github');
        const instructionsPath = path.join(githubDir, 'copilot-instructions.md');
        const instructions = `# Copilot Instructions — AgentDocx SpecKit

## Task Implementation

When you start implementing a task from tasks.md:

1. **Before starting**, write \`.task_runtime/current-task.json\`:
\`\`\`json
{
  "task_id": "T001",
  "file": "src/models/user.py",
  "status": "in_progress"
}
\`\`\`

2. **When finished**, update \`.task_runtime/current-task.json\`:
\`\`\`json
{
  "task_id": "T001",
  "file": "src/models/user.py",
  "status": "done"
}
\`\`\`

3. **Mark the task** in tasks.md with \`[x]\` when done.

The backend tracks task progress via this JSON file.
`;
        try {
            if (!fs.existsSync(githubDir)) {
                fs.mkdirSync(githubDir, { recursive: true });
            }
            fs.writeFileSync(instructionsPath, instructions, 'utf-8');
            watcherOutputChannel.appendLine(`[TASK-STATE] copilot-instructions.md généré`);
        }
        catch (err) {
            watcherOutputChannel.appendLine(`[TASK-STATE] Erreur écriture instructions: ${err.message}`);
        }
        // =========================================================================
        // 7. Task State Watcher — détecte .task_runtime/current-task.json
        // =========================================================================
        const taskRuntimeDir = path.join(workspaceFolder.uri.fsPath, '.task_runtime');
        if (!fs.existsSync(taskRuntimeDir)) {
            fs.mkdirSync(taskRuntimeDir, { recursive: true });
        }
        const currentTaskWatcher = vscode.workspace.createFileSystemWatcher('**/.task_runtime/current-task.json');
        currentTaskWatcher.onDidChange((uri) => postCurrentTaskState(uri, projectName, apiPort));
        currentTaskWatcher.onDidCreate((uri) => postCurrentTaskState(uri, projectName, apiPort));
        context.subscriptions.push(currentTaskWatcher);
        watcherOutputChannel.appendLine(`[TASK-STATE] Watcher current-task.json actif (projet: ${projectName})`);
    }
}
function deactivate() {
    if (serverProcess) {
        serverProcess.kill();
        serverProcess = undefined;
    }
    if (watcherProcess) {
        watcherProcess.kill();
        watcherProcess = undefined;
    }
}
function parseTasks(content) {
    const lines = content.split('\n');
    const taskStatus = {};
    let currentTaskId = null;
    let currentTaskFile = null;
    let foundInProgress = false;
    for (const line of lines) {
        const match = line.match(/^- \[([ xX~\/])\] (T\d+)\s*(.*)/);
        if (!match)
            continue;
        const checkbox = match[1];
        const taskId = match[2];
        const rest = match[3];
        if (checkbox === 'x' || checkbox === 'X') {
            taskStatus[taskId] = 'done';
        }
        else if (checkbox === '~' || checkbox === '/') {
            taskStatus[taskId] = 'in_progress';
            currentTaskId = taskId;
            foundInProgress = true;
            const fileMatch = rest.match(/(?:in|dans|→|->)\s+([^\s]+\.\w+)/);
            if (fileMatch) {
                currentTaskFile = fileMatch[1];
            }
        }
        else {
            if (!foundInProgress) {
                taskStatus[taskId] = 'in_progress';
                currentTaskId = taskId;
                foundInProgress = true;
                const fileMatch = rest.match(/(?:in|dans|→|->)\s+([^\s]+\.\w+)/);
                if (fileMatch) {
                    currentTaskFile = fileMatch[1];
                }
            }
            else {
                taskStatus[taskId] = 'pending';
            }
        }
    }
    return { currentTaskId, currentTaskFile, taskStatus };
}
let _isUpdatingTasks = false;
function postCurrentTaskState(uri, projectName, apiPort) {
    if (_isUpdatingTasks) {
        return;
    }
    try {
        const content = fs.readFileSync(uri.fsPath, 'utf-8');
        const data = JSON.parse(content);
        const postData = JSON.stringify({
            current_task_id: data.task_id || null,
            current_task_file: data.file || null,
            task_status: data.task_id ? { [data.task_id]: data.status || 'in_progress' } : {},
            started_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        });
        const req = http.request({
            hostname: '127.0.0.1',
            port: apiPort,
            path: `/api/v1/pipeline/task-state/${projectName}`,
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) },
        }, (res) => {
            let d = '';
            res.on('data', (chunk) => { d += chunk; });
            res.on('end', () => {
                watcherOutputChannel.appendLine(`[TASK-STATE] ${data.task_id || '?'} → ${data.status || '?'} (${res.statusCode})`);
            });
        });
        req.on('error', (err) => {
            watcherOutputChannel.appendLine(`[TASK-STATE] Erreur: ${err.message}`);
        });
        req.write(postData);
        req.end();
    }
    catch (err) {
        watcherOutputChannel.appendLine(`[TASK-STATE] Erreur: ${err.message}`);
    }
}
function postTaskState(uri, projectName, apiPort) {
    if (_isUpdatingTasks) {
        return;
    }
    try {
        const content = fs.readFileSync(uri.fsPath, 'utf-8');
        const lines = content.split('\n');
        let modified = false;
        // Si aucune tâche n'est [~], marquer la première [ ] comme [~]
        const hasInProgress = lines.some((l) => /^- \[~\]/.test(l));
        if (!hasInProgress) {
            for (let i = 0; i < lines.length; i++) {
                if (/^- \[ \]/.test(lines[i])) {
                    lines[i] = lines[i].replace('- [ ]', '- [~]');
                    modified = true;
                    watcherOutputChannel.appendLine(`[TASK-STATE] Marqué ${lines[i].match(/T\d+/)?.[0] || '?'} comme in_progress`);
                    break;
                }
            }
        }
        const state = parseTasks(lines.join('\n'));
        if (modified) {
            _isUpdatingTasks = true;
            fs.writeFileSync(uri.fsPath, lines.join('\n'), 'utf-8');
            _isUpdatingTasks = false;
        }
        const postData = JSON.stringify({
            current_task_id: state.currentTaskId,
            current_task_file: state.currentTaskFile,
            task_status: state.taskStatus,
            started_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
        });
        const req = http.request({
            hostname: '127.0.0.1',
            port: apiPort,
            path: `/api/v1/pipeline/task-state/${projectName}`,
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) },
        }, (res) => {
            let data = '';
            res.on('data', (chunk) => { data += chunk; });
            res.on('end', () => {
                watcherOutputChannel.appendLine(`[TASK-STATE] ${state.currentTaskId || 'aucune'} → ${res.statusCode}`);
            });
        });
        req.on('error', (err) => {
            watcherOutputChannel.appendLine(`[TASK-STATE] Erreur: ${err.message}`);
        });
        req.write(postData);
        req.end();
    }
    catch (err) {
        _isUpdatingTasks = false;
        watcherOutputChannel.appendLine(`[TASK-STATE] Erreur: ${err.message}`);
    }
}
//# sourceMappingURL=extension.js.map