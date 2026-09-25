/**
 * Pull VPS desktop-plugins onto this Mac while Desktop is connected.
 * Install once at ~/.hermes/desktop-plugins/vps-ui-sync/plugin.js
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

const ID = 'vps-ui-sync'
const POLL_MS = 15_000
const SHA_PREFIX = 'hermes.vps-ui-sync.sha.'

const CSS = `
.hermes-uisync-chip{display:inline-flex;align-items:center;gap:5px;height:100%;padding:0 6px;border:0;background:transparent;color:var(--ui-accent);font-size:11px;line-height:1;cursor:pointer}
.hermes-uisync-chip:hover{background:var(--chrome-action-hover);color:var(--ui-accent)}
.hermes-uisync-panel{width:18rem;max-width:calc(100vw - 24px);padding:12px;display:grid;gap:8px;font-size:12px}
.hermes-uisync-panel p{margin:0;color:var(--ui-text-secondary)}
.hermes-uisync-panel strong{color:var(--ui-text-primary)}
.hermes-uisync-list{margin:0;padding:0;list-style:none;display:grid;gap:4px;max-height:12rem;overflow-y:auto}
.hermes-uisync-list li{display:flex;justify-content:space-between;gap:8px;color:var(--ui-text-tertiary);font-size:11px}
[data-slot="aui_thread-viewport"]{overflow-x:hidden!important;overflow-y:auto!important;overscroll-behavior:contain;scrollbar-gutter:stable;overflow-anchor:none!important}
[data-slot="aui_thread-viewport"][data-user-scroll="1"]{scroll-behavior:auto!important}
.xterm-viewport{overflow-y:scroll!important;overscroll-behavior:contain;scrollbar-gutter:stable}
[data-terminal] .xterm-viewport::-webkit-scrollbar,.xterm .xterm-viewport::-webkit-scrollbar{width:10px!important;height:10px!important}
[data-terminal] .xterm-viewport::-webkit-scrollbar-thumb,.xterm .xterm-viewport::-webkit-scrollbar-thumb{background:color-mix(in srgb,var(--ui-text-tertiary) 45%,transparent)!important;border-radius:999px}
[data-terminal] .xterm-viewport::-webkit-scrollbar-track,.xterm .xterm-viewport::-webkit-scrollbar-track{background:transparent!important}
`

const CHAT_VIEWPORT = '[data-slot="aui_thread-viewport"]'
const XTERM_VIEWPORT = '.xterm-viewport'
const XTERM_HOST = '[data-terminal], .xterm'
const HOLD_MS = 6000
const BOTTOM_PX = 32
const NESTED = '.scrollbar-overlay, pre, [data-slot="code-block"]'
const scrollTopDesc = Object.getOwnPropertyDescriptor(Element.prototype, 'scrollTop')

function getTop(el) {
  return scrollTopDesc?.get ? scrollTopDesc.get.call(el) : el.scrollTop
}

function setTop(el, value) {
  if (scrollTopDesc?.set) scrollTopDesc.set.call(el, value)
  else el.scrollTop = value
}

function distanceFromBottom(el) {
  return el.scrollHeight - getTop(el) - el.clientHeight
}

function wheelDeltaY(event, el) {
  let dy = event.deltaY
  if (event.deltaMode === 1) dy *= 16
  if (event.deltaMode === 2) dy *= el.clientHeight || 1
  return dy
}

function clampTop(el, value) {
  const max = Math.max(0, el.scrollHeight - el.clientHeight)
  return Math.min(max, Math.max(0, value))
}

function restoreNativeScroll(el) {
  try {
    if (Object.prototype.hasOwnProperty.call(el, 'scrollTop')) delete el.scrollTop
  } catch {
    // ignore
  }
  try {
    if (Object.prototype.hasOwnProperty.call(el, 'scrollTo')) delete el.scrollTo
  } catch {
    // ignore
  }
}

function xtermFromNode(node) {
  if (!node) return null
  if (node.matches?.(XTERM_VIEWPORT)) return node
  const host = node.closest?.(XTERM_HOST)
  return host?.querySelector?.(XTERM_VIEWPORT) || null
}

function chatFromNode(node) {
  if (!node) return null
  if (node.matches?.(CHAT_VIEWPORT)) return node
  return node.closest?.(CHAT_VIEWPORT) || null
}

/** Prefer the terminal under the pointer. Never steal wheel for a chat pane sitting behind the xterm overlay. */
function scrollerAt(x, y) {
  const stack = document.elementsFromPoint(x, y)
  for (const node of stack) {
    const xterm = xtermFromNode(node)
    if (xterm) return { el: xterm, kind: 'xterm' }
  }
  for (const node of stack) {
    const chat = chatFromNode(node)
    if (chat) return { el: chat, kind: 'chat' }
  }
  return null
}

