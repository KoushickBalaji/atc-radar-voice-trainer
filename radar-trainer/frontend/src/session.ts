/** Per-tab capability held only in memory. No cookie or storage shared between tabs. */
let token: string | null = null;
export const hasSession = () => token !== null;
export const socketProtocols = () => token ? ['atc-session', token] : undefined;

export async function sessionFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  const requestToken = token;
  if (requestToken) headers.set('X-ATC-Session', requestToken);
  const response = await fetch(path, { ...init, headers });
  if (response.status === 410 && requestToken && token === requestToken) expireSession();
  return response;
}

export async function beginSession() {
  await endSession();
  const response = await fetch('/api/session', { method: 'POST', signal: AbortSignal.timeout(100000) });
  // Retain the original standalone/local launcher; hosted gateway never returns these.
  if (response.status === 404 || response.status === 405) return;
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.detail || 'Unable to create a practice session. Please try again.');
  if (typeof result.token !== 'string' || result.token.length < 32) throw new Error('The session service is unavailable.');
  token = result.token;
}

export async function endSession() {
  const previous = token;
  token = null; // Clear before waiting; stale requests cannot inherit a new session.
  if (previous) await fetch('/api/session', { method: 'DELETE', headers: { 'X-ATC-Session': previous },
    keepalive: true, signal: AbortSignal.timeout(7000) }).catch(() => undefined);
}

export function expireSession() {
  if (!token) return;
  void endSession();
  window.dispatchEvent(new Event('atc-session-ended'));
}
