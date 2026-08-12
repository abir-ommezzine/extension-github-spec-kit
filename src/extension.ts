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

// Embedded fallback copy of .github/copilot-instructions.md — used when the
// loose file isn't present inside the installed extension package (e.g. a
// packaged .vsix that didn't bundle .github/). Keep this in sync with the
// source file at the repo root; when developing from source, the source file
// on disk is always preferred (see activate() below), so this constant only
// matters for packaged installs.
const EMBEDDED_COPILOT_INSTRUCTIONS: string = "# Copilot Instructions — AgentDocx SpecKit\n\n## CRITICAL: Task Status Reporting\n\nYOU MUST follow this rule EXACTLY:\n\n### Before implementing ANY task:\n\n1. Read tasks.md to find the task you will implement.\n2. Build a full status snapshot of **every** task listed in tasks.md:\n   - The task you are about to start → `\"in_progress\"`\n   - Any task whose checkbox is already `[x]` → `\"done\"`\n   - Every other task → `\"todo\"`\n3. WRITE this file IMMEDIATELY at `.task_runtime/current-task.json`:\n\n```json\n{\n  \"task_id\": \"THE_TASK_ID\",\n  \"file\": \"THE_FILE_PATH\",\n  \"status\": \"in_progress\",\n  \"project_name\": \"PROJECT_NAME\",\n  \"updated_at\": \"2026-08-10T10:30:00.000000+00:00\",\n  \"tasks\": {\n    \"T001\": \"done\",\n    \"T002\": \"done\",\n    \"T003\": \"in_progress\",\n    \"T004\": \"todo\"\n  }\n}\n```\n\nExample:\n```json\n{\n  \"task_id\": \"T004\", \n  \"file\": \"src/routes.py\", \n  \"status\": \"in_progress\",\n  \"project_name\": \"001-cli-todo-manager\",\n  \"updated_at\": \"2026-08-10T10:30:00.000000+00:00\",\n  \"tasks\": {\n    \"T001\": \"done\",\n    \"T002\": \"done\",\n    \"T003\": \"done\",\n    \"T004\": \"in_progress\",\n    \"T005\": \"todo\"\n  }\n}\n```\n\n### After completing the task:\n\n1. Mark the task's checkbox as `[x]` in tasks.md.\n2. Rebuild the full status snapshot the same way as above — this task now reports `\"done\"` instead of `\"in_progress\"`.\n3. WRITE this file at `.task_runtime/current-task.json`:\n\n```json\n{\n  \"task_id\": \"THE_TASK_ID\",\n  \"file\": \"THE_FILE_PATH\",\n  \"status\": \"done\",\n  \"project_name\": \"PROJECT_NAME\",\n  \"updated_at\": \"2026-08-10T10:45:00.000000+00:00\",\n  \"tasks\": {\n    \"T001\": \"done\",\n    \"T002\": \"done\",\n    \"T003\": \"done\",\n    \"T004\": \"todo\"\n  }\n}\n```\n\n### Why the `tasks` map matters\n\nThe backend does **not** read checkboxes in tasks.md to determine ticket status — it only trusts `current-task.json`. If `tasks` is missing, or only lists the task you're currently touching, any task whose transition wasn't caught live (e.g. the backend wasn't running at that moment) will stay stuck in its last known state forever, even though tasks.md shows it as done. Always write the **complete** map, for every task in tasks.md, every single time you write this file — not just the one task you're working on.\n\n### Project Name Guidelines:\n- Extract the project name from the specs directory structure: `specs/PROJECT_NAME/tasks.md`\n- For example: `specs/001-cli-todo-manager/tasks.md` → `project_name: \"001-cli-todo-manager\"`\n- If working directly in specs/tasks.md, use the parent directory name as project name\n\n### NEVER skip this step. The backend depends on this file to track progress and sync status to the kanban board.";

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
    // 6. Copilot Instructions — génère .github/copilot-instructions.md
    // =========================================================================
    const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
    if (workspaceFolder) {
        const githubDir = path.join(workspaceFolder.uri.fsPath, '.github');
        if (!fs.existsSync(githubDir)) {
            fs.mkdirSync(githubDir, { recursive: true });
        }

        const instructionsPath = path.join(githubDir, 'copilot-instructions.md');
        const sourceInstructionsPath = path.join(context.extensionPath, '.github', 'copilot-instructions.md');

        // Prefer the loose file on disk (always correct when running from source,
        // e.g. via F5 / Extension Development Host). Fall back to the embedded
        // copy above when it's missing — e.g. a packaged .vsix that didn't bundle
        // .github/. This guarantees the file is always generated either way.
        let instructionsContent: string;
        if (fs.existsSync(sourceInstructionsPath)) {
            instructionsContent = fs.readFileSync(sourceInstructionsPath, 'utf8');
        } else {
            instructionsContent = EMBEDDED_COPILOT_INSTRUCTIONS;
            watcherOutputChannel.appendLine(`[INIT] Fichier source .github/copilot-instructions.md introuvable dans le package — utilisation de la copie embarquée.`);
        }

        try {
            fs.writeFileSync(instructionsPath, instructionsContent, 'utf8');
            watcherOutputChannel.appendLine(`[INIT] .github/copilot-instructions.md généré avec succès.`);
        } catch (err) {
            watcherOutputChannel.appendLine(`[ERREUR] Échec de la génération des instructions Copilot : ${err}`);
        }
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
