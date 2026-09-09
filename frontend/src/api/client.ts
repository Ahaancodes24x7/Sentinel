/**
 * API client.
 *
 * Deliberately has NO silent mock fallback. The previous version quietly swapped
 * in fabricated data whenever the backend was unreachable, which meant a broken
 * connection looked exactly like a working system — the single worst failure
 * mode for a safety console, and a fatal one to be caught doing in a demo.
 *
 * When the backend is down, requests throw and the UI shows an explicit
 * disconnected state. Nothing on screen is ever data the system did not receive.
 */

const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? '/api/v1';

export const TOKEN_KEY = 'sentinel_token';
export const ROLE_KEY = 'sentinel_role';
export const USER_KEY = 'sentinel_user';

export class ApiError extends Error {
  status: number;
  code: string;
  offline: boolean;

  constructor(message: string, status = 0, code = 'UNKNOWN', offline = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.offline = offline;
  }
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function clearSession(): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(ROLE_KEY);
  window.localStorage.removeItem(USER_KEY);
}

interface RequestOptions extends RequestInit {
  /** Milliseconds before the request is aborted. Pattern endpoints legitimately
   *  take a few seconds on a 25k-report corpus, so this is generous. */
  timeoutMs?: number;
}

export async function apiRequest<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 20000, ...init } = options;
  const token = getToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((init.headers as Record<string, string>) ?? {}),
  };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...init,
      headers,
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timer);
    const aborted = (err as Error)?.name === 'AbortError';
    throw new ApiError(
      aborted ? 'Request timed out' : 'Cannot reach the Sentinel API',
      0,
      aborted ? 'TIMEOUT' : 'NETWORK',
      true,
    );
  }
  clearTimeout(timer);

  if (response.status === 401) {
    clearSession();
    throw new ApiError('Session expired — sign in again', 401, 'UNAUTHORIZED');
  }

  if (!response.ok) {
    let code = `HTTP_${response.status}`;
    let message = response.statusText || 'Request failed';
    try {
      const body = await response.json();
      const detail = body?.error ?? body?.detail;
      if (detail && typeof detail === 'object') {
        code = detail.code ?? code;
        message = detail.message ?? message;
      } else if (typeof detail === 'string') {
        message = detail;
      }
    } catch {
      /* non-JSON error body — keep the status text */
    }
    throw new ApiError(message, response.status, code);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) => apiRequest<T>(endpoint, options),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'POST',
      body: body === undefined ? undefined : JSON.stringify(body),
    }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
};

/** Build a query string, skipping empty/undefined values. */
export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '' || value === 'all') return;
    search.append(key, String(value));
  });
  const out = search.toString();
  return out ? `?${out}` : '';
}

export { API_BASE_URL };
