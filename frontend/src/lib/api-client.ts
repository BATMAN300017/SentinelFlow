import { API_BASE_URL } from './utils';

export interface ApiErrorDetail {
  message: string;
  status?: number;
  isNetworkError?: boolean;
  isTimeout?: boolean;
  endpoint?: string;
}

export class ApiError extends Error {
  status?: number;
  isNetworkError: boolean;
  isTimeout: boolean;
  endpoint: string;

  constructor(detail: ApiErrorDetail) {
    super(detail.message);
    this.name = 'ApiError';
    this.status = detail.status;
    this.isNetworkError = detail.isNetworkError ?? false;
    this.isTimeout = detail.isTimeout ?? false;
    this.endpoint = detail.endpoint || '';
  }
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
  const { timeoutMs = 20000, ...fetchOptions } = options;
  const token = typeof window !== 'undefined' ? localStorage.getItem('sentinel_token') : null;
  const headers = new Headers(fetchOptions.headers || {});

  headers.set('Content-Type', 'application/json');
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE_URL}${cleanEndpoint}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timer);

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      const message = errorBody.detail || errorBody.message || `API request failed (${response.status} ${response.statusText})`;
      throw new ApiError({
        message,
        status: response.status,
        endpoint: cleanEndpoint,
      });
    }

    return await response.json();
  } catch (err: any) {
    clearTimeout(timer);

    if (err instanceof ApiError) {
      throw err;
    }

    if (err.name === 'AbortError') {
      throw new ApiError({
        message: `Request timed out after ${timeoutMs / 1000}s while contacting ${cleanEndpoint}`,
        isTimeout: true,
        endpoint: cleanEndpoint,
      });
    }

    throw new ApiError({
      message: err.message || 'Network error: could not connect to SentinelFlow backend API',
      isNetworkError: true,
      endpoint: cleanEndpoint,
    });
  }
}

export async function pingApi(): Promise<{
  ok: boolean;
  status: string;
  latencyMs: number;
  version?: string;
  error?: string;
}> {
  const start = performance.now();
  try {
    const res = await fetchApi<{ status: string; version?: string }>('/health', { timeoutMs: 8000 });
    const latencyMs = Math.round(performance.now() - start);
    return {
      ok: res.status === 'ok' || res.status === 'healthy',
      status: res.status || 'online',
      latencyMs,
      version: res.version,
    };
  } catch (err: any) {
    const latencyMs = Math.round(performance.now() - start);
    return {
      ok: false,
      status: 'offline',
      latencyMs,
      error: err.message,
    };
  }
}
