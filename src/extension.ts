import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as child_process from 'child_process';
import * as http from 'http';

let serverProcess: child_process.ChildProcess | undefined;
let watcherProcess: child_process.ChildProcess | undefined;

// 💡 Deux canaux de sortie distincts pour une traçabilité optimale
let serverOutputChannel: vscode.OutputChannel;
let watcherOutputChannel: vscode.OutputChannel;

function getPythonExecutable(): string {
    return process.platform === 'win32' ? 'python' : 'python3';
}

export function activate(context: vscode.ExtensionContext) {
    // Initialisation des deux canaux d'affichage
    serverOutputChannel = vscode.window.createOutputChannel("AgentDocx Server");
    watcherOutputChannel = vscode.window.createOutputChannel("AgentDocx Watcher");

    serverOutputChannel.appendLine("[INIT] Canal Serveur FastAPI prêt.");
    watcherOutputChannel.appendLine("[INIT] Canal Watcher Python prêt.");

    // Détermination du dossier backend s'il existe
    const backendPath = path.join(context.extensionPath, 'backend');
    const executionCwd = fs.existsSync(backendPath) ? backendPath : context.extensionPath;
    const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath || executionCwd;

    // Options pour child_process.spawn avec CWD et PYTHONPATH configurés
    const spawnOptions: child_process.SpawnOptions = {
        cwd: executionCwd,
        env: {
            ...process.env,
            PYTHONIOENCODING: 'utf-8',
            PYTHONPATH: executionCwd + path.delimiter + (process.env.PYTHONPATH || ''),
            SPECKIT_WORKSPACE: workspacePath,
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
        serverOutputChannel.appendLine(`[SERVEUR] Workspace: ${workspacePath}`);

        serverProcess = child_process.spawn(pythonCmd, [scriptPath, workspacePath], spawnOptions);

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

        watcherProcess = child_process.spawn(pythonCmd, [scriptPath, workspacePath], spawnOptions);

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

        const requestOptions: http.RequestOptions = {
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

    context.subscriptions.push(
        startServerCmd,
        stopServerCmd,
        startWatcherCmd,
        stopWatcherCmd,
        triggerPipelineCmd,
        serverOutputChannel,
        watcherOutputChannel
    );

    // Démarrage automatique au chargement
    vscode.commands.executeCommand('agentdocx-speckit.start_server');
    vscode.commands.executeCommand('agentdocx-speckit.startWatcher');

    // =========================================================================
    // 6. Task State Watcher — détecte les changements dans tasks.md
    //    + génère .github/copilot-instructions.md
    // =========================================================================
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
        const config = vscode.workspace.getConfiguration('agentdocx-speckit');
        const projectName = config.get<string>('projectName', workspaceFolder.name);
        const apiPort = config.get<number>('apiPort', 8000);

        // Générer .github/copilot-instructions.md
        const githubDir = path.join(workspaceFolder.uri.fsPath, '.github');
        const instructionsPath = path.join(githubDir, 'copilot-instructions.md');
        const instructions = `# Copilot Instructions — AgentDocx SpecKit

## CRITICAL: Task Status Reporting

YOU MUST follow this rule EXACTLY:

### Before implementing ANY task:

1. Read tasks.md to find the task you will implement
2. WRITE this file IMMEDIATELY at \`.task_runtime/current-task.json\`:

\`\`\`json
{"task_id": "THE_TASK_ID", "file": "THE_FILE_PATH", "status": "in_progress"}
\`\`\`

### After completing the task:

WRITE this file at \`.task_runtime/current-task.json\`:

\`\`\`json
{"task_id": "THE_TASK_ID", "file": "THE_FILE_PATH", "status": "done"}
\`\`\`

### NEVER skip this step. The backend depends on this file to track progress.
`;
        try {
            if (!fs.existsSync(githubDir)) { fs.mkdirSync(githubDir, { recursive: true }); }
            if (!fs.existsSync(instructionsPath)) {
                fs.writeFileSync(instructionsPath, instructions, 'utf-8');
                watcherOutputChannel.appendLine(`[TASK-STATE] copilot-instructions.md généré`);
            }
        } catch (err: any) {
            watcherOutputChannel.appendLine(`[TASK-STATE] Erreur: ${err.message}`);
        }

        // Watcher tasks.md → marque [~] + POST
        const tasksWatcher = vscode.workspace.createFileSystemWatcher('**/tasks.md');
        tasksWatcher.onDidChange((uri) => markInProgressAndPostState(uri, projectName, apiPort));
        tasksWatcher.onDidCreate((uri) => markInProgressAndPostState(uri, projectName, apiPort));
        context.subscriptions.push(tasksWatcher);

        // Watcher current-task.json → POST quand Copilot écrit dedans
        // Utilise un POLLING (plus fiable que le file watcher pour les dot-folders
        // et les écritures rapides par Copilot)
        const taskRuntimeDir = path.join(workspaceFolder.uri.fsPath, '.task_runtime');
        const currentTaskPath = path.join(taskRuntimeDir, 'current-task.json');
        let lastPostedContent = '';
        const pollInterval = setInterval(() => {
            try {
                if (!fs.existsSync(currentTaskPath)) { return; }
                const content = fs.readFileSync(currentTaskPath, 'utf-8').trim();
                if (!content || content === lastPostedContent) { return; }
                lastPostedContent = content;
                const data = JSON.parse(content);
                if (data.task_id && data.status) {
                    postCurrentTaskToBackend(data, projectName, apiPort);
                }
            } catch (err: any) {
                // Fichier partiel (Copilot en train d'écrire) → on réessaiera au prochain tick
                lastPostedContent = '';
            }
        }, 2000);
        context.subscriptions.push({ dispose: () => clearInterval(pollInterval) });

        watcherOutputChannel.appendLine(`[TASK-STATE] Polling current-task.json actif (projet: ${projectName}, port: ${apiPort})`);
    }
}

export function deactivate() {
    if (serverProcess) {
        serverProcess.kill();
        serverProcess = undefined;
    }
    if (watcherProcess) {
        watcherProcess.kill();
        watcherProcess = undefined;
    }
}

// =========================================================================
// Task State — parse tasks.md et POST le JSON au backend
// =========================================================================

interface TaskState {
    currentTaskId: string | null;
    currentTaskFile: string | null;
    taskStatus: Record<string, string>;
}

function parseTasks(content: string): TaskState {
    const lines = content.split('\n');
    const taskStatus: Record<string, string> = {};
    let currentTaskId: string | null = null;
    let currentTaskFile: string | null = null;
    let foundInProgress = false;

    for (const line of lines) {
        const match = line.match(/^- \[([ xX~\/])\] (T\d+)\s*(.*)/);
        if (!match) continue;

        const checkbox = match[1];
        const taskId = match[2];
        const rest = match[3];

        if (checkbox === 'x' || checkbox === 'X') {
            taskStatus[taskId] = 'done';
        } else if (checkbox === '~' || checkbox === '/') {
            taskStatus[taskId] = 'in_progress';
            currentTaskId = taskId;
            foundInProgress = true;
            const fileMatch = rest.match(/(?:in|dans|→|->)\s+([^\s]+\.\w+)/);
            if (fileMatch) { currentTaskFile = fileMatch[1]; }
        } else {
            if (!foundInProgress) {
                taskStatus[taskId] = 'in_progress';
                currentTaskId = taskId;
                foundInProgress = true;
                const fileMatch = rest.match(/(?:in|dans|→|->)\s+([^\s]+\.\w+)/);
                if (fileMatch) { currentTaskFile = fileMatch[1]; }
            } else {
                taskStatus[taskId] = 'pending';
            }
        }
    }

    return { currentTaskId, currentTaskFile, taskStatus };
}

let _isUpdatingTasks = false;

function markInProgressAndPostState(uri: vscode.Uri, projectName: string, apiPort: number) {
    if (_isUpdatingTasks) { return; }

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

        const req = http.request(
            {
                hostname: '127.0.0.1',
                port: apiPort,
                path: `/api/v1/pipeline/task-state/${projectName}`,
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) },
            },
            (res) => {
                let d = '';
                res.on('data', (chunk) => { d += chunk; });
                res.on('end', () => {
                    watcherOutputChannel.appendLine(`[TASK-STATE] ${state.currentTaskId || 'aucune'} → ${res.statusCode}`);
                });
            }
        );
        req.on('error', (err) => {
            watcherOutputChannel.appendLine(`[TASK-STATE] Erreur: ${err.message}`);
        });
        req.write(postData);
        req.end();
    } catch (err: any) {
        _isUpdatingTasks = false;
        watcherOutputChannel.appendLine(`[TASK-STATE] Erreur: ${err.message}`);
    }
}

function postCurrentTaskToBackend(data: any, projectName: string, apiPort: number) {
    try {
        const postData = JSON.stringify({
            current_task_id: data.task_id,
            task_status: { [data.task_id]: data.status },
        });

        const req = http.request(
            {
                hostname: '127.0.0.1',
                port: apiPort,
                path: `/api/v1/pipeline/task-state/${projectName}`,
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(postData) },
            },
            (res) => {
                let d = '';
                res.on('data', (chunk) => { d += chunk; });
                res.on('end', () => {
                    watcherOutputChannel.appendLine(`[CURRENT-TASK] ${data.task_id}=${data.status} → ${res.statusCode}`);
                });
            }
        );
        req.on('error', (err) => {
            watcherOutputChannel.appendLine(`[CURRENT-TASK] Erreur: ${err.message}`);
        });
        req.write(postData);
        req.end();
    } catch (err: any) {
        watcherOutputChannel.appendLine(`[CURRENT-TASK] Erreur: ${err.message}`);
    }
}
