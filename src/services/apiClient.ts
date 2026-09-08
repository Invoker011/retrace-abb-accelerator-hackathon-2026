/**
 * Centralized API Client for RETRACE
 * Communicates with the FastAPI intelligence backend.
 * Provides resilient fallback handling when backend is offline or unreachable.
 */

const DEFAULT_BACKEND_URL = 'http://localhost:8000';

export const getApiBaseUrl = (): string => {
  const metaEnv = (import.meta as unknown as { env?: Record<string, string | undefined> })?.env;
  const envUrl = metaEnv?.VITE_RETRACE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  return DEFAULT_BACKEND_URL;
};

export class ApiError extends Error {
  public status: number;
  public details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export interface RequestOptions {
  timeoutMs?: number;
  headers?: Record<string, string>;
}

async function executeRequest<T>(
  endpoint: string,
  method: 'GET' | 'POST' = 'GET',
  body?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  const { timeoutMs = 2500, headers = {} } = options;
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${cleanEndpoint}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    clearTimeout(timer);

    if (!response.ok) {
      let errorDetail: string | undefined;
      try {
        const errJson = await response.json();
        errorDetail = errJson.detail || errJson.message;
      } catch {
        // Non-JSON error body
      }
      throw new ApiError(
        errorDetail || `API request failed with status ${response.status}`,
        response.status
      );
    }

    const data = await response.json();
    return data as T;
  } catch (err: unknown) {
    clearTimeout(timer);

    if (err instanceof ApiError) {
      throw err;
    }

    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError('API request timed out', 408);
    }

    // Network unreachable / CORS / offline
    throw new ApiError('Backend service currently unavailable', 503, err);
  }
}

export const apiClient = {
  request: executeRequest,

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return executeRequest<T>(endpoint, 'GET', undefined, options);
  },

  async post<T>(endpoint: string, body: unknown, options?: RequestOptions): Promise<T> {
    return executeRequest<T>(endpoint, 'POST', body, options);
  },

  /**
   * Health check to detect whether FastAPI backend is actively responding
   */
  async checkHealth(): Promise<boolean> {
    try {
      const res = await executeRequest<{ status: string }>('/health', 'GET', undefined, {
        timeoutMs: 1200,
      });
      return res?.status === 'healthy';
    } catch {
      return false;
    }
  },
};
