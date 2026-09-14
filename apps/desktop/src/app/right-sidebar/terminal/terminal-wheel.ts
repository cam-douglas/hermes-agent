/** Trackpad wheel can chase FitAddon by 1px and WINCH the PTY. Freeze fit
 *  briefly after a wheel. Do not intercept the event: xterm 6 already scrolls
 *  the viewport (or encodes mouse-protocol wheel to the PTY). Hiding
 *  `.xterm-scrollable-element` overflow / its scrollbar is what killed scroll. */

export const TERMINAL_WHEEL_FIT_FREEZE_MS = 500

export function shouldFreezeTerminalFitForWheel(
  now: number,
  lastWheelAt: number,
  freezeMs = TERMINAL_WHEEL_FIT_FREEZE_MS
): boolean {
  return lastWheelAt > 0 && now - lastWheelAt < freezeMs
}
