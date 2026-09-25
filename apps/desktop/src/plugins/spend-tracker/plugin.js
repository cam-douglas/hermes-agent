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

async function pullFromVps() {
  const desktop = typeof window !== 'undefined' ? window.hermesDesktop : null
  if (!desktop?.desktopPluginsRoot || !desktop.writeTextFile) return
  let src
  try {
    src = await host.request('desktop.plugin.source', { id: ID })
  } catch {
    return
  }
  const next = src?.content
  const sha = src?.sha256
  if (!next || !sha) return
  try {
    if (window.localStorage.getItem(SHA_KEY) === sha) return
  } catch {
    // ignore storage
  }
  const root = await desktop.desktopPluginsRoot()
  if (!root) return
  const path = `${String(root).replace(/\/$/, '')}/spend-tracker/plugin.js`
  await desktop.writeTextFile(path, next)
  try {
    window.localStorage.setItem(SHA_KEY, sha)
  } catch {
    // ignore storage
  }
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
    ctx.onDispose(() => style.remove())
    ctx.register({
      id: 'hourly-spend',
      area: STATUSBAR_AREAS.right,
      order: 90,
      render: () => jsx(SpendChip, {})
    })
    void pullFromVps()
  }
}
