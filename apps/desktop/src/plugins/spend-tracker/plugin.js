/**
 * Spend tracker for the Desktop status bar.
 * Replace this file on the Mac at ~/.hermes/desktop-plugins/spend-tracker/plugin.js
 * then Command Palette → Reload desktop plugins.
 */
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  host,
  STATUSBAR_AREAS
} from '@hermes/plugin-sdk'
import { useEffect, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'spend-tracker'
const POLL_MS = 5000

const CSS = `
.hermes-spend-chip{display:inline-flex;align-items:center;gap:5px;height:100%;padding:0 6px;border:0;background:transparent;color:var(--ui-text-secondary);font-size:11px;line-height:1;cursor:pointer}
.hermes-spend-chip:hover{background:var(--chrome-action-hover);color:var(--ui-text-primary)}
.hermes-spend-chip[data-tone=over]{color:var(--ui-danger, var(--destructive))}
.hermes-spend-chip[data-tone=warn]{color:#d97706}
.hermes-spend-num{font-variant-numeric:tabular-nums}
.hermes-spend-panel{width:20rem;max-width:calc(100vw - 24px);display:flex;flex-direction:column;max-height:min(24rem,70vh);font-size:12px}
.hermes-spend-head{display:grid;gap:8px;padding:12px;border-bottom:1px solid var(--ui-stroke-secondary, rgba(127,127,127,.25));flex:0 0 auto}
.hermes-spend-title{margin:0;font-weight:600;color:var(--ui-text-primary)}
.hermes-spend-row{display:flex;justify-content:space-between;gap:12px;min-width:0}
.hermes-spend-row span:first-child{color:var(--ui-text-tertiary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hermes-spend-row span:last-child{color:var(--ui-text-primary);font-variant-numeric:tabular-nums;flex-shrink:0}
.hermes-spend-hist{flex:1 1 auto;min-height:10rem;max-height:16rem;overflow-y:auto;padding:12px}
.hermes-spend-hist p{margin:0 0 8px;font-size:11px;font-weight:600;color:var(--ui-text-tertiary)}
.hermes-spend-hist ol{margin:0;padding:0;list-style:none;display:grid;gap:6px}
.hermes-spend-hist li{display:flex;justify-content:space-between;gap:8px;font-size:11px;min-width:0}
.hermes-spend-hist li span:first-child{color:var(--ui-text-tertiary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hermes-spend-hist li span:last-child{color:var(--ui-text-primary);font-variant-numeric:tabular-nums;flex-shrink:0}
`

function money(value) {
  if (value == null || Number.isNaN(Number(value))) return '$—'
  const n = Number(value)
  if (n === 0) return '$0.00'
  if (n < 0.01) return `$${n.toFixed(4)}`
  return `$${n.toFixed(2)}`
}

function countdown(seconds, over) {
  if (!over) return 'paid now'
  const s = Math.max(0, Math.round(Number(seconds) || 0))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}

function toneOf(spend) {
  if (spend?.over_limit) return 'over'
  const hour = Number(spend?.hour_usd)
  const limit = Number(spend?.limit_usd) || 1
  if (Number.isFinite(hour) && hour / limit >= 0.7) return 'warn'
  return 'ok'
}

function Row({ label, value }) {
  return jsxs('div', { className: 'hermes-spend-row', children: [jsx('span', { children: label }), jsx('span', { children: value })] })
}

function SpendChip() {
  const [spend, setSpend] = useState(null)
  const [open, setOpen] = useState(false)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    let cancelled = false
    let timer = 0
    const poll = async () => {
      try {
        const next = await host.request('spend.snapshot', { session_id: '' })
        if (!cancelled) setSpend(next || null)
        await pullFromVps()
      } catch {
        if (!cancelled) setSpend(prev => prev)
      }
      if (!cancelled) timer = window.setTimeout(() => void poll(), POLL_MS)
    }
    void poll()
    const tick = window.setInterval(() => setNow(Date.now()), 1000)
    return () => {
      cancelled = true
      window.clearTimeout(timer)
      window.clearInterval(tick)
    }
  }, [])

  const over = spend?.over_limit === true
  const hour = spend?.hour_usd
  const limit = spend?.limit_usd ?? 1
  let resetIn = 0
  if (over) {
    if (spend?.reset_at) {
      const until = Date.parse(spend.reset_at) - now
      resetIn = Number.isNaN(until) ? spend.reset_in_s || 0 : Math.max(0, until / 1000)
    } else {
      resetIn = spend?.reset_in_s || 0
    }
  }
  const label = hour == null ? '$—/hr' : `${money(hour)}/${money(limit)}`
  const history = Array.isArray(spend?.history) ? spend.history.slice().reverse() : []
  const tone = toneOf(spend)
  const title = over
    ? `Free fallback · paid models in ${countdown(resetIn, true)}`
    : `Hourly spend ${label} · click for session, day, last request, and 24h history`

  return jsxs(DropdownMenu, {
    modal: false,
    open,
    onOpenChange: setOpen,
    children: [
      jsx(DropdownMenuTrigger, {
        asChild: true,
        children: jsxs('button', {
          type: 'button',
          className: 'hermes-spend-chip',
          'data-tone': tone,
          'data-slot': 'hourly-spend',
          title,
          children: [
            jsx('span', { 'aria-hidden': true, children: '💳' }),
            jsx('span', { className: 'hermes-spend-num', children: label }),
            over ? jsx('span', { className: 'hermes-spend-num', children: countdown(resetIn, true) }) : null
          ]
        })
      }),
      jsx(DropdownMenuContent, {
        side: 'top',
        align: 'end',
        sideOffset: 8,
        className: 'w-80 p-0',
        'aria-label': 'Spend',
        children: jsxs('div', {
          className: 'hermes-spend-panel',
          children: [
            jsxs('div', {
              className: 'hermes-spend-head',
              children: [
                jsx('p', { className: 'hermes-spend-title', children: 'Spend' }),
                jsx(Row, { label: 'This chat', value: money(spend?.session_usd) }),
                jsx(Row, { label: 'Past hour (all chats)', value: `${money(hour)} / ${money(limit)}` }),
                jsx(Row, { label: 'Past day (all chats)', value: money(spend?.day_usd) }),
                jsx(Row, { label: 'Last request', value: money(spend?.last_request_usd) }),
                jsx(Row, {
                  label: 'Paid models reset',
                  value: over ? countdown(resetIn, true) : 'paid route active'
                })
              ]
            }),
            jsxs('div', {
              className: 'hermes-spend-hist',
              children: [
                jsx('p', { children: 'Last 24 hours' }),
                history.length === 0
                  ? jsx('div', { children: 'No spend samples yet.' })
                  : jsx('ol', {
                      children: history.map((row, index) =>
                        jsxs(
                          'li',
                          {
                            children: [
                              jsx('span', {
                                children: `${String(row.at || '').replace('T', ' ').replace('Z', '')} · ${
                                  row.mode || '—'
                                }`
                              }),
                              jsx('span', {
                                children: `${money(row.hour_usd)}/hr · ${money(row.last_request_usd)} req`
                              })
                            ]
                          },
                          row.at || row.ts || index
                        )
                      )
                    })
              ]
            })
          ]
        })
      })
    ]
  })
}

