import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import * as child_process from 'child_process';
import * as http from 'http';

let serverProcess: child_process.ChildProcess | undefined;
let watcherProcess: child_process.ChildProcess | undefined;
let frontendProcess: child_process.ChildProcess | undefined;

// 💡 Trois canaux de sortie distincts pour une traçabilité optimale
let serverOutputChannel: vscode.OutputChannel;
let watcherOutputChannel: vscode.OutputChannel;
let frontendOutputChannel: vscode.OutputChannel;

function getPythonExecutable(): string {
    return process.platform === 'win32' ? 'python' : 'python3';
}

// Sur Windows, spawn('npm.cmd', ...) sans shell:true échoue avec EINVAL —
// CreateProcess ne sait pas exécuter un .cmd directement, il faut passer par
// cmd.exe. Node ne fait pas cette traduction tout seul en dehors du shell.
// Tous les arguments passés ici sont des littéraux fixes (jamais de contenu
// utilisateur/fichier), donc l'activation du shell est sans risque d'injection.
function spawnNpm(args: string[], cwd: string): child_process.ChildProcess {
    if (process.platform === 'win32') {
        return child_process.spawn('npm', args, { cwd, shell: true });
    }
    return child_process.spawn('npm', args, { cwd });
}

// Localise le dossier `frontend/` réel : soit une jonction/dossier du
// workspace (projet enfant, ou ce repo source lui-même), soit un dossier
// bundlé dans l'extension packagée (secours, généralement absent du .vsix).
function resolveFrontendPath(context: vscode.ExtensionContext, workspacePath: string): string | undefined {
    const candidates = [
        path.join(workspacePath, 'frontend'),
        path.join(context.extensionPath, 'frontend'),
    ];
    for (const candidate of candidates) {
        if (fs.existsSync(path.join(candidate, 'package.json'))) {
            return candidate;
        }
    }
    return undefined;
}

// Exécute une commande npm dans `cwd` en streamant sa sortie dans `channel`,
// et résout avec le code de sortie du process.
function runNpmCommand(args: string[], cwd: string, channel: vscode.OutputChannel): Promise<number> {
    return new Promise((resolve) => {
        channel.appendLine(`[FRONTEND] $ npm ${args.join(' ')}`);

        let proc: child_process.ChildProcess;
        try {
            proc = spawnNpm(args, cwd);
        } catch (err) {
            channel.appendLine(`[FRONTEND] Erreur lors du lancement de npm ${args.join(' ')} : ${err}`);
            resolve(1);
            return;
        }

        proc.stdout?.on('data', (data) => channel.append(data.toString()));
        proc.stderr?.on('data', (data) => channel.append(data.toString()));

        proc.on('close', (code) => resolve(code ?? 1));
        proc.on('error', (err) => {
            channel.appendLine(`[FRONTEND] Erreur lors de l'exécution de npm ${args.join(' ')} : ${err.message}`);
            resolve(1);
        });
    });
}

// ÉTAPE 3 de configFrontEnd.pdf : le script "start" DOIT être préfixé par
// cross-env, sinon Windows échoue avec "'PORT' n'est pas reconnu...".
function ensureCrossEnvInStartScript(frontendPath: string, channel: vscode.OutputChannel): void {
    const pkgPath = path.join(frontendPath, 'package.json');
    try {
        const raw = fs.readFileSync(pkgPath, 'utf8');
        const pkg = JSON.parse(raw);
        const start: string = pkg.scripts?.start || '';
        if (start && !start.includes('cross-env')) {
            pkg.scripts.start = `cross-env ${start}`;
            fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n', 'utf8');
            channel.appendLine(`[FRONTEND] package.json corrigé : "start" utilise désormais cross-env.`);
        }
    } catch (err) {
        channel.appendLine(`[FRONTEND] Impossible de vérifier/corriger package.json : ${err}`);
    }
}

