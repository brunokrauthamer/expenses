import './index.css';
import { useState } from 'react';
import AppLink from '../../components/AppLink/index.jsx';
import Button from '../../components/Button/index.jsx';
import { navigate, useLocation } from '../../store/navigation.js';
import { useAuth } from '../../store/auth/useAuth.js';
import { safeAuthDestination } from '../../shared/routes.js';
import CredentialsForm from './CredentialsForm/index.jsx';
import GoogleSignInButton from './GoogleSignInButton/index.jsx';
import { useGoogleSignIn } from './useGoogleSignIn.js';

export default function AuthPage({ mode = 'login' }) {
  const registering = mode === 'register';
  const { signIn, signUp, completeGoogleSignIn } = useAuth();
  const location = useLocation();
  const params = new URLSearchParams(location.split('?')[1] ?? '');
  const next = safeAuthDestination(params.get('next'));
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const google = useGoogleSignIn({ next, completeGoogleSignIn, setError });
  const busy = isSubmitting || google.isBusy;

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (registering && password !== confirmation) {
      setError('As senhas precisam ser iguais.');
      return;
    }
    setIsSubmitting(true);
    try {
      if (registering) await signUp({ email, password });
      else await signIn({ email, password });
      navigate(next, { replace: true });
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível entrar. Tente novamente.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="auth-layout">
      <section className="auth-card" aria-labelledby="auth-title">
        <AppLink className="brand auth-brand" to="/entrar" aria-label="Expenses, página inicial">
          <span className="brand-mark" aria-hidden="true">
            e
          </span>
          <span>
            expenses<span className="brand-period">.</span>
          </span>
        </AppLink>
        <p className="eyebrow">SEU ESPAÇO FINANCEIRO</p>
        <h1 id="auth-title">{registering ? 'Crie sua conta' : 'Bem-vindo de volta'}</h1>
        <p className="auth-copy">
          {registering
            ? 'Cadastre-se para acompanhar seus gastos.'
            : 'Entre para continuar acompanhando seus gastos.'}
        </p>
        <CredentialsForm
          registering={registering}
          email={email}
          setEmail={setEmail}
          password={password}
          setPassword={setPassword}
          confirmation={confirmation}
          setConfirmation={setConfirmation}
          busy={busy}
          error={error}
          onSubmit={submit}
        />
        {(google.googleEnabled || google.checkingConfig) && (
          <>
            <div className="auth-divider">
              <span>ou</span>
            </div>
            <GoogleSignInButton
              checking={google.checkingConfig}
              busy={google.isBusy}
              disabled={busy || google.checkingConfig || !google.googleEnabled}
              onClick={() => google.openGoogleLogin()}
            />
            {google.popupBlocked && google.googleEnabled && (
              <Button
                variant="text"
                className="text-button auth-fallback"
                onClick={() => google.openGoogleLogin('redirect')}
              >
                Continuar nesta aba
              </Button>
            )}
          </>
        )}
        {!google.checkingConfig && !google.googleEnabled && !error && (
          <p className="form-message" role="status">
            O login Google não está configurado no servidor.
          </p>
        )}
        <p className="auth-switch">
          {registering ? 'Já tem uma conta?' : 'Ainda não tem uma conta?'}{' '}
          <AppLink to={registering ? '/entrar' : '/cadastro'}>
            {registering ? 'Entrar' : 'Cadastre-se'}
          </AppLink>
        </p>
      </section>
    </section>
  );
}
