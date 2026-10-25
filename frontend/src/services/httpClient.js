const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL?.trim() || '/api').replace(/\/+$/, '');
let accessToken = null;
let refreshRequest = null;
let authGeneration = 0;

export function setAccessToken(token) {
  authGeneration += 1;
  accessToken = token;
}

export function clearAccessToken() {
  authGeneration += 1;
  accessToken = null;
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function buildApiUrl(path) {
  return `${API_BASE_URL}${path}`;
}

export async function request(
  path,
  { signal, method = 'GET', body, skipAuth = false, retryAuth = true } = {},
) {
  let response;
  let responseText;
  let didTimeOut = false;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => {
    didTimeOut = true;
    controller.abort();
  }, 15_000);
  const abortRequest = () => controller.abort(signal.reason);
  if (signal?.aborted) abortRequest();
  else signal?.addEventListener('abort', abortRequest, { once: true });

  try {
    const headers = body === undefined ? {} : { 'Content-Type': 'application/json' };
    if (!skipAuth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
    response = await fetch(buildApiUrl(path), {
      method,
      signal: controller.signal,
      credentials: 'include',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status !== 204) responseText = await response.text();
  } catch (error) {
    if (signal?.aborted) throw error;
    if (didTimeOut) throw new ApiError('A API demorou para responder. Tente novamente.', 0);
    if (error?.name === 'AbortError') throw error;
    throw new ApiError(
      'Não foi possível conectar à API. Confira se o backend está em execução.',
      0,
    );
  } finally {
    window.clearTimeout(timeout);
    signal?.removeEventListener('abort', abortRequest);
  }

  if (response.status === 204) return undefined;
  const contentType = response.headers.get('content-type') ?? '';
  if (response.ok && !contentType.includes('application/json')) {
    throw new ApiError(
      'A rota da API retornou HTML em vez de JSON. Verifique o endereço da API e a configuração do proxy.',
      response.status,
    );
  }
  let responseBody;
  try {
    responseBody = responseText ? JSON.parse(responseText) : undefined;
  } catch {
    responseBody = undefined;
  }

  if (response.status === 401 && !skipAuth && retryAuth && path !== '/auth/refresh') {
    try {
      const refreshed = await refreshAccessToken();
      if (refreshed) return request(path, { signal, method, body, retryAuth: false });
    } catch {
      clearAccessToken();
      window.dispatchEvent(new Event('auth:expired'));
    }
  }

  if (!response.ok) {
    const detail = responseBody?.detail;
    const message = Array.isArray(detail)
      ? detail.map((issue) => issue.msg).join(' ')
      : typeof detail === 'string'
        ? detail
        : 'A solicitação não pôde ser concluída.';
    throw new ApiError(message, response.status);
  }
  return responseBody;
}

export async function refreshAccessToken({ force = false } = {}) {
  if (force && refreshRequest) {
    try {
      await refreshRequest;
    } catch {
      /* A conclusão OAuth usa o cookie recém-definido. */
    }
  }
  if (!refreshRequest) {
    const generation = authGeneration;
    refreshRequest = request('/auth/refresh', { method: 'POST', skipAuth: true, retryAuth: false })
      .then((result) => {
        if (authGeneration === generation) {
          accessToken = result.access_token;
          authGeneration += 1;
        }
        return result;
      })
      .finally(() => {
        refreshRequest = null;
      });
  }
  return refreshRequest;
}
