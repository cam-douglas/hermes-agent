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

export type HermesInvocation = {
  command: string;
  argsPrefix: string[];
};

const PYTHON_CANDIDATES = ["python3", "python"] as const;

export async function resolveHermesInvocation(preferred?: string): Promise<HermesInvocation> {
  const tryBin = (preferred?.trim() || HERMES_CLI) || HERMES_CLI;

  try {
    await execFileAsync(tryBin, ["--version"], { timeout: 10_000 });
    return { command: tryBin, argsPrefix: [] };
  } catch (err: unknown) {
    const e = err as NodeJS.ErrnoException;
    if (e.code !== "ENOENT") {
      // Binary exists but --version failed — still use it (matches prior adapter behavior).
      return { command: tryBin, argsPrefix: [] };
    }
  }

  for (const py of PYTHON_CANDIDATES) {
    try {
      await execFileAsync(py, ["-m", "hermes_cli.main", "--version"], { timeout: 15_000 });
      return { command: py, argsPrefix: ["-m", "hermes_cli.main"] };
    } catch (err: unknown) {
      const e = err as NodeJS.ErrnoException;
      if (e.code === "ENOENT") {
        continue;
      }
      // Python found but module invocation failed — try next interpreter.
    }
  }

  const notFound = new Error(`Hermes CLI "${tryBin}" not found in PATH`);
  (notFound as NodeJS.ErrnoException).code = "ENOENT";
  throw notFound;
}
