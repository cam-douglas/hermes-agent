/** Named tmux sessions so a Desktop quit only detaches the SSH client.
 *  Cursor (or any other process) keeps running on the remote until the user
 *  closes the tab. Reopen reattaches; if the session is gone, resume the
 *  matching Cursor chat (`agent --resume` / `--continue`, not a bash `/resume`). */

export function shellSingleQuote(value: string): string {
  return `'${String(value).replace(/'/g, `'\\''`)}'`
}

export function sanitizeTmuxSessionName(persistKey: string): string {
  const cleaned = String(persistKey || '')
    .trim()
    .replace(/[^A-Za-z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48)

  return `h-${cleaned || 'term'}`
}

export function buildKillPersistedSessionCommand(persistKey: string): string {
  return `tmux kill-session -t ${shellSingleQuote(sanitizeTmuxSessionName(persistKey))} 2>/dev/null || true`
}

export interface PersistentRemoteCommandOptions {
  cwd?: string
  persistKey: string
  cursorChatId?: string
  resumeOnCreate?: boolean
}

export function buildPersistentRemoteCommand({
  cwd = '',
  persistKey,
  cursorChatId = '',
  resumeOnCreate = false
}: PersistentRemoteCommandOptions): string {
  const session = shellSingleQuote(sanitizeTmuxSessionName(persistKey))
  const remoteCwd = shellSingleQuote(String(cwd || '').trim())
  const chat = shellSingleQuote(String(cursorChatId || '').trim())
  const resume = resumeOnCreate ? '--resume' : ''

  return [
    'export PATH="$HOME/bin:$HOME/.local/bin:$PATH"',
    `HERMES_TERM=${session}`,
    `HERMES_CWD=${remoteCwd}`,
    `HERMES_CHAT=${chat}`,
    resume
      ? 'HERMES_RESUME=1'
      : 'HERMES_RESUME=',
    'if [ -x "$HOME/bin/hermes-term" ]; then',
    `  exec "$HOME/bin/hermes-term" --session "$HERMES_TERM" --cwd "$HERMES_CWD" --chat "$HERMES_CHAT" ${resume}`,
    'fi',
    'if [ -n "$HERMES_CWD" ]; then cd "$HERMES_CWD" 2>/dev/null || true; fi',
    'if command -v tmux >/dev/null 2>&1; then',
    '  if tmux has-session -t "$HERMES_TERM" 2>/dev/null; then exec tmux attach-session -t "$HERMES_TERM"; fi',
    '  if [ -n "$HERMES_RESUME" ]; then',
    '    if [ -x "$HOME/bin/hermes-term-resume" ]; then',
    '      exec tmux new-session -s "$HERMES_TERM" ${HERMES_CWD:+-c "$HERMES_CWD"} -- "$HOME/bin/hermes-term-resume"',
    '    fi',
    '    if [ -n "$HERMES_CHAT" ]; then',
    '      exec tmux new-session -s "$HERMES_TERM" ${HERMES_CWD:+-c "$HERMES_CWD"} -- agent --resume "$HERMES_CHAT"',
    '    fi',
    '    exec tmux new-session -s "$HERMES_TERM" ${HERMES_CWD:+-c "$HERMES_CWD"} -- agent --continue',
    '  fi',
    '  exec tmux new-session -s "$HERMES_TERM" ${HERMES_CWD:+-c "$HERMES_CWD"}',
    'fi',
    'if [ -n "$HERMES_RESUME" ]; then',
    '  if [ -x "$HOME/bin/hermes-term-resume" ]; then exec "$HOME/bin/hermes-term-resume"; fi',
    '  if [ -n "$HERMES_CHAT" ]; then exec agent --resume "$HERMES_CHAT"; fi',
    '  exec agent --continue',
    'fi',
    'exec "$SHELL" -l'
  ].join('\n')
}
