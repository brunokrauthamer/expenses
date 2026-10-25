import { buildApiUrl, refreshAccessToken, request } from './httpClient.js';

export const register = (credentials) =>
  request('/auth/register', {
    method: 'POST',
    body: credentials,
    skipAuth: true,
    retryAuth: false,
  });
export const login = (credentials) =>
  request('/auth/login', { method: 'POST', body: credentials, skipAuth: true, retryAuth: false });
export const refreshSession = (options) => refreshAccessToken(options);
export const logout = () =>
  request('/auth/logout', { method: 'POST', skipAuth: true, retryAuth: false });
export const googleLoginEnabled = () =>
  request('/auth/google/status', { skipAuth: true, retryAuth: false });

export function googleLoginUrl({ mode = 'popup', requestId, next } = {}) {
  const params = new URLSearchParams({ mode, request_id: requestId, next });
  return `${buildApiUrl('/auth/google/start')}?${params}`;
}
