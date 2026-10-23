import { useEffect, useState } from 'react';
import { AppLink, navigate, useLocation } from '../shared/router.jsx';
import { useAuth } from '../shared/AuthContext.jsx';
import { api } from '../services/api.js';

export default function AuthPage({ mode = 'login' }) {
  const registering = mode === 'register';
  const { signIn, signUp } = useAuth();
  const location = useLocation();
  const params = new URLSearchParams(location.split('?')[1] ?? '');
  const next = params.get('next') || '/despesas';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [googleEnabled, setGoogleEnabled] = useState(false);

  useEffect(() => {
    let active = true;
    api.googleLoginEnabled().then((result) => {
      if (active) setGoogleEnabled(result.enabled);
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (registering && password !== confirmation) {
      setError('As senhas precisam ser iguais.');
      return;
    }
    setBusy(true);
    try {
      if (registering) await signUp({ email, password });
      else await signIn({ email, password });
      navigate(next.startsWith('/') && !next.startsWith('//') ? next : '/despesas', { replace: true });
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível entrar. Tente novamente.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-layout">
      <section className="auth-card" aria-labelledby="auth-title">
        <AppLink className="brand auth-brand" to="/entrar" aria-label="Expenses, página inicial">
          <span className="brand-mark" aria-hidden="true">e</span>
          <span>expenses<span className="brand-period">.</span></span>
        </AppLink>
        <p className="eyebrow">SEU ESPAÇO FINANCEIRO</p>
        <h1 id="auth-title">{registering ? 'Crie sua conta' : 'Bem-vindo de volta'}</h1>
        <p className="auth-copy">{registering ? 'Cadastre-se para acompanhar seus gastos.' : 'Entre para continuar acompanhando seus gastos.'}</p>
        <form className="auth-form" onSubmit={submit}>
          <label className="field" htmlFor="auth-email">E-mail
            <input id="auth-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required maxLength={254} />
          </label>
          <label className="field" htmlFor="auth-password">Senha
            <input id="auth-password" type="password" autoComplete={registering ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} required minLength={registering ? 12 : 1} maxLength={128} />
          </label>
          {registering && <label className="field" htmlFor="auth-confirmation">Confirme a senha
            <input id="auth-confirmation" type="password" autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required minLength={12} maxLength={128} />
          </label>}
          {error && <p className="form-message error-message" role="alert">{error}</p>}
          <button className="submit-button" type="submit" disabled={busy}>
            <span>{busy ? 'Aguarde…' : registering ? 'Criar conta' : 'Entrar'}</span><span aria-hidden="true">→</span>
          </button>
        </form>
        {googleEnabled && <>
          <div className="auth-divider"><span>ou</span></div>
          <button className="google-button" type="button" onClick={() => (window.location.href = `${(import.meta.env.VITE_API_BASE_URL?.trim() || '/api').replace(/\/+$/, '')}/auth/google/start`)}>
            <span className="google-g" aria-hidden="true">G</span> Continuar com Google
          </button>
        </>}
        <p className="auth-switch">
          {registering ? 'Já tem uma conta?' : 'Ainda não tem uma conta?'}{' '}
          <AppLink to={registering ? '/entrar' : '/cadastro'}>{registering ? 'Entrar' : 'Cadastre-se'}</AppLink>
        </p>
      </section>
    </section>
  );
}