// Réparation automatique complète, reproduisant exactement les étapes de
// configFrontEnd.pdf (nettoyage, cross-env, ajv@8.12.0, réinstallation).
async function repairFrontendDependencies(frontendPath: string, channel: vscode.OutputChannel): Promise<boolean> {
    channel.appendLine("[FRONTEND] ==== Réparation automatique des dépendances (voir configFrontEnd.pdf) ====");

    for (const dir of ['node_modules', 'package-lock.json']) {
        const target = path.join(frontendPath, dir);
        if (fs.existsSync(target)) {
            channel.appendLine(`[FRONTEND] Suppression de ${dir}...`);
            try {
                fs.rmSync(target, { recursive: true, force: true });
            } catch (err) {
                channel.appendLine(`[FRONTEND] Échec de la suppression de ${dir} : ${err}`);
            }
        }
    }

    await runNpmCommand(['cache', 'clean', '--force'], frontendPath, channel);
    await runNpmCommand(['install', 'cross-env', '--save-dev', '--legacy-peer-deps'], frontendPath, channel);
    ensureCrossEnvInStartScript(frontendPath, channel);
    await runNpmCommand(['install', 'ajv@8.12.0', '--legacy-peer-deps'], frontendPath, channel);
    const installCode = await runNpmCommand(['install', '--legacy-peer-deps'], frontendPath, channel);

    if (installCode !== 0) {
        channel.appendLine(`[FRONTEND] npm install --legacy-peer-deps a échoué (code ${installCode}).`);
        channel.appendLine(`[FRONTEND] Vérifiez votre version de Node.js ("node --version" — Node 18 ou 20 recommandé, voir configFrontEnd.pdf Option C).`);
        return false;
    }

    channel.appendLine("[FRONTEND] ==== Réparation terminée ====");
    return true;
}

