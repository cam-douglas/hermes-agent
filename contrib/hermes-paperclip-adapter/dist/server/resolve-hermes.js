/**
 * Locate a working Hermes CLI invocation.
 *
 * Mirrors Hermes gateway behavior: prefer a `hermes` shim on PATH, then fall
 * back to `python3 -m hermes_cli.main` when the package is installed but the
 * console script is not exposed (common with venvs / systemd services).
 */
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { HERMES_CLI } from "../shared/constants.js";
const execFileAsync = promisify(execFile);
const PYTHON_CANDIDATES = ["python3", "python"];
export async function resolveHermesInvocation(preferred) {
    const tryBin = (preferred?.trim() || HERMES_CLI) || HERMES_CLI;
    try {
        await execFileAsync(tryBin, ["--version"], { timeout: 10_000 });
        return { command: tryBin, argsPrefix: [] };
    }
    catch (err) {
        const e = err;
        if (e.code !== "ENOENT") {
            // Binary exists but --version failed — still use it (matches prior adapter behavior).
            return { command: tryBin, argsPrefix: [] };
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
            // Python found but module invocation failed — try next interpreter.
        }
    }
    const notFound = new Error(`Hermes CLI "${tryBin}" not found in PATH`);
    notFound.code = "ENOENT";
    throw notFound;
}
//# sourceMappingURL=resolve-hermes.js.map