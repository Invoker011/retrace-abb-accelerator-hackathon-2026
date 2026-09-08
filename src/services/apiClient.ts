/**
 * Centralized API Client for RETRACE
 * Communicates with the FastAPI intelligence backend.
 * Provides resilient fallback handling when backend is offline or unreachable.
 */

// TEMPORARY DEVELOPMENT FALLBACK (diagnostic only, not final production configuration):
const TEMPORARY_DEV_FALLBACK_URL = 'https://retrace-api-1026070772207.us-central1.run.app';

export const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_RETRACE_API_URL;
  if (envUrl && typeof envUrl === 'string' && envUrl.trim().length > 0) {
    return envUrl.trim().replace(/\/+$/, '');
  }
  // TEMPORARY DEVELOPMENT FALLBACK:
  return TEMPORARY_DEV_FALLBACK_URL;
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
  method: 'GET' | 'POST' | 'DELETE' = 'GET',
  body?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  const { timeoutMs = 4000, headers = {} } = options;
  const baseUrl = getApiBaseUrl();
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${baseUrl}${cleanEndpoint}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
    const requestHeaders: Record<string, string> = {
      Accept: 'application/json',
      ...headers,
    };

    if (!isFormData) {
      requestHeaders['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      method,
      headers: requestHeaders,
      body: isFormData ? body : (body ? JSON.stringify(body) : undefined),
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

export type ApiConnectionState = 'connecting' | 'live' | 'mock_fallback';

export const apiClient = {
  request: executeRequest,

  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return executeRequest<T>(endpoint, 'GET', undefined, options);
  },

  async post<T>(endpoint: string, body: unknown, options?: RequestOptions): Promise<T> {
    return executeRequest<T>(endpoint, 'POST', body, options);
  },

  async upload<T>(endpoint: string, formData: FormData, options?: RequestOptions): Promise<T> {
    return executeRequest<T>(endpoint, 'POST', formData, {
      timeoutMs: options?.timeoutMs || 20000,
      headers: options?.headers,
    });
  },

  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return executeRequest<T>(endpoint, 'DELETE', undefined, options);
  },

  /**
   * Health check to detect whether FastAPI backend is actively responding
   */
  async checkHealth(): Promise<boolean> {
    const baseUrl = getApiBaseUrl();
    const healthUrl = `${baseUrl}/health`;
    const windowOrigin = typeof window !== 'undefined' ? window.location.origin : 'unknown';

    if (import.meta.env.DEV) {
      console.log(`[RETRACE DEBUG] window origin: ${windowOrigin}`);
      console.log(`[RETRACE DEBUG] configured API base URL: ${import.meta.env.VITE_RETRACE_API_URL || '(undefined, using temporary dev fallback)'}`);
      console.log(`[RETRACE DEBUG] health URL: ${healthUrl}`);
    }

    try {
      const res = await executeRequest<{ status: string }>('/health', 'GET', undefined, {
        timeoutMs: 3000,
      });
      const isHealthy = res?.status === 'healthy';
      if (isHealthy) {
        if (import.meta.env.DEV) {
          console.log(`[RETRACE] Backend connected: ${baseUrl}`);
        }
        return true;
      }
      if (import.meta.env.DEV) {
        console.warn('[RETRACE] Backend unavailable - using mock fallback');
      }
      return false;
    } catch (err) {
      if (import.meta.env.DEV) {
        console.warn('[RETRACE] Backend health check failed:', err);
      }
      return false;
    }
  },
};