// Lance "npm start" et observe stdout/stderr pour détecter un démarrage
// réussi (webpack compilé) ou un échec connu (PORT non reconnu, module ajv/
// cross-env manquant, erreur npm) sans dépendre d'un délai arbitraire fixe.
function tryStartFrontendDevServer(frontendPath: string, channel: vscode.OutputChannel): Promise<'ok' | 'failed'> {
    return new Promise((resolve) => {
        channel.appendLine(`[FRONTEND] Démarrage de "npm start" dans ${frontendPath}...`);

        let proc: child_process.ChildProcess;
        try {
            proc = spawnNpm(['start'], frontendPath);
        } catch (err) {
            channel.appendLine(`[FRONTEND] Erreur lors du lancement de "npm start" : ${err}`);
            resolve('failed');
            return;
        }

        let settled = false;
        const failurePatterns = [
            /is not recognized as an internal or external command/i,
            /Cannot find module ['"]ajv/i,
            /Cannot find module ['"]cross-env/i,
            /npm ERR!/,
            /ERESOLVE/,
        ];

        const succeed = () => {
            if (settled) { return; }
            settled = true;
            frontendProcess = proc;
            resolve('ok');
        };
        const fail = () => {
            if (settled) { return; }
            settled = true;
            try { proc.kill(); } catch { /* déjà arrêté */ }
            resolve('failed');
        };

        const onOutput = (data: Buffer) => {
            const text = data.toString();
            channel.append(text);
            if (/compiled successfully|webpack compiled|you can now view/i.test(text)) {
                succeed();
            } else if (failurePatterns.some((re) => re.test(text))) {
                fail();
            }
        };

        proc.stdout?.on('data', onOutput);
        proc.stderr?.on('data', onOutput);

        proc.on('close', (code) => {
            channel.appendLine(`[FRONTEND] Processus "npm start" terminé avec le code ${code}`);
            if (frontendProcess === proc) {
                frontendProcess = undefined;
            }
            fail();
        });

        proc.on('error', (err) => {
            channel.appendLine(`[FRONTEND] Erreur au lancement : ${err.message}`);
            fail();
        });

        // Filet de sécurité : passé 90s sans signal net, on suppose que la
        // machine est simplement lente et on laisse le serveur continuer.
        setTimeout(() => {
            if (!settled) {
                channel.appendLine("[FRONTEND] Aucun signal de succès/échec net après 90s — démarrage lent supposé, on continue.");
                succeed();
            }
        }, 90000);
    });
}

async function startFrontendInternal(context: vscode.ExtensionContext, workspacePath: string): Promise<void> {
    frontendOutputChannel.show(true);

    if (frontendProcess) {
        frontendOutputChannel.appendLine("[FRONTEND] Le frontend est déjà en cours d'exécution.");
        return;
    }

    const frontendPath = resolveFrontendPath(context, workspacePath);
    if (!frontendPath) {
        vscode.window.showErrorMessage("Dossier 'frontend' introuvable (ni dans le workspace, ni dans l'extension).");
        frontendOutputChannel.appendLine("[ERREUR FRONTEND] Dossier 'frontend' introuvable.");
        return;
    }

    frontendOutputChannel.appendLine(`[FRONTEND] Dossier détecté : ${frontendPath}`);

    if (!fs.existsSync(path.join(frontendPath, 'node_modules'))) {
        frontendOutputChannel.appendLine("[FRONTEND] node_modules absent — installation initiale...");
        await runNpmCommand(['install', '--legacy-peer-deps'], frontendPath, frontendOutputChannel);
    }

    let result = await tryStartFrontendDevServer(frontendPath, frontendOutputChannel);

    if (result === 'failed') {
        frontendOutputChannel.appendLine("[FRONTEND] Échec du démarrage — lancement de la réparation automatique (voir configFrontEnd.pdf)...");
        const repaired = await repairFrontendDependencies(frontendPath, frontendOutputChannel);
        if (!repaired) {
            vscode.window.showErrorMessage("Échec de la réparation automatique du frontend. Consultez le canal 'AgentDocx Frontend' et configFrontEnd.pdf.");
            return;
        }
        result = await tryStartFrontendDevServer(frontendPath, frontendOutputChannel);
    }

    if (result === 'ok') {
        vscode.window.showInformationMessage("Frontend React démarré (http://localhost:5000).");
    } else {
        vscode.window.showErrorMessage("Impossible de démarrer le frontend même après réparation automatique. Consultez le canal 'AgentDocx Frontend'.");
    }
}

// Embedded fallback copy of .github/copilot-instructions.md — used when the
// loose file isn't present inside the installed extension package (e.g. a
// packaged .vsix that didn't bundle .github/). Keep this in sync with the
// source file at the repo root; when developing from source, the source file
// on disk is always preferred (see activate() below), so this constant only
// matters for packaged installs.
const EMBEDDED_COPILOT_INSTRUCTIONS: string = "# Copilot Instructions — AgentDocx SpecKit\n\n## CRITICAL: Task Status Reporting\n\nYOU MUST follow this rule EXACTLY:\n\n### Before implementing ANY task:\n\n1. Read tasks.md to find the task you will implement.\n2. Build a full status snapshot of **every** task listed in tasks.md:\n   - The task you are about to start → `\"in_progress\"`\n   - Any task whose checkbox is already `[x]` → `\"done\"`\n   - Every other task → `\"todo\"`\n3. WRITE this file IMMEDIATELY at `.task_runtime/current-task.json`:\n\n```json\n{\n  \"task_id\": \"THE_TASK_ID\",\n  \"file\": \"THE_FILE_PATH\",\n  \"status\": \"in_progress\",\n  \"project_name\": \"PROJECT_NAME\",\n  \"updated_at\": \"2026-08-10T10:30:00.000000+00:00\",\n  \"tasks\": {\n    \"T001\": \"done\",\n    \"T002\": \"done\",\n    \"T003\": \"in_progress\",\n    \"T004\": \"todo\"\n  }\n}\n```\n\nExample:\n```json\n{\n  \"task_id\": \"T004\", \n  \"file\": \"src/routes.py\", \n  \"status\": \"in_progress\",\n  \"project_name\": \"001-cli-todo-manager\",\n  \"updated_at\": \"2026-08-10T10:30:00.000000+00:00\",\n  \"tasks\": {\n    \"T001\": \"done\",\n    \"T002\": \"done\",\n    \"T003\": \"done\",\n    \"T004\": \"in_progress\",\n    \"T005\": \"todo\"\n  }\n}\n```\n\n### After completing the task:\n\n1. Mark the task's checkbox as `[x]` in tasks.md.\n2. Rebuild the full status snapshot the same way as above — this task now reports `\"done\"` instead of `\"in_progress\"`.\n3. WRITE this file at `.task_runtime/current-task.json`:\n\n```json\n{\n  \"task_id\": \"THE_TASK_ID\",\n  \"file\": \"THE_FILE_PATH\",\n  \"status\": \"done\",\n  \"project_name\": \"PROJECT_NAME\",\n  \"updated_at\": \"2026-08-10T10:45:00.000000+00:00\",\n  \"tasks\": {\n    \"T001\": \"done\",\n    \"T002\": \"done\",\n    \"T003\": \"done\",\n    \"T004\": \"todo\"\n  }\n}\n```\n\n### Why the `tasks` map matters\n\nThe backend does **not** read checkboxes in tasks.md to determine ticket status — it only trusts `current-task.json`. If `tasks` is missing, or only lists the task you're currently touching, any task whose transition wasn't caught live (e.g. the backend wasn't running at that moment) will stay stuck in its last known state forever, even though tasks.md shows it as done. Always write the **complete** map, for every task in tasks.md, every single time you write this file — not just the one task you're working on.\n\n### Project Name Guidelines:\n- Extract the project name from the specs directory structure: `specs/PROJECT_NAME/tasks.md`\n- For example: `specs/001-cli-todo-manager/tasks.md` → `project_name: \"001-cli-todo-manager\"`\n- If working directly in specs/tasks.md, use the parent directory name as project name\n\n### NEVER skip this step. The backend depends on this file to track progress and sync status to the kanban board.";

export function activate(context: vscode.ExtensionContext) {
    // Initialisation des trois canaux d'affichage
    serverOutputChannel = vscode.window.createOutputChannel("AgentDocx Server");
    watcherOutputChannel = vscode.window.createOutputChannel("AgentDocx Watcher");
    frontendOutputChannel = vscode.window.createOutputChannel("AgentDocx Frontend");

    serverOutputChannel.appendLine("[INIT] Canal Serveur FastAPI prêt.");
    watcherOutputChannel.appendLine("[INIT] Canal Watcher Python prêt.");
    frontendOutputChannel.appendLine("[INIT] Canal Frontend React prêt.");

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

    // Le Watcher tourne indéfiniment et ne fait jamais os.chdir() (contrairement à
    // start_server.py). S'il gardait `executionCwd` (le dossier d'installation de
    // l'extension quand aucun `backend/` n'est bundlé) comme répertoire courant,
    // Windows verrouillerait ce dossier tant que le process vit, et
    // "Install from VSIX" échouerait avec EBUSY à chaque mise à jour de
    // l'extension. On le fait donc démarrer directement dans le workspace.
    const watcherSpawnOptions: child_process.SpawnOptions = {
        ...spawnOptions,
        cwd: workspacePath,
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

        watcherProcess = child_process.spawn(pythonCmd, [scriptPath, workspacePath], watcherSpawnOptions);

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

    // =========================================================================
    // 5bis. Commande : Démarrer le Frontend React
    // =========================================================================
    const startFrontendCmd = vscode.commands.registerCommand('agentdocx-speckit.startFrontend', () => {
        startFrontendInternal(context, workspacePath);
    });

    // =========================================================================
    // 5ter. Commande : Arrêter le Frontend React
    // =========================================================================
    const stopFrontendCmd = vscode.commands.registerCommand('agentdocx-speckit.stopFrontend', () => {
        frontendOutputChannel.show(true);
        if (!frontendProcess) {
            vscode.window.showInformationMessage("Aucun frontend n'est en cours d'exécution.");
            return;
        }

        frontendProcess.kill();
        frontendProcess = undefined;
        frontendOutputChannel.appendLine("[FRONTEND] Frontend arrêté.");
        vscode.window.showInformationMessage("Frontend arrêté.");
    });

    context.subscriptions.push(
        startServerCmd,
        stopServerCmd,
        startWatcherCmd,
        stopWatcherCmd,
        triggerPipelineCmd,
        startFrontendCmd,
        stopFrontendCmd,
        serverOutputChannel,
        watcherOutputChannel,
        frontendOutputChannel
    );

    // Démarrage automatique au chargement
    vscode.commands.executeCommand('agentdocx-speckit.start_server');
    vscode.commands.executeCommand('agentdocx-speckit.startWatcher');
    vscode.commands.executeCommand('agentdocx-speckit.startFrontend');

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
    if (frontendProcess) {
        frontendProcess.kill();
        frontendProcess = undefined;
    }
}

// Task State interface kept for potential future use
interface TaskState {
    currentTaskId: string | null;
    currentTaskFile: string | null;
    taskStatus: Record<string, string>;
}
