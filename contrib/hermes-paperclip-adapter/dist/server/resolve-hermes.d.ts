/**
 * Locate a working Hermes CLI invocation.
 *
 * Mirrors Hermes gateway behavior: prefer a `hermes` shim on PATH, then fall
 * back to `python3 -m hermes_cli.main` when the package is installed but the
 * console script is not exposed (common with venvs / systemd services).
 */
export type HermesInvocation = {
    command: string;
    argsPrefix: string[];
};
export declare function resolveHermesInvocation(preferred?: string): Promise<HermesInvocation>;
//# sourceMappingURL=resolve-hermes.d.ts.map