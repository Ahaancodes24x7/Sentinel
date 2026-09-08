/**
 * Framework-agnostic token holder. The backend token is an opaque hex string
 * (not a JWT) held in an in-memory store server-side — the client just stores
 * and replays it. Kept in a module variable (fast, SSR-safe) mirrored to
 * localStorage (survives reload). Every access is guarded — localStorage can
 * throw in private windows / thumbnail capture / storage-blocked browsers.
 */
const TOKEN_KEY = "sentinel.token";
const ROLE_KEY = "sentinel.role";
const USER_KEY = "sentinel.username";

let memToken: string | null = null;

export interface StoredSession {
  token: string;
  role: string;
  username: string;
}

export function readSession(): StoredSession | null {
  if (memToken) {
    return {
      token: memToken,
      role: safeGet(ROLE_KEY) ?? "",
      username: safeGet(USER_KEY) ?? "",
    };
  }
  const token = safeGet(TOKEN_KEY);
  if (!token) return null;
  memToken = token;
  return {
    token,
    role: safeGet(ROLE_KEY) ?? "",
    username: safeGet(USER_KEY) ?? "",
  };
}

export function writeSession(s: StoredSession): void {
  memToken = s.token;
  safeSet(TOKEN_KEY, s.token);
  safeSet(ROLE_KEY, s.role);
  safeSet(USER_KEY, s.username);
}

export function clearSession(): void {
  memToken = null;
  safeRemove(TOKEN_KEY);
  safeRemove(ROLE_KEY);
  safeRemove(USER_KEY);
}

export function getToken(): string | null {
  return readSession()?.token ?? null;
}

function safeGet(k: string): string | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage.getItem(k);
  } catch {
    return null;
  }
}
function safeSet(k: string, v: string): void {
  try {
    window.localStorage.setItem(k, v);
  } catch {
    /* ignore */
  }
}
function safeRemove(k: string): void {
  try {
    window.localStorage.removeItem(k);
  } catch {
    /* ignore */
  }
}
