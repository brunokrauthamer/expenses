import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api, clearAccessToken, setAccessToken } from '../services/api.js';
import { clearQueryCache } from './queryCache.js';

const AuthContext = createContext(null);

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
    const expire = () => {
      clearSession();
    };
    window.addEventListener('auth:expired', expire);
    api.refreshSession()
      .then((session) => {
        if (!active || transition.current !== requestTransition) return;
        acceptSession(session);
      })
      .catch(() => {
        if (!active || transition.current !== requestTransition) return;
        clearSession();
      });
    return () => { active = false; window.removeEventListener('auth:expired', expire); };
  }, [acceptSession, clearSession]);

  const signIn = useCallback(async (credentials) => {
    const requestTransition = ++transition.current;
    const session = await api.login(credentials);
    if (transition.current !== requestTransition) return null;
    acceptSession(session);
    return session.user;
  }, [acceptSession]);

  const signUp = useCallback(async (credentials) => {
    const requestTransition = ++transition.current;
    const session = await api.register(credentials);
    if (transition.current !== requestTransition) return null;
    acceptSession(session);
    return session.user;
  }, [acceptSession]);

  const completeGoogleSignIn = useCallback(async () => {
    const requestTransition = ++transition.current;
    const session = await api.refreshSession({ force: true });
    if (transition.current !== requestTransition) return null;
    acceptSession(session);
    return session.user;
  }, [acceptSession]);

  const signOut = useCallback(async () => {
    clearSession();
    try { await api.logout(); } catch { /* A saída local deve funcionar mesmo sem a API. */ } finally {
      currentUserId.current = null;
    }
  }, [clearSession]);

  const value = useMemo(() => ({ user, status, signIn, signUp, completeGoogleSignIn, signOut }), [user, status, signIn, signUp, completeGoogleSignIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth precisa estar dentro de AuthProvider.');
  return context;
}
