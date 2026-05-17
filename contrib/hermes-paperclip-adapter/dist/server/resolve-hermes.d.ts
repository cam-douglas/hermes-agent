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
export type HermesInvocation = {
    command: string;
    argsPrefix: string[];
};
export declare function resolveHermesInvocation(preferred?: string): Promise<HermesInvocation>;
//# sourceMappingURL=resolve-hermes.d.ts.map