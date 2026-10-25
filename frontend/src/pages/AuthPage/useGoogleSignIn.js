import { useCallback, useEffect, useRef, useState } from 'react';
import { googleLoginEnabled, googleLoginUrl } from '../../services/auth.js';
import { navigate } from '../../store/navigation.js';
import { isTrustedGoogleAuthMessage } from '../../shared/googleAuth.js';

const GOOGLE_ERROR_MESSAGES = {
  cancelled: 'O acesso com Google foi cancelado. Você pode tentar novamente quando quiser.',
  expired: 'Esta tentativa de acesso expirou. Comece novamente.',
  account_conflict:
    'Este e-mail já está associado a uma conta. Entre com e-mail e senha ou contate o suporte para vinculá-la com segurança.',
};

export function useGoogleSignIn({ next, completeGoogleSignIn, setError }) {
  const [googleEnabled, setGoogleEnabled] = useState(false);
  const [checkingConfig, setCheckingConfig] = useState(true);
  const [popupBlocked, setPopupBlocked] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const attemptRef = useRef(null);

  const finishAttempt = useCallback(() => {
    const attempt = attemptRef.current;
    if (!attempt) return;
    window.clearInterval(attempt.poll);
    window.clearTimeout(attempt.timeout);
    window.clearTimeout(attempt.closedGrace);
    window.removeEventListener('message', attempt.onMessage);
    attemptRef.current = null;
    setIsBusy(false);
  }, []);

  useEffect(() => {
    let active = true;
    googleLoginEnabled()
      .then(({ enabled }) => {
        if (active) setGoogleEnabled(Boolean(enabled));
      })
      .catch(() => {
        if (active)
          setError(
            'Não foi possível verificar a autenticação Google. Confira a conexão e tente novamente.',
          );
      })
      .finally(() => {
        if (active) setCheckingConfig(false);
      });
    return () => {
      active = false;
      finishAttempt();
    };
  }, [finishAttempt, setError]);

  const openGoogleLogin = useCallback(
    (mode = 'popup') => {
      setError('');
      setPopupBlocked(false);
      const requestId = crypto.randomUUID().replaceAll('-', '');
      const url = googleLoginUrl({ mode, requestId, next });
      if (mode === 'redirect') {
        window.location.assign(url);
        return;
      }

      const popup = window.open(
        url,
        'expenses-google-login',
        'popup,width=500,height=650,resizable=yes,scrollbars=yes',
      );
      if (!popup) {
        setPopupBlocked(true);
        setError('O navegador bloqueou a janela de acesso. Permita o popup ou continue nesta aba.');
        return;
      }

      setIsBusy(true);
      const attempt = {
        popup,
        requestId,
        poll: null,
        timeout: null,
        closedGrace: null,
        onMessage: null,
      };
      attempt.onMessage = async (event) => {
        if (
          !isTrustedGoogleAuthMessage(event, { origin: window.location.origin, popup, requestId })
        )
          return;
        const { data } = event;

        finishAttempt();
        if (!data.success) {
          setError(
            GOOGLE_ERROR_MESSAGES[data.reason] ||
              'Não foi possível entrar com Google. Tente novamente.',
          );
          return;
        }
        try {
          await completeGoogleSignIn();
          navigate(next, { replace: true });
        } catch {
          setError(
            'A conta Google foi autenticada, mas não foi possível iniciar sua sessão no Expenses. Tente novamente.',
          );
        }
      };
      attempt.poll = window.setInterval(() => {
        if (popup.closed && attemptRef.current === attempt && !attempt.closedGrace) {
          attempt.closedGrace = window.setTimeout(() => {
            if (attemptRef.current !== attempt) return;
            finishAttempt();
            setError('A janela de acesso foi fechada antes de concluir o login. Tente novamente.');
          }, 1500);
        }
      }, 350);
      attempt.timeout = window.setTimeout(
        () => {
          if (attemptRef.current === attempt) {
            popup.close();
            finishAttempt();
            setError('A tentativa de acesso expirou. Comece novamente.');
          }
        },
        5 * 60 * 1000,
      );
      attemptRef.current = attempt;
      window.addEventListener('message', attempt.onMessage);
    },
    [completeGoogleSignIn, finishAttempt, next, setError],
  );

  useEffect(
    () => () => {
      const attempt = attemptRef.current;
      if (attempt) attempt.popup.close();
      finishAttempt();
    },
    [finishAttempt],
  );

  return { googleEnabled, checkingConfig, popupBlocked, isBusy, openGoogleLogin };
}
