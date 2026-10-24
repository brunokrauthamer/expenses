import { useEffect } from 'react';
import { AppLink, navigate } from '../shared/router.jsx';
import { AuthProvider, useAuth } from '../shared/AuthContext.jsx';

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

function RedirectCompletion({ next }) {
  const { status } = useAuth();

  useEffect(() => {
    if (status === 'authenticated') navigate(next, { replace: true });
  }, [next, status]);

  return (
    <div className="auth-loading" role="status">
      {status === 'loading'
        ? 'Confirmando seu acesso…'
        : <span>Não foi possível confirmar sua sessão. <AppLink to="/entrar">Tente novamente</AppLink></span>}
    </div>
  );
}

function CompletionError({ reason }) {
  const message = reason === 'cancelled'
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
  const next = safeDestination(params.get('next'));
  const hasOpener = Boolean(window.opener && !window.opener.closed);

  useEffect(() => {
    if (!hasOpener) return;
    try {
      window.opener.postMessage({
        type: 'expenses:google-auth',
        requestId,
        success: result === 'success',
        reason: result === 'success' ? undefined : reason,
      }, window.location.origin);
      window.close();
    } catch {
      // Se a hospedagem isolar a janela, a sessão poderá ser restaurada nesta aba.
    }
  }, [hasOpener, reason, requestId, result]);

  if (hasOpener) {
    return <div className="auth-loading" role="status">{result === 'success' ? 'Acesso confirmado. Você pode fechar esta janela.' : 'Acesso não concluído. Você pode fechar esta janela.'}</div>;
  }
  if (result !== 'success') return <CompletionError reason={reason} />;

  return <AuthProvider><RedirectCompletion next={next} /></AuthProvider>;
}