const SHA_KEY = 'hermes.plugin.spend-tracker.sha256'
const RESCUE_IDS = [ID, 'vps-ui-sync', 'task-list']
const forcedWrite = new Set()

async function pullPlugin(desktop, root, id) {
  let src
  try {
    src = await host.request('desktop.plugin.source', { id })
  } catch {
    return
  }
  const next = src?.content
  const sha = src?.sha256
  if (!next || !sha) return
  const storageKey = id === ID ? SHA_KEY : `hermes.vps-ui-sync.sha.${id}`
  const force = id === 'vps-ui-sync' && !next.includes('probe') && !forcedWrite.has(id)
  try {
    if (!force && window.localStorage.getItem(storageKey) === sha) return
  } catch {
    // write anyway
  }
  const path = `${String(root).replace(/\/$/, '')}/${id}/plugin.js`
  try {
    await desktop.writeTextFile(path, next)
    if (force) forcedWrite.add(id)
    window.localStorage.setItem(storageKey, sha)
  } catch {
    // folder missing on Mac
  }
}

async function pullFromVps() {
  const desktop = typeof window !== 'undefined' ? window.hermesDesktop : null
  if (!desktop?.desktopPluginsRoot || !desktop.writeTextFile) return
  const root = await desktop.desktopPluginsRoot()
  if (!root) return
  for (const id of RESCUE_IDS) await pullPlugin(desktop, String(root).replace(/\/$/, ''), id)
}

