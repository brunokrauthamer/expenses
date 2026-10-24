import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, clearAccessToken, setAccessToken } from '../services/api.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let active = true;
    const expire = () => {
      clearAccessToken();
      if (active) { setUser(null); setStatus('anonymous'); }
    };
    window.addEventListener('auth:expired', expire);
    api.refreshSession()
      .then((session) => {
        if (!active) return;
        setAccessToken(session.access_token);
        setUser(session.user);
        setStatus('authenticated');
      })
      .catch(() => {
        if (!active) return;
        clearAccessToken();
        setUser(null);
        setStatus('anonymous');
      });
    return () => { active = false; window.removeEventListener('auth:expired', expire); };
  }, []);

  const signIn = useCallback(async (credentials) => {
    const session = await api.login(credentials);
    setAccessToken(session.access_token);
    setUser(session.user);
    setStatus('authenticated');
    return session.user;
  }, []);

  const signUp = useCallback(async (credentials) => {
    const session = await api.register(credentials);
    setAccessToken(session.access_token);
    setUser(session.user);
    setStatus('authenticated');
    return session.user;
  }, []);

  const completeGoogleSignIn = useCallback(async () => {
    const session = await api.refreshSession({ force: true });
    setAccessToken(session.access_token);
    setUser(session.user);
    setStatus('authenticated');
    return session.user;
  }, []);

  const signOut = useCallback(async () => {
    try { await api.logout(); } catch { /* A saída local deve funcionar mesmo sem a API. */ } finally {
      clearAccessToken();
      setUser(null);
      setStatus('anonymous');
    }
  }, []);

  const value = useMemo(() => ({ user, status, signIn, signUp, completeGoogleSignIn, signOut }), [user, status, signIn, signUp, completeGoogleSignIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth precisa estar dentro de AuthProvider.');
  return context;
}
