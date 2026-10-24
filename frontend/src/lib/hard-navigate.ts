/**
 * A full page load, not a client-side navigation. Used when the session changes (sign in,
 * sign out): the browser drops everything in memory, including the client router cache, so
 * nothing from the previous session can show again. A module of its own so tests can mock it.
 */
export function hardNavigate(url: string): void {
  window.location.assign(url);
}
