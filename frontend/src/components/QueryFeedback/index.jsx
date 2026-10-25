import Button from '../Button/index.jsx';
import { getQueryErrorMessage } from '../../shared/errors.js';

export default function QueryFeedback({
  error,
  isLoading = false,
  hasData = false,
  refetch,
  loadingMessage = 'Carregando…',
  updatingMessage = 'Atualizando os dados…',
  className = '',
}) {
  if (error) {
    return (
      <div
        className={`query-state error-state query-feedback${className ? ` ${className}` : ''}`}
        role={hasData ? 'status' : 'alert'}
      >
        <p>{hasData ? 'Não foi possível atualizar os dados.' : getQueryErrorMessage(error)}</p>
        {refetch && (
          <Button variant="text" className="text-button" onClick={refetch}>
            Tentar novamente
          </Button>
        )}
      </div>
    );
  }
  if (!isLoading) return null;
  return (
    <p className={`query-state query-feedback${className ? ` ${className}` : ''}`} role="status">
      {hasData ? updatingMessage : loadingMessage}
    </p>
  );
}
