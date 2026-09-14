import { describe, expect, it } from 'vitest'

import {
  buildKillPersistedSessionCommand,
  buildPersistentRemoteCommand,
  sanitizeTmuxSessionName,
  shellSingleQuote
} from './terminal-persist'

describe('terminal persist remote command', () => {
  it('sanitizes tab ids into tmux-safe session names', () => {
    expect(sanitizeTmuxSessionName('550e8400-e29b-41d4-a716-446655440000')).toBe(
      'h-550e8400-e29b-41d4-a716-446655440000'
    )
    expect(sanitizeTmuxSessionName('term/one;rm -rf /')).toBe('h-term-one-rm-rf')
    expect(sanitizeTmuxSessionName('')).toBe('h-term')
  })

  it('single-quotes values that contain quotes', () => {
    expect(shellSingleQuote("a'b")).toBe(`'a'\\''b'`)
  })

  it('kills only the named tmux session', () => {
    const command = buildKillPersistedSessionCommand('term-one')

    expect(command).toContain("tmux kill-session -t 'h-term-one'")
    expect(command).toContain('2>/dev/null || true')
  })

  it('attaches an existing tmux session and does not auto-resume a live pane', () => {
    const command = buildPersistentRemoteCommand({ persistKey: 'term-one', cwd: '/home/hermes' })

    expect(command).toContain("HERMES_TERM='h-term-one'")
    expect(command).toContain("HERMES_CWD='/home/hermes'")
    expect(command).toContain('tmux attach-session -t "$HERMES_TERM"')
    expect(command).toContain('exec tmux new-session -s "$HERMES_TERM"')
    expect(command).toContain('HERMES_RESUME=')
    expect(command).not.toContain('HERMES_RESUME=1')
    expect(command).not.toMatch(/hermes-term" --session.*--resume/)
  })

  it('resumes Cursor when the tmux session is gone', () => {
    const command = buildPersistentRemoteCommand({
      persistKey: 'term-two',
      cwd: '/work',
      cursorChatId: 'chat-99',
      resumeOnCreate: true
    })

    expect(command).toContain('HERMES_RESUME=1')
    expect(command).toContain("HERMES_CHAT='chat-99'")
    expect(command).toContain('--resume')
    expect(command).toContain('agent --resume "$HERMES_CHAT"')
    expect(command).toContain('agent --continue')
    expect(command).toContain('hermes-term-resume')
  })
})
