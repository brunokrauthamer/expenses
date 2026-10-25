import Button from '../../../components/Button/index.jsx';

export default function GoogleSignInButton({ checking, busy, disabled, onClick }) {
  return (
    <Button
      variant="secondary"
      className="google-button"
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-busy={busy || checking}
    >
      <svg className="google-logo" aria-hidden="true" viewBox="0 0 24 24">
        <path
          fill="#4285F4"
          d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.75 3.28-8.09Z"
        />
        <path
          fill="#34A853"
          d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A10.99 10.99 0 0 0 12 23Z"
        />
        <path
          fill="#FBBC05"
          d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84Z"
        />
        <path
          fill="#EA4335"
          d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15A10.52 10.52 0 0 0 12 1a10.99 10.99 0 0 0-9.82 6.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38Z"
        />
      </svg>
      {checking
        ? 'Verificando disponibilidade…'
        : busy
          ? 'Aguardando autenticação…'
          : 'Continuar com Google'}
    </Button>
  );
}
