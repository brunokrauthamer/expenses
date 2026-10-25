import Button from '../../../components/Button/index.jsx';
import FeedbackMessage from '../../../components/FeedbackMessage/index.jsx';
import FormField from '../../../components/FormField/index.jsx';
import Input from '../../../components/Input/index.jsx';

export default function CredentialsForm({
  registering,
  email,
  setEmail,
  password,
  setPassword,
  confirmation,
  setConfirmation,
  busy,
  error,
  onSubmit,
}) {
  return (
    <form className="auth-form" onSubmit={onSubmit}>
      <FormField label="E-mail" htmlFor="auth-email" required>
        <Input
          id="auth-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
          maxLength={254}
        />
      </FormField>
      <FormField label="Senha" htmlFor="auth-password" required>
        <Input
          id="auth-password"
          type="password"
          autoComplete={registering ? 'new-password' : 'current-password'}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
          minLength={registering ? 12 : 1}
          maxLength={128}
        />
      </FormField>
      {registering && (
        <FormField label="Confirme a senha" htmlFor="auth-confirmation" required>
          <Input
            id="auth-confirmation"
            type="password"
            autoComplete="new-password"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            required
            minLength={12}
            maxLength={128}
          />
        </FormField>
      )}
      {error && <FeedbackMessage type="error">{error}</FeedbackMessage>}
      <Button className="submit-button" type="submit" loading={busy}>
        <span>{busy ? 'Aguarde…' : registering ? 'Criar conta' : 'Entrar'}</span>
        <span aria-hidden="true">→</span>
      </Button>
    </form>
  );
}