export default {
  id: ID,
  name: 'Spend tracker',
  description: 'Status-bar spend next to permissions: session, hour, day, last request, reset, 24h history.',
  defaultEnabled: true,
  register(ctx) {
    const style = document.createElement('style')
    style.textContent = CSS
    document.head.append(style)
    const timer = window.setInterval(() => void pullFromVps(), POLL_MS)
    ctx.onDispose(() => {
      style.remove()
      window.clearInterval(timer)
    })
    ctx.register({
      id: 'hourly-spend',
      area: STATUSBAR_AREAS.right,
      order: 90,
      render: () => jsx(SpendChip, {})
    })
    registerTaskListFromSpend(ctx)
    registerMessagingFromSpend(ctx)
    void pullFromVps()
  }
}

const TASK_FLAG = '__hermesTaskListUi'
const TASK_ADD = 'hermes-task-list-add'
const TASK_POLL_MS = 2000
const TASK_CSS = `
.hermes-tasks{display:flex;flex-direction:column;gap:4px;padding:6px 8px 8px;max-height:min(28vh,16rem);overflow-y:auto}
.hermes-tasks-head{display:flex;align-items:center;gap:6px;min-width:0}
.hermes-tasks-title{margin:0;flex:1 1 auto;min-width:0;font-size:11px;font-weight:600;color:var(--ui-text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hermes-tasks-btn{display:inline-flex;align-items:center;justify-content:center;width:1.35rem;height:1.35rem;padding:0;border:0;border-radius:6px;background:transparent;color:var(--ui-text-tertiary);cursor:pointer;font-size:14px;line-height:1}
.hermes-tasks-btn:hover{background:var(--chrome-action-hover);color:var(--ui-text-primary)}
.hermes-tasks-btn[data-kind=danger]:hover{color:var(--ui-danger, var(--destructive))}
.hermes-tasks-row{display:flex;align-items:center;gap:4px;min-width:0}
.hermes-tasks-text{flex:1 1 auto;min-width:0;border:0;background:transparent;color:var(--ui-text-primary);font-size:12px;line-height:1.35;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hermes-tasks-text[data-status=completed]{color:var(--ui-text-tertiary);text-decoration:line-through}
.hermes-tasks-text[data-status=in_progress]{color:var(--ui-accent)}
.hermes-tasks-input{flex:1 1 auto;min-width:0;height:1.5rem;padding:0 6px;border:1px solid color-mix(in srgb,var(--ui-accent) 35%,transparent);border-radius:6px;background:transparent;color:var(--ui-text-primary);font-size:12px}
.hermes-tasks-empty{margin:0;font-size:11px;color:var(--ui-text-tertiary)}
.hermes-tasks-hint{margin:0;font-size:10px;color:var(--ui-text-tertiary)}
[data-hermes-native-todos=hidden]{display:none!important}
`

function taskSessionId() {
  const state = host.state || {}
  try {
    return String(state.focusedSessionId?.get?.() || state.activeSessionId?.get?.() || '')
  } catch {
    return ''
  }
}

