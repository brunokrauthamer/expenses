const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL?.trim() || '/api').replace(/\/+$/, '');
let accessToken = null;
let refreshRequest = null;

export function setAccessToken(token) {
  accessToken = token;
}

export function clearAccessToken() {
  accessToken = null;
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, { signal, method = 'GET', body, skipAuth = false, retryAuth = true } = {}) {
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
    response = await fetch(`${API_BASE_URL}${path}`, {
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
    throw new ApiError('Não foi possível conectar à API. Confira se o backend está em execução.', 0);
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
      : typeof detail === 'string' ? detail : 'A solicitação não pôde ser concluída.';
    throw new ApiError(message, response.status);
  }
  return responseBody;
}

async function refreshAccessToken({ force = false } = {}) {
  if (force && refreshRequest) {
    try { await refreshRequest; } catch { /* A conclusão OAuth usa o cookie recém-definido. */ }
  }
  if (!refreshRequest) {
    refreshRequest = request('/auth/refresh', { method: 'POST', skipAuth: true, retryAuth: false })
      .then((result) => {
        setAccessToken(result.access_token);
        return result;
      })
      .finally(() => { refreshRequest = null; });
  }
  return refreshRequest;
}

export const api = {
  register: (credentials) => request('/auth/register', { method: 'POST', body: credentials, skipAuth: true, retryAuth: false }),
  login: (credentials) => request('/auth/login', { method: 'POST', body: credentials, skipAuth: true, retryAuth: false }),
  refreshSession: (options) => refreshAccessToken(options),
  logout: () => request('/auth/logout', { method: 'POST', skipAuth: true, retryAuth: false }),
  googleLoginEnabled: () => request('/auth/google/status', { skipAuth: true, retryAuth: false }),
  googleLoginUrl: ({ mode = 'popup', requestId, next } = {}) => {
    const params = new URLSearchParams({ mode, request_id: requestId, next });
    return `${API_BASE_URL}/auth/google/start?${params}`;
  },
  getCategories: (signal) => request('/categories', { signal }),
  getPaymentMethods: (signal) => request('/payment-methods', { signal }),
  getIncomeCategories: (signal) => request('/income-categories', { signal }),
  getIncomeEntries: (filters = {}, signal) => {
    const params = new URLSearchParams();
    if (filters.startMonth) params.set('start_month', filters.startMonth);
    if (filters.endMonth) params.set('end_month', filters.endMonth);
    if (filters.incomeCategoryId) params.set('income_category_id', filters.incomeCategoryId);
    if (filters.expenseCategoryId) params.set('expense_category_id', filters.expenseCategoryId);
    if (filters.search) params.set('search', filters.search);
    if (filters.page) params.set('page', String(filters.page));
    if (filters.pageSize) params.set('page_size', String(filters.pageSize));
    return request(`/income-entries?${params}`, { signal });
  },
  getRecentExpenses: (month, signal) => request(`/expenses/month?month=${month}`, { signal }),
  getExpenseHistory: (filters, signal) => {
    const params = new URLSearchParams();
    params.set('month', filters.month);
    params.set('page', String(filters.page ?? 1));
    params.set('page_size', String(filters.pageSize ?? 100));
    if (filters.categoryId) params.set('category_id', filters.categoryId);
    if (filters.paymentMethodId) params.set('payment_method_id', filters.paymentMethodId);
    if (filters.search) params.set('search', filters.search);
    return request(`/expenses/history?${params}`, { signal });
  },
  getExpenses: (filters, signal) => {
    const params = new URLSearchParams();
    params.set('month', filters.month);
    params.set('page', String(filters.page ?? 1));
    params.set('page_size', String(filters.pageSize ?? 100));
    if (filters.categoryId) params.set('category_id', filters.categoryId);
    if (filters.paymentMethodId) params.set('payment_method_id', filters.paymentMethodId);
    if (filters.search) params.set('search', filters.search);
    return request(`/expenses?${params}`, { signal });
  },
  getSummary: (filters, signal) => {
    const params = new URLSearchParams();
    params.set('start_month', filters.startMonth);
    params.set('end_month', filters.endMonth);
    if (filters.categoryId) params.set('category_id', filters.categoryId);
    if (filters.paymentMethodId) params.set('payment_method_id', filters.paymentMethodId);
    if (filters.search) params.set('search', filters.search);
    return request(`/expenses/summary?${params}`, { signal });
  },
  createExpense: (expense) => request('/expenses', { method: 'POST', body: expense }),
  updateExpense: (expenseId, expense) => request(`/expenses/${expenseId}`, { method: 'PUT', body: expense }),
  deleteExpense: (expenseId) => request(`/expenses/${expenseId}`, { method: 'DELETE' }),
  createIncomeEntry: (entry) => request('/income-entries', { method: 'POST', body: entry }),
  updateIncomeEntry: (entryId, entry) => request(`/income-entries/${entryId}`, { method: 'PUT', body: entry }),
  deleteIncomeEntry: (entryId) => request(`/income-entries/${entryId}`, { method: 'DELETE' }),
};
