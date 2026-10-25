import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { clearAccessToken, setAccessToken } from '../../services/httpClient.js';
import { login, logout, refreshSession, register } from '../../services/auth.js';
import { clearQueryCache } from '../queryCache.js';
import { AuthContext } from './authContext.js';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('loading');
  const currentUserId = useRef(null);
  const transition = useRef(0);

  const acceptSession = useCallback((session) => {
    if (currentUserId.current !== session.user.id) clearQueryCache();
    currentUserId.current = session.user.id;
    setAccessToken(session.access_token);
    setUser(session.user);
    setStatus('authenticated');
  }, []);

  const clearSession = useCallback(() => {
    transition.current += 1;
    currentUserId.current = null;
    clearAccessToken();
    clearQueryCache();
    setUser(null);
    setStatus('anonymous');
  }, []);

  useEffect(() => {
    let active = true;
    const requestTransition = transition.current;
    const expire = () => clearSession();
    window.addEventListener('auth:expired', expire);
    refreshSession()
      .then((session) => {
        if (!active || transition.current !== requestTransition) return;
        acceptSession(session);
      })
      .catch(() => {
        if (!active || transition.current !== requestTransition) return;
        clearSession();
      });
    return () => {
      active = false;
      window.removeEventListener('auth:expired', expire);
    };
  }, [acceptSession, clearSession]);

  const signIn = useCallback(
    async (credentials) => {
      const requestTransition = ++transition.current;
      const session = await login(credentials);
      if (transition.current !== requestTransition) return null;
      acceptSession(session);
      return session.user;
    },
    [acceptSession],
  );

  const signUp = useCallback(
    async (credentials) => {
      const requestTransition = ++transition.current;
      const session = await register(credentials);
      if (transition.current !== requestTransition) return null;
      acceptSession(session);
      return session.user;
    },
    [acceptSession],
  );

  const completeGoogleSignIn = useCallback(async () => {
    const requestTransition = ++transition.current;
    const session = await refreshSession({ force: true });
    if (transition.current !== requestTransition) return null;
    acceptSession(session);
    return session.user;
  }, [acceptSession]);

  const signOut = useCallback(async () => {
    clearSession();
    try {
      await logout();
    } catch {
      /* A saída local deve funcionar mesmo sem a API. */
    } finally {
      currentUserId.current = null;
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({ user, status, signIn, signUp, completeGoogleSignIn, signOut }),
    [user, status, signIn, signUp, completeGoogleSignIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