function SpendTaskPanel() {
  const [sid, setSid] = useState(() => taskSessionId())
  const [state, setState] = useState({ todos: [], keep_open: false, revision: 0 })
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState('')
  const [editing, setEditing] = useState('')
  const [editText, setEditText] = useState('')

  useEffect(() => {
    let cancelled = false
    const unsubs = []
    const applySid = () => {
      if (!cancelled) setSid(taskSessionId())
    }
    for (const atom of [host.state?.focusedSessionId, host.state?.activeSessionId]) {
      if (atom && typeof atom.listen === 'function') unsubs.push(atom.listen(applySid))
    }
    const refresh = async () => {
      applySid()
      const sessionId = taskSessionId()
      if (!sessionId) {
        if (!cancelled) setState({ todos: [], keep_open: false, revision: 0 })
        return
      }
      try {
        const next = await host.request('todo.get', { session_id: sessionId })
        if (!cancelled && next) setState(next)
      } catch {
        // RPC not on this serve yet
      }
    }
    void refresh()
    const timer = window.setInterval(() => void refresh(), TASK_POLL_MS)
    const off =
      typeof host.onEvent === 'function'
        ? host.onEvent('todo.updated', event => {
            const eventSid = String(event?.session_id || '')
            if (!eventSid || eventSid === taskSessionId()) void refresh()
          })
        : () => {}
    const onAdd = () => {
      setAdding(true)
      setDraft('')
    }
    window.addEventListener(TASK_ADD, onAdd)
    return () => {
      cancelled = true
      window.clearInterval(timer)
      unsubs.forEach(fn => {
        try {
          fn()
        } catch {
          // ignore
        }
      })
      off()
      window.removeEventListener(TASK_ADD, onAdd)
    }
  }, [])

  const todos = Array.isArray(state.todos) ? state.todos : []
  const keepOpen = state.keep_open === true || todos.some(item => item.status === 'pending' || item.status === 'in_progress')
  const done = todos.filter(item => item.status === 'completed').length

  useEffect(() => {
    const stack = document.querySelector('[data-slot="composer-status-stack"]')
    if (!stack) return
    for (const button of stack.querySelectorAll('button[aria-expanded]')) {
      if (!/tasks?\s+\d+\/\d+/i.test(button.textContent || '')) continue
      const section = button.parentElement?.parentElement
      if (!section) continue
      if (keepOpen && todos.length) section.setAttribute('data-hermes-native-todos', 'hidden')
      else {
        section.removeAttribute('data-hermes-native-todos')
        if (keepOpen && button.getAttribute('aria-expanded') === 'false') button.click()
      }
    }
  }, [keepOpen, todos.length, state.revision])

  if (!sid || (!todos.length && !adding && !keepOpen)) return null

  const saveAdd = async () => {
    const content = draft.trim()
    setAdding(false)
    setDraft('')
    if (!content || !sid) return
    try {
      const next = await host.request('todo.add', { session_id: sid, content })
      if (next) setState(next)
    } catch {
      // ignore
    }
  }

  const saveEdit = async id => {
    const content = editText.trim()
    setEditing('')
    if (!content || !sid) return
    try {
      const next = await host.request('todo.update', { session_id: sid, id, content })
      if (next) setState(next)
    } catch {
      // ignore
    }
  }

  const remove = async id => {
    if (!sid) return
    try {
      const next = await host.request('todo.delete', { session_id: sid, id })
      if (next) setState(next)
    } catch {
      // ignore
    }
  }

  return jsxs('div', {
    className: 'hermes-tasks',
    'data-slot': 'hermes-task-list',
    children: [
      jsxs('div', {
        className: 'hermes-tasks-head',
        children: [
          jsx('p', { className: 'hermes-tasks-title', children: todos.length ? `Tasks ${done}/${todos.length}` : 'Tasks' }),
          jsx('button', {
            type: 'button',
            className: 'hermes-tasks-btn',
            title: 'Add task',
            'aria-label': 'Add task',
            onClick: () => {
              setAdding(true)
              setDraft('')
            },
            children: '+'
          })
        ]
      }),
      ...todos.map(item => {
        const id = String(item?.id || '')
        if (editing === id) {
          return jsxs('div', {
            className: 'hermes-tasks-row',
            children: [
              jsx('input', {
                className: 'hermes-tasks-input',
                value: editText,
                autoFocus: true,
                onChange: event => setEditText(event.target.value),
                onKeyDown: event => {
                  if (event.key === 'Enter') void saveEdit(id)
                  if (event.key === 'Escape') setEditing('')
                }
              }),
              jsx('button', { type: 'button', className: 'hermes-tasks-btn', title: 'Save', onClick: () => void saveEdit(id), children: '✓' })
            ]
          }, id)
        }
        return jsxs('div', {
          className: 'hermes-tasks-row',
          children: [
            jsx('span', { className: 'hermes-tasks-text', 'data-status': item.status, title: item.content, children: item.content }),
            jsx('button', {
              type: 'button',
              className: 'hermes-tasks-btn',
              title: 'Edit task',
              'aria-label': `Edit ${item.content}`,
              onClick: () => {
                setEditing(id)
                setEditText(item.content || '')
              },
              children: '✎'
            }),
            jsx('button', {
              type: 'button',
              className: 'hermes-tasks-btn',
              'data-kind': 'danger',
              title: 'Remove task',
              'aria-label': `Remove ${item.content}`,
              onClick: () => void remove(id),
              children: '×'
            })
          ]
        }, id)
      }),
      adding
        ? jsxs('div', {
            className: 'hermes-tasks-row',
            children: [
              jsx('input', {
                className: 'hermes-tasks-input',
                value: draft,
                autoFocus: true,
                placeholder: 'New task',
                onChange: event => setDraft(event.target.value),
                onKeyDown: event => {
                  if (event.key === 'Enter') void saveAdd()
                  if (event.key === 'Escape') {
                    setAdding(false)
                    setDraft('')
                  }
                }
              }),
              jsx('button', { type: 'button', className: 'hermes-tasks-btn', title: 'Add', onClick: () => void saveAdd(), children: '+' })
            ]
          })
        : null,
      keepOpen ? jsx('p', { className: 'hermes-tasks-hint', children: 'Stays open until you say a task is done or complete.' }) : null
    ]
  })
}

