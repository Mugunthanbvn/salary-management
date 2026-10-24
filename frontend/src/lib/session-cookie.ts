/**
 * Name of the httpOnly cookie FastAPI sets on login. JavaScript in the browser can't read
 * it; only proxy.ts (is there a session?) and lib/api/server.ts (forward it) look at it.
 */
export const SESSION_COOKIE = "session";