function nestedScroller(event, viewport) {
  let node = event.target
  if (node && typeof node.closest !== 'function') node = node.parentElement
  const nested = node?.closest?.(NESTED)
  if (!nested || nested === viewport || !viewport.contains(nested)) return null
  if (nested.scrollHeight <= nested.clientHeight + 1) return null
  return nested
}

function nestedCanConsume(nested, dy) {
  const top = nested.scrollTop
  const max = nested.scrollHeight - nested.clientHeight
  if (dy < 0 && top > 0) return true
  if (dy > 0 && top < max - 1) return true
  return false
}

function watchPaneScroll() {
  const states = new WeakMap()
  const cleanups = new Set()

  const stateOf = el => {
    let state = states.get(el)
    if (!state) {
      state = { heldUntil: 0, saved: 0, raf: 0, dragging: false, lastHeight: el.scrollHeight }
      states.set(el, state)
    }
    return state
  }

  const tick = el => {
    const state = stateOf(el)
    state.raf = 0
    if (Date.now() >= state.heldUntil && !state.dragging) {
      if (distanceFromBottom(el) <= BOTTOM_PX) el.removeAttribute('data-user-scroll')
      return
    }
    const top = getTop(el)
    const height = el.scrollHeight
    if (state.dragging) {
      state.saved = top
    } else {
      state.saved = clampTop(el, state.saved)
      const jumpedDown = top > state.saved + 8
      const towardBottom = distanceFromBottom(el) + 8 < height - state.saved - el.clientHeight
      const prepended = height > (state.lastHeight || height) + 8 && !towardBottom
      if (prepended) {
        state.saved = top
      } else if (jumpedDown && towardBottom) {
        setTop(el, state.saved)
      } else if (!jumpedDown) {
        state.saved = top
      }
    }
    state.lastHeight = height
    state.raf = window.requestAnimationFrame(() => tick(el))
  }

  const hold = (el, top) => {
    const state = stateOf(el)
    state.heldUntil = Date.now() + HOLD_MS
    state.saved = clampTop(el, top)
    el.setAttribute('data-user-scroll', '1')
    if (!state.raf) state.raf = window.requestAnimationFrame(() => tick(el))
  }

  const releaseBottom = el => {
    const state = stateOf(el)
    state.heldUntil = 0
    state.dragging = false
    el.removeAttribute('data-user-scroll')
  }

  const applyDelta = (el, dy) => {
    const next = clampTop(el, getTop(el) + dy)
    setTop(el, next)
    hold(el, next)
    return next
  }

  const onWheel = event => {
    const hit = scrollerAt(event.clientX, event.clientY)
    if (!hit) return
    const { el, kind } = hit
    if (el.scrollHeight <= el.clientHeight + 1) return
    const dy = wheelDeltaY(event, el)
    if (!dy) return
    if (kind === 'chat') {
      const nested = nestedScroller(event, el)
      if (nested && nestedCanConsume(nested, dy)) return
      if (dy < 0 && getTop(el) <= 1) return
    }
    if (dy > 0 && distanceFromBottom(el) <= BOTTOM_PX) {
      releaseBottom(el)
      return
    }
    event.preventDefault()
    event.stopImmediatePropagation()
    applyDelta(el, dy)
  }

  const onPointerDown = event => {
    const hit = scrollerAt(event.clientX, event.clientY)
    if (!hit) return
    const box = hit.el.getBoundingClientRect()
    if (event.clientX < box.right - 22) return
    const state = stateOf(hit.el)
    state.dragging = true
    hold(hit.el, getTop(hit.el))
    const move = () => hold(hit.el, getTop(hit.el))
    const up = () => {
      state.dragging = false
      hold(hit.el, getTop(hit.el))
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
    cleanups.add(() => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    })
  }

  const onKey = event => {
    const keys = { PageUp: -0.9, PageDown: 0.9, ArrowUp: -0.15, ArrowDown: 0.15 }
    const factor = keys[event.key]
    if (factor == null) return
    if (event.target && /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName)) return
    if (event.target?.isContentEditable) return
    if (event.target?.classList?.contains('xterm-helper-textarea')) return
    const hover =
      document.querySelector(`${XTERM_HOST}:hover ${XTERM_VIEWPORT}`) ||
      document.querySelector(`${CHAT_VIEWPORT}:hover`)
    if (!hover || hover.scrollHeight <= hover.clientHeight + 1) return
    const dy = hover.clientHeight * factor
    if (dy > 0 && distanceFromBottom(hover) <= BOTTOM_PX) {
      releaseBottom(hover)
      return
    }
    event.preventDefault()
    applyDelta(hover, dy)
  }

  const scan = () => {
    document.querySelectorAll(`${CHAT_VIEWPORT}, ${XTERM_VIEWPORT}`).forEach(restoreNativeScroll)
  }
  scan()
  const observer = new MutationObserver(scan)
  observer.observe(document.documentElement, { childList: true, subtree: true })

  document.addEventListener('wheel', onWheel, { capture: true, passive: false })
  document.addEventListener('pointerdown', onPointerDown, { capture: true })
  document.addEventListener('keydown', onKey, { capture: true })

  return () => {
    observer.disconnect()
    document.removeEventListener('wheel', onWheel, { capture: true })
    document.removeEventListener('pointerdown', onPointerDown, { capture: true })
    document.removeEventListener('keydown', onKey, { capture: true })
    for (const stop of cleanups) stop()
    cleanups.clear()
    document.querySelectorAll(`${CHAT_VIEWPORT}, ${XTERM_VIEWPORT}`).forEach(el => {
      restoreNativeScroll(el)
      el.removeAttribute('data-user-scroll')
    })
  }
}