function registerTaskListFromSpend(ctx) {
  if (typeof window !== 'undefined' && window[TASK_FLAG]) return
  if (typeof window !== 'undefined') window[TASK_FLAG] = true
  const style = document.createElement('style')
  style.textContent = TASK_CSS
  document.head.append(style)
  ctx.onDispose(() => {
    style.remove()
    if (typeof window !== 'undefined') delete window[TASK_FLAG]
  })
  const attachments = 'composer.attachments'
  const top = 'composer.top'
  ctx.register({
    id: 'add-task',
    area: attachments,
    data: {
      label: 'Add Task',
      icon: 'checklist',
      run: () => window.dispatchEvent(new CustomEvent(TASK_ADD))
    }
  })
  ctx.register({
    id: 'task-panel',
    area: top,
    order: 15,
    render: () => jsx(SpendTaskPanel, {})
  })
}

const EMOJI_FLAG = '__hermesMessagingEmojiUi'
const EMOJI_OPEN = 'hermes-messaging-emoji-open'
const MESSAGING_EMOJI = [
  '😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '😉', '😊', '😇', '🥰', '😍', '🤩', '😘',
  '😋', '😜', '🤪', '🤗', '🤭', '🤫', '🤔', '🫡', '😐', '😏', '😒', '🙄', '😬', '😌', '😔', '😴',
  '😷', '🤒', '🤕', '🤢', '🥴', '🤯', '🤠', '🥳', '😎', '🤓', '😕', '😟', '😮', '😯', '😲', '😳',
  '🥺', '😢', '😭', '😱', '😖', '😞', '😩', '😤', '😡', '🤬', '💀', '💩', '👻', '🤖', '👍', '👎',
  '👏', '🙌', '🤝', '🙏', '💪', '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '💔', '💕', '💯', '✨',
  '🔥', '⭐', '🎉', '✅', '❌', '⚠️', '💬', '👀', '🙈', '👌', '✌️', '🤞'
]

const EMOJI_CSS = `
.hermes-emoji{display:flex;flex-direction:column;gap:6px;padding:6px 8px 8px;max-height:min(36vh,18rem);overflow:hidden}
.hermes-emoji-head{display:flex;align-items:center;gap:6px;min-width:0}
.hermes-emoji-title{margin:0;flex:1 1 auto;min-width:0;font-size:11px;font-weight:600;color:var(--ui-text-secondary)}
.hermes-emoji-btn{display:inline-flex;align-items:center;justify-content:center;min-width:1.35rem;height:1.35rem;padding:0 6px;border:0;border-radius:6px;background:transparent;color:var(--ui-text-tertiary);cursor:pointer;font-size:12px;line-height:1}
.hermes-emoji-btn:hover{background:var(--chrome-action-hover);color:var(--ui-text-primary)}
.hermes-emoji-grid{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:2px;overflow-y:auto;max-height:min(28vh,14rem)}
.hermes-emoji-cell{display:flex;align-items:center;justify-content:center;height:1.85rem;padding:0;border:0;border-radius:6px;background:transparent;cursor:pointer;font-size:18px;line-height:1}
.hermes-emoji-cell:hover{background:var(--chrome-action-hover)}
`

