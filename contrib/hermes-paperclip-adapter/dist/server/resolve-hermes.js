/**
 * Locate a working Hermes CLI invocation.
 *
 * Mirrors Hermes gateway behavior: prefer a `hermes` shim on PATH, then fall
 * back to `python3 -m hermes_cli.main` when the package is installed but the
 * console script is not exposed (common with venvs / systemd services).
 *
 * Also tries well-known install locations (e.g. ~/.local/bin/hermes) because
 * GUI/IDE-launched Node processes often inherit a minimal PATH that omits
 * `~/.local/bin` even though the shim exists.
 */
import { execFile } from "node:child_process";
import { homedir } from "node:os";
import { platform } from "node:process";
import { promisify } from "node:util";
import { HERMES_CLI } from "../shared/constants.js";
const execFileAsync = promisify(execFile);
const PYTHON_CANDIDATES = ["python3", "python"];
/** Extra shims to try when bare ``hermes`` is not on PATH (minimal GUI PATH). */
function extraHermesShimPaths(preferred) {
    const out = [];
    const push = (s) => {
        const t = s?.trim();
        if (t && !out.includes(t)) {
            out.push(t);
        }
    };
    push(process.env.HERMES_CLI);
    push(process.env.HERMES_COMMAND);
    const repo = process.env.HERMES_AGENT_REPO?.trim();
    if (repo && platform !== "win32") {
        push(`${repo}/venv/bin/hermes`);
        push(`${repo}/.venv/bin/hermes`);
    }
    const home = homedir();
    if (home) {
        if (platform === "win32") {
            push(`${home}\\.local\\bin\\hermes.exe`);
        }
        else {
            push(`${home}/.local/bin/hermes`);
        }
    }
    if (platform !== "win32") {
        push("/opt/homebrew/bin/hermes");
        push("/usr/local/bin/hermes");
    }
    return out.filter((p) => p !== preferred);
}
async function tryShim(path) {
    try {
        await execFileAsync(path, ["--version"], { timeout: 10_000 });
        return { command: path, argsPrefix: [] };
    }
    catch (err) {
        const e = err;
        if (e.code !== "ENOENT") {
            return { command: path, argsPrefix: [] };
        }
        return null;
    }
}
export async function resolveHermesInvocation(preferred) {
    const first = (preferred?.trim() || HERMES_CLI) || HERMES_CLI;
    const attemptPaths = [first, ...extraHermesShimPaths(first)];
    for (const path of attemptPaths) {
        if (!path) {
            continue;
        }
        const hit = await tryShim(path);
        if (hit) {
            return hit;
        }
    }
    for (const py of PYTHON_CANDIDATES) {
        try {
            await execFileAsync(py, ["-m", "hermes_cli.main", "--version"], { timeout: 15_000 });
            return { command: py, argsPrefix: ["-m", "hermes_cli.main"] };
        }
        catch (err) {
            const e = err;
            if (e.code === "ENOENT") {
                continue;
            }
        }
    }
    const notFound = new Error(`Hermes CLI "${first}" not found in PATH`);
    notFound.code = "ENOENT";
    throw notFound;
}
//# sourceMappingURL=resolve-hermes.js.map