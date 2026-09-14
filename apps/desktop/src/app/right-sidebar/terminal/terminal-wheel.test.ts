import { describe, expect, it } from 'vitest'

import { shouldFreezeTerminalFitForWheel, TERMINAL_WHEEL_FIT_FREEZE_MS } from './terminal-wheel'

describe('shouldFreezeTerminalFitForWheel', () => {
  it('freezes FitAddon for a short window after a wheel', () => {
    expect(shouldFreezeTerminalFitForWheel(1_000, 0)).toBe(false)
    expect(shouldFreezeTerminalFitForWheel(1_000, 900)).toBe(true)
    expect(shouldFreezeTerminalFitForWheel(1_000 + TERMINAL_WHEEL_FIT_FREEZE_MS, 1_000)).toBe(false)
  })
})