function insertComposerText(text) {
  const insert = typeof window !== 'undefined' ? window.__hermesInsertComposerText : null
  if (typeof insert === 'function') {
    insert(text)
    return
  }
  const editor = document.querySelector('[contenteditable="true"]')
  if (!editor) return
  editor.focus()
  try {
    document.execCommand('insertText', false, text)
  } catch {
    // ignore
  }
  editor.dispatchEvent(new InputEvent('input', { bubbles: true, data: text, inputType: 'insertText' }))
}

function findQueuedEditSave() {
  for (const button of document.querySelectorAll('button')) {
    if ((button.textContent || '').trim() !== 'Save') continue
    const banner = (button.closest('div')?.parentElement?.textContent || '')
    if (/edit(ing)? queued/i.test(banner)) return button
  }
  return null
}

function composerEditor() {
  return (
    document.querySelector('[data-slot="composer-root"] [contenteditable="true"]') ||
    document.querySelector('[contenteditable="true"]')
  )
}

function composerIsEmpty() {
  const editor = composerEditor()
  return !editor || !(editor.textContent || '').trim()
}

function findStopButton() {
  for (const button of document.querySelectorAll('button')) {
    const label = (button.getAttribute('aria-label') || button.textContent || '').trim().toLowerCase()
    if (label === 'stop') return button
  }
  return null
}

function MessagingChrome() {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onOpen = () => setOpen(true)
    window.addEventListener(EMOJI_OPEN, onOpen)
    return () => window.removeEventListener(EMOJI_OPEN, onOpen)
  }, [])

  useEffect(() => {
    const onKey = event => {
      if (event.key !== 'Enter' || event.shiftKey || event.altKey || event.isComposing) return
      const save = findQueuedEditSave()
      if (save) {
        event.preventDefault()
        event.stopImmediatePropagation()
        save.click()
        return
      }
      // Packaged empty Enter while busy promotes the queue (interrupt). Block it.
      if (!event.metaKey && !event.ctrlKey && composerIsEmpty() && findStopButton()) {
        event.preventDefault()
        event.stopImmediatePropagation()
      }
    }
    document.addEventListener('keydown', onKey, true)
    return () => document.removeEventListener('keydown', onKey, true)
  }, [])

  if (!open) return null

  return jsxs('div', {
    className: 'hermes-emoji',
    'data-slot': 'hermes-messaging-emoji',
    children: [
      jsxs('div', {
        className: 'hermes-emoji-head',
        children: [
          jsx('p', { className: 'hermes-emoji-title', children: 'Emoji' }),
          jsx('button', {
            type: 'button',
            className: 'hermes-emoji-btn',
            title: 'Close',
            'aria-label': 'Close emoji picker',
            onClick: () => setOpen(false),
            children: '×'
          })
        ]
      }),
      jsx('div', {
        className: 'hermes-emoji-grid',
        children: MESSAGING_EMOJI.map(emoji =>
          jsx(
            'button',
            {
              type: 'button',
              className: 'hermes-emoji-cell',
              title: emoji,
              'aria-label': `Insert ${emoji}`,
              onClick: () => {
                insertComposerText(emoji)
                setOpen(false)
              },
              children: emoji
            },
            emoji
          )
        )
      })
    ]
  })
}

function registerMessagingFromSpend(ctx) {
  if (typeof window !== 'undefined' && window[EMOJI_FLAG]) return
  if (typeof window !== 'undefined') window[EMOJI_FLAG] = true
  const style = document.createElement('style')
  style.textContent = EMOJI_CSS
  document.head.append(style)
  ctx.onDispose(() => {
    style.remove()
    if (typeof window !== 'undefined') delete window[EMOJI_FLAG]
  })
  ctx.register({
    id: 'add-emoji',
    area: 'composer.attachments',
    data: {
      label: 'Emoji',
      icon: 'smiley',
      run: ({ insertText } = {}) => {
        if (typeof insertText === 'function') window.__hermesInsertComposerText = insertText
        window.dispatchEvent(new CustomEvent(EMOJI_OPEN))
      }
    }
  })
  ctx.register({
    id: 'messaging-emoji-panel',
    area: 'composer.top',
    order: 5,
    render: () => jsx(MessagingChrome, {})
  })
}
