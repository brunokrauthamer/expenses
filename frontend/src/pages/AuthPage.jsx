import { useCallback, useEffect, useRef, useState } from 'react';
import { AppLink, navigate, useLocation } from '../shared/router.jsx';
import { useAuth } from '../shared/AuthContext.jsx';
import { api } from '../services/api.js';

const DESTINATIONS = new Set(['/despesas', '/gastos', '/consolidado']);

function safeDestination(value) {
  try {
    const parsed = new URL(value || '/despesas', window.location.origin);
    return parsed.origin === window.location.origin && DESTINATIONS.has(parsed.pathname)
      ? `${parsed.pathname}${parsed.search}`
      : '/despesas';
  } catch {
    return '/despesas';
  }
}

const GOOGLE_ERROR_MESSAGES = {
  cancelled: 'O acesso com Google foi cancelado. Você pode tentar novamente quando quiser.',
  expired: 'Esta tentativa de acesso expirou. Comece novamente.',
  account_conflict: 'Este e-mail já está associado a uma conta. Entre com e-mail e senha ou contate o suporte para vinculá-la com segurança.',
};

export default function AuthPage({ mode = 'login' }) {
  const registering = mode === 'register';
  const { signIn, signUp, completeGoogleSignIn } = useAuth();
  const location = useLocation();
  const params = new URLSearchParams(location.split('?')[1] ?? '');
  const next = safeDestination(params.get('next'));
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [checkingConfig, setCheckingConfig] = useState(true);
  const [popupBlocked, setPopupBlocked] = useState(false);
  const attemptRef = useRef(null);

  const finishAttempt = useCallback(() => {
    const attempt = attemptRef.current;
    if (!attempt) return;
    window.clearInterval(attempt.poll);
    window.clearTimeout(attempt.timeout);
    window.clearTimeout(attempt.closedGrace);
    window.removeEventListener('message', attempt.onMessage);
    attemptRef.current = null;
    setBusy(false);
  }, []);

  useEffect(() => {
    let active = true;
    api.googleLoginEnabled()
      .then(({ enabled }) => { if (active) setGoogleEnabled(Boolean(enabled)); })
      .catch(() => { if (active) setError('Não foi possível verificar a autenticação Google. Confira a conexão e tente novamente.'); })
      .finally(() => { if (active) setCheckingConfig(false); });
    return () => {
      active = false;
      finishAttempt();
    };
  }, [finishAttempt]);

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
      navigate(next, { replace: true });
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível entrar. Tente novamente.');
    } finally {
      setBusy(false);
    }
  }

  function openGoogleLogin(mode = 'popup') {
    setError('');
    setPopupBlocked(false);
    const requestId = crypto.randomUUID().replaceAll('-', '');
    const url = api.googleLoginUrl({ mode, requestId, next });
    if (mode === 'redirect') {
      window.location.assign(url);
      return;
    }

    const popup = window.open(url, 'expenses-google-login', 'popup,width=500,height=650,resizable=yes,scrollbars=yes');
    if (!popup) {
      setPopupBlocked(true);
      setError('O navegador bloqueou a janela de acesso. Permita o popup ou continue nesta aba.');
      return;
    }

    setBusy(true);
    const attempt = { popup, requestId, poll: null, timeout: null, closedGrace: null, onMessage: null };
    attempt.onMessage = async (event) => {
      const data = event.data;
      if (
        event.origin !== window.location.origin || event.source !== popup ||
        !data || data.type !== 'expenses:google-auth' || data.requestId !== requestId ||
        typeof data.success !== 'boolean'
      ) return;

      finishAttempt();
      if (!data.success) {
        setError(GOOGLE_ERROR_MESSAGES[data.reason] || 'Não foi possível entrar com Google. Tente novamente.');
        return;
      }
      try {
        await completeGoogleSignIn();
        navigate(next, { replace: true });
      } catch {
        setError('A conta Google foi autenticada, mas não foi possível iniciar sua sessão no Expenses. Tente novamente.');
      }
    };
    attempt.poll = window.setInterval(() => {
      if (popup.closed && attemptRef.current === attempt && !attempt.closedGrace) {
        // A página de conclusão fecha o popup depois de enviar postMessage.
        // Aguarde a mensagem antes de tratar o fechamento como cancelamento.
        attempt.closedGrace = window.setTimeout(() => {
          if (attemptRef.current !== attempt) return;
          finishAttempt();
          setError('A janela de acesso foi fechada antes de concluir o login. Tente novamente.');
        }, 1500);
      }
    }, 350);
    attempt.timeout = window.setTimeout(() => {
      if (attemptRef.current === attempt) {
        popup.close();
        finishAttempt();
        setError('A tentativa de acesso expirou. Comece novamente.');
      }
    }, 5 * 60 * 1000);
    attemptRef.current = attempt;
    window.addEventListener('message', attempt.onMessage);
  }

  useEffect(() => () => {
    const attempt = attemptRef.current;
    if (attempt) attempt.popup.close();
    finishAttempt();
  }, [finishAttempt]);

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
        {(googleEnabled || checkingConfig) && <>
          <div className="auth-divider"><span>ou</span></div>
          <button
            className="google-button"
            type="button"
            onClick={() => openGoogleLogin()}
            disabled={busy || checkingConfig || !googleEnabled}
            aria-busy={busy || checkingConfig}
          >
            <svg className="google-logo" aria-hidden="true" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.75 3.28-8.09Z" />
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A10.99 10.99 0 0 0 12 23Z" />
              <path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z" />
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15A10.52 10.52 0 0 0 12 1a10.99 10.99 0 0 0-9.82 6.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z" />
            </svg>
            {checkingConfig ? 'Verificando disponibilidade…' : busy ? 'Aguardando autenticação…' : 'Continuar com Google'}
          </button>
          {popupBlocked && googleEnabled && (
            <button className="text-button auth-fallback" type="button" onClick={() => openGoogleLogin('redirect')}>
              Continuar nesta aba
            </button>
          )}
        </>}
        {!checkingConfig && !googleEnabled && !error && (
          <p className="form-message" role="status">O login Google não está configurado no servidor.</p>
        )}
        <p className="auth-switch">
          {registering ? 'Já tem uma conta?' : 'Ainda não tem uma conta?'}{' '}
          <AppLink to={registering ? '/entrar' : '/cadastro'}>{registering ? 'Entrar' : 'Cadastre-se'}</AppLink>
        </p>
      </section>
    </section>
  );
}
