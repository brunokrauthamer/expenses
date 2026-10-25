import { useEffect } from 'react';
import AppLink from '../../components/AppLink/index.jsx';
import { navigate } from '../../store/navigation.js';
import { AuthProvider } from '../../store/auth/AuthProvider.jsx';
import { useAuth } from '../../store/auth/useAuth.js';
import { safeAuthDestination } from '../../shared/routes.js';

function RedirectCompletion({ next }) {
  const { status } = useAuth();

  useEffect(() => {
    if (status === 'authenticated') navigate(next, { replace: true });
  }, [next, status]);

  return (
    <div className="auth-loading" role="status">
      {status === 'loading' ? (
        'Confirmando seu acesso…'
      ) : (
        <span>
          Não foi possível confirmar sua sessão. <AppLink to="/entrar">Tente novamente</AppLink>
        </span>
      )}
    </div>
  );
}

function CompletionError({ reason }) {
  const message =
    reason === 'cancelled'
      ? 'O acesso com Google foi cancelado.'
      : reason === 'account_conflict'
        ? 'Este e-mail já está associado a uma conta. Entre em contato com o suporte para vinculá-la com segurança.'
        : 'Não foi possível concluir o acesso com Google. Tente novamente.';

  return (
    <div className="auth-loading completion-message">
      <p role="status">{message}</p>
      <AppLink to="/entrar">Voltar ao Expenses</AppLink>
    </div>
  );
}

export default function GoogleAuthComplete() {
  const params = new URLSearchParams(window.location.search);
  const result = params.get('result');
  const reason = params.get('reason');
  const requestId = params.get('request_id');
  const next = safeAuthDestination(params.get('next'));
  const hasOpener = Boolean(window.opener && !window.opener.closed);

  useEffect(() => {
    if (!hasOpener) return;
    try {
      window.opener.postMessage(
        {
          type: 'expenses:google-auth',
          requestId,
          success: result === 'success',
          reason: result === 'success' ? undefined : reason,
        },
        window.location.origin,
      );
      window.close();
    } catch {
      // Se a hospedagem isolar a janela, a sessão poderá ser restaurada nesta aba.
    }
  }, [hasOpener, reason, requestId, result]);

  if (hasOpener) {
    return (
      <div className="auth-loading" role="status">
        {result === 'success'
          ? 'Acesso confirmado. Você pode fechar esta janela.'
          : 'Acesso não concluído. Você pode fechar esta janela.'}
      </div>
    );
  }
  if (result !== 'success') return <CompletionError reason={reason} />;

  return (
    <AuthProvider>
      <RedirectCompletion next={next} />
    </AuthProvider>
  );
}
