/**
 * Editable session task list for the live Desktop window.
 * Pulled onto the Mac at ~/.hermes/desktop-plugins/task-list/plugin.js
 */
import { host } from '@hermes/plugin-sdk'
import { useEffect, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'task-list'
const POLL_MS = 2000
const FLAG = '__hermesTaskListUi'
const ADD_EVENT = 'hermes-task-list-add'

const CSS = `
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

function currentSessionId() {
  const state = host.state || {}
  try {
    const focused = state.focusedSessionId?.get?.()
    if (focused) return String(focused)
    const active = state.activeSessionId?.get?.()
    if (active) return String(active)
  } catch {
    // older SDK
  }
  return ''
}

async function rpc(method, params) {
  return host.request(method, params)
}

function todoId(item) {
  return String(item?.id || '').replace(/^todo:/, '')
}

function TaskPanel() {
  const [sid, setSid] = useState(() => currentSessionId())
  const [state, setState] = useState({ todos: [], keep_open: false, revision: 0 })
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState('')
  const [editing, setEditing] = useState('')
  const [editText, setEditText] = useState('')

  useEffect(() => {
    let cancelled = false
    const unsubs = []
    const applySid = () => {
      if (!cancelled) setSid(currentSessionId())
    }
    for (const atom of [host.state?.focusedSessionId, host.state?.activeSessionId]) {
      if (atom && typeof atom.listen === 'function') {
        unsubs.push(atom.listen(applySid))
      }
    }
    const refresh = async () => {
      applySid()
      const sessionId = currentSessionId()
      if (!sessionId) {
        if (!cancelled) setState({ todos: [], keep_open: false, revision: 0 })
        return
      }
      try {
        const next = await rpc('todo.get', { session_id: sessionId })
        if (!cancelled && next) setState(next)
      } catch {
        // serve may not have the RPC yet
      }
    }
    void refresh()
    const timer = window.setInterval(() => void refresh(), POLL_MS)
    const offUpdated =
      typeof host.onEvent === 'function'
        ? host.onEvent('todo.updated', event => {
            const eventSid = String(event?.session_id || '')
            if (!eventSid || eventSid === currentSessionId()) void refresh()
          })
        : () => {}
    const onAdd = () => {
      setAdding(true)
      setDraft('')
    }
    window.addEventListener(ADD_EVENT, onAdd)
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
      offUpdated()
      window.removeEventListener(ADD_EVENT, onAdd)
    }
  }, [])

  const todos = Array.isArray(state.todos) ? state.todos : []
  const keepOpen = state.keep_open === true || todos.some(item => item.status === 'pending' || item.status === 'in_progress')
  const done = todos.filter(item => item.status === 'completed').length

  useEffect(() => {
    const stack = document.querySelector('[data-slot="composer-status-stack"]')
    if (!stack) return
    const buttons = stack.querySelectorAll('button[aria-expanded]')
    for (const button of buttons) {
      const label = button.textContent || ''
      if (!/tasks?\s+\d+\/\d+/i.test(label)) continue
      const section = button.parentElement?.parentElement
      if (!section) continue
      if (keepOpen && todos.length) {
        section.setAttribute('data-hermes-native-todos', 'hidden')
      } else {
        section.removeAttribute('data-hermes-native-todos')
        if (keepOpen && button.getAttribute('aria-expanded') === 'false') {
          button.click()
        }
      }
    }
  }, [keepOpen, todos.length, state.revision])

  const sessionId = sid
  if (!sessionId || (!todos.length && !adding && !keepOpen)) return null

  const saveAdd = async () => {
    const content = draft.trim()
    setAdding(false)
    setDraft('')
    if (!content || !sessionId) return
    try {
      const next = await rpc('todo.add', { session_id: sessionId, content })
      if (next) setState(next)
    } catch {
      // ignore
    }
  }

  const saveEdit = async id => {
    const content = editText.trim()
    setEditing('')
    if (!content || !sessionId) return
    try {
      const next = await rpc('todo.update', { session_id: sessionId, id, content })
      if (next) setState(next)
    } catch {
      // ignore
    }
  }

  const remove = async id => {
    if (!sessionId) return
    try {
      const next = await rpc('todo.delete', { session_id: sessionId, id })
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
          jsx('p', {
            className: 'hermes-tasks-title',
            children: todos.length ? `Tasks ${done}/${todos.length}` : 'Tasks'
          }),
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
      todos.length === 0 && !adding
        ? jsx('p', { className: 'hermes-tasks-empty', children: 'No tasks yet.' })
        : null,
      ...todos.map(item => {
        const id = todoId(item)
        if (editing === id) {
          return jsxs(
            'div',
            {
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
                jsx('button', {
                  type: 'button',
                  className: 'hermes-tasks-btn',
                  title: 'Save',
                  onClick: () => void saveEdit(id),
                  children: '✓'
                })
              ]
            },
            id
          )
        }
        return jsxs(
          'div',
          {
            className: 'hermes-tasks-row',
            children: [
              jsx('span', {
                className: 'hermes-tasks-text',
                'data-status': item.status,
                title: item.content,
                children: item.content
              }),
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
          },
          id
        )
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
              jsx('button', {
                type: 'button',
                className: 'hermes-tasks-btn',
                title: 'Add',
                onClick: () => void saveAdd(),
                children: '+'
              })
            ]
          })
        : null,
      keepOpen
        ? jsx('p', {
            className: 'hermes-tasks-hint',
            children: 'Stays open until you say a task is done or complete.'
          })
        : null
    ]
  })
}

export function registerTaskList(ctx) {
  if (typeof window !== 'undefined' && window[FLAG]) return
  if (typeof window !== 'undefined') window[FLAG] = true

  const style = document.createElement('style')
  style.textContent = CSS
  document.head.append(style)
  ctx.onDispose(() => {
    style.remove()
    if (typeof window !== 'undefined') delete window[FLAG]
  })

  const attachments = 'composer.attachments'
  const top = 'composer.top'

  ctx.register({
    id: 'add-task',
    area: attachments,
    data: {
      label: 'Add Task',
      icon: 'checklist',
      run: () => {
        window.dispatchEvent(new CustomEvent(ADD_EVENT))
      }
    }
  })
  ctx.register({
    id: 'task-panel',
    area: top,
    order: 15,
    render: () => jsx(TaskPanel, {})
  })
}

export default {
  id: ID,
  name: 'Task list',
  description: 'Plus, edit, and remove on the chat task list. Stays open until you confirm each task.',
  defaultEnabled: true,
  register(ctx) {
    registerTaskList(ctx)
  }
}
