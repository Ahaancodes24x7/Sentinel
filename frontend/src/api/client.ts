const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data: T | null; error: string | null; isFallback: boolean }> {
  const token = localStorage.getItem('sentinel_token');
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500); // 3.5s timeout before graceful fallback

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errJson = await response.json().catch(() => ({}));
      const errorMsg = errJson?.error?.message || `HTTP ${response.status}: ${response.statusText}`;
      return { data: null, error: errorMsg, isFallback: true };
    }

    const data = await response.json();
    return { data, error: null, isFallback: false };
  } catch (err: any) {
    // Backend unavailable or network error -> signal fallback to mock data
    return {
      data: null,
      error: err.name === 'AbortError' ? 'Backend connection timed out' : err.message || 'Network error',
      isFallback: true,
    };
  }
}
