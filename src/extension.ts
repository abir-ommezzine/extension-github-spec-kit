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

        // =========================================================================
        // 6. Task State — removed old tasks.md watcher + parseTasks logic.
        //    Status is now driven exclusively by .task_runtime/current-task.json
        //    which the backend file watcher picks up automatically.
        // =========================================================================
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

// Task State interface kept for potential future use
interface TaskState {
    currentTaskId: string | null;
    currentTaskFile: string | null;
    taskStatus: Record<string, string>;
}