function shaKey(id) {
  return `${SHA_PREFIX}${id}`
}

async function syncFromVps() {
  const desktop = typeof window !== 'undefined' ? window.hermesDesktop : null
  if (!desktop?.desktopPluginsRoot || !desktop.writeTextFile) {
    return { ok: false, error: 'local plugin writes unavailable', wrote: [], skipped: [] }
  }
  const listed = await host.request('desktop.plugin.list', {})
  const plugins = Array.isArray(listed?.plugins) ? listed.plugins : []
  const root = String((await desktop.desktopPluginsRoot()) || '').replace(/\/$/, '')
  if (!root) return { ok: false, error: 'plugin root missing', wrote: [], skipped: [] }
  const wrote = []
  const skipped = []
  for (const item of plugins) {
    const id = item?.id
    const sha = item?.sha256
    if (!id || !sha) continue
    try {
      if (window.localStorage.getItem(shaKey(id)) === sha) {
        skipped.push(id)
        continue
      }
    } catch {
      // compare anyway
    }
    const src = await host.request('desktop.plugin.source', { id })
    if (!src?.content || src.sha256 !== sha) {
      skipped.push(id)
      continue
    }
    const path = `${root}/${id}/plugin.js`
    try {
      await desktop.writeTextFile(path, src.content)
      try {
        window.localStorage.setItem(shaKey(id), sha)
      } catch {
        // ignore
      }
      wrote.push(id)
    } catch {
      skipped.push(`${id} (folder missing on Mac)`)
    }
  }
  return { ok: true, wrote, skipped, count: plugins.length }
}

function SyncChip() {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState('waiting')
  const [detail, setDetail] = useState(null)

  useEffect(() => {
    let cancelled = false
    let timer = 0
    const tick = async () => {
      try {
        const result = await syncFromVps()
        if (!cancelled) {
          setDetail(result)
          setStatus(result.ok ? (result.wrote?.length ? 'pulled' : 'idle') : 'error')
        }
      } catch (error) {
        if (!cancelled) {
          setStatus('error')
          setDetail({ error: error instanceof Error ? error.message : String(error) })
        }
      }
      if (!cancelled) timer = window.setTimeout(() => void tick(), POLL_MS)
    }
    void tick()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [])

  const label = status === 'pulled' ? 'UI pulled' : status === 'error' ? 'UI sync err' : 'UI sync'
  const wrote = detail?.wrote || []
  const skipped = detail?.skipped || []

  return jsxs(DropdownMenu, {
    modal: false,
    open,
    onOpenChange: setOpen,
    children: [
      jsx(DropdownMenuTrigger, {
        asChild: true,
        children: jsx('button', {
          type: 'button',
          className: 'hermes-uisync-chip',
          title: 'Pulls VPS desktop-plugins. Terminal wheel keeps your place.',
          children: label
        })
      }),
      jsx(DropdownMenuContent, {
        side: 'top',
        align: 'end',
        sideOffset: 8,
        className: 'p-0',
        children: jsxs('div', {
          className: 'hermes-uisync-panel',
          children: [
            jsx('p', { children: jsx('strong', { children: 'VPS → Mac plugins' }) }),
            jsx('p', {
              children:
                status === 'error'
                  ? detail?.error || 'sync failed'
                  : `Last pass: ${wrote.length} updated, ${skipped.length} unchanged or blocked.`
            }),
            jsx('p', {
              children:
                'Terminal pane: wheel and the scrollbar keep the line you scrolled to. cursor-agent output no longer yanks the xterm back to the live tail.'
            }),
            wrote.length
              ? jsx('ol', {
                  className: 'hermes-uisync-list',
                  children: wrote.map(id => jsx('li', { children: id }, id))
                })
              : null
          ]
        })
      })
    ]
  })
}

export default {
  id: ID,
  name: 'VPS UI sync',
  description: 'Pull VPS desktop-plugins onto this Mac over the live gateway.',
  defaultEnabled: true,
  register(ctx) {
    const style = document.createElement('style')
    style.textContent = CSS
    document.head.append(style)
    const stopWatch = watchPaneScroll()
    ctx.onDispose(() => {
      style.remove()
      stopWatch()
    })
    ctx.register({
      id: 'vps-ui-sync',
      area: STATUSBAR_AREAS.right,
      order: 95,
      render: () => jsx(SyncChip, {})
    })
  }
}
