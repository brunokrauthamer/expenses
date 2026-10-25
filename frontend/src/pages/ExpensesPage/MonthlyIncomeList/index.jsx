import '../../../components/ExpenseList/index.css';
import { useState } from 'react';
import ConfirmDialog from '../../../components/ConfirmDialog/index.jsx';
import IconButton from '../../../components/IconButton/index.jsx';
import EmptyState from '../../../components/ui/EmptyState.jsx';
import Icon from '../../../components/ui/Icon.jsx';
import CategoryIcon from '../../../components/ui/CategoryIcon.jsx';
import { formatDate, formatMoney } from '../../../shared/format.js';
import { categoryColor } from '../../../shared/categoryColors.js';
import { getQueryErrorMessage } from '../../../shared/errors.js';
import { removeIncomeEntry } from '../../../store/mutations/incomeEntries.js';

export default function MonthlyIncomeList({
  userId,
  entries,
  categories,
  incomeCategories,
  isLoading,
  error,
  refetch,
  onEdit,
}) {
  const [entryToDelete, setEntryToDelete] = useState(null);
  const [deleteError, setDeleteError] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [message, setMessage] = useState('');

  async function confirmDelete() {
    if (!entryToDelete) return;
    setIsDeleting(true);
    setDeleteError('');
    setMessage('');
    try {
      await removeIncomeEntry(userId, entryToDelete.id);
      setEntryToDelete(null);
      setMessage('Entrada excluída.');
    } catch (requestError) {
      setDeleteError(requestError.message || 'Não foi possível excluir esta entrada.');
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <section className="monthly-income-section" aria-label="Entradas do mês">
      <div className="section-heading list-heading">
        <div className="list-heading-copy">
          <h2>Entradas deste mês</h2>
          <p>Valores recebidos no mês selecionado.</p>
        </div>
      </div>
      {message && (
        <p className="form-message" role="status">
          {message}
        </p>
      )}
      {error && (
        <div className="query-state error-state" role={entries ? 'status' : 'alert'}>
          <p>{entries ? 'Não foi possível atualizar as entradas.' : getQueryErrorMessage(error)}</p>
          <button className="text-button" type="button" onClick={refetch}>
            Tentar novamente
          </button>
        </div>
      )}
      {isLoading && !entries && (
        <p className="query-state" role="status">
          Carregando as entradas deste mês…
        </p>
      )}
      {entries?.items?.length > 0 && (
        <ul className="expense-list scroll-region" aria-label="Entradas recebidas neste mês">
          {entries.items.map((entry) => {
            const incomeCategory = incomeCategories.find(
              (category) => category.id === entry.income_category_id,
            );
            const type = entry.income_category_name ?? incomeCategory?.name ?? 'Entrada';
            const expenseCategory =
              entry.expense_category_name ??
              categories.find((category) => category.id === entry.expense_category_id)?.name;
            const isSalary =
              type
                .normalize('NFD')
                .replace(/[\u0300-\u036f]/g, '')
                .toLocaleLowerCase('pt-BR') === 'salario';
            return (
              <li className="expense-item" key={entry.id}>
                <span
                  className="expense-symbol"
                  style={
                    expenseCategory
                      ? { '--category-color': categoryColor(entry.expense_category_id) }
                      : undefined
                  }
                  aria-hidden="true"
                >
                  {incomeCategory?.requires_expense_category && expenseCategory ? (
                    <CategoryIcon name={expenseCategory} size={18} />
                  ) : (
                    <Icon name={isSalary ? 'salary' : 'wallet'} size={18} />
                  )}
                </span>
                <div className="expense-details">
                  <strong>{entry.description}</strong>
                  <span>
                    {type}
                    {entry.income_category_deleted ? ' (excluída)' : ''}
                    {expenseCategory
                      ? ` · ${expenseCategory}${entry.expense_category_deleted ? ' (excluída)' : ''}`
                      : ''}{' '}
                    · {formatDate(entry.received_date)}
                  </span>
                </div>
                <strong className="expense-amount">{formatMoney(entry.amount)}</strong>
                <div className="expense-actions">
                  <IconButton
                    onClick={() => onEdit(entry)}
                    aria-label={`Editar ${entry.description}`}
                    title="Editar entrada"
                  >
                    <Icon name="edit" size={16} />
                  </IconButton>
                  <IconButton
                    className="delete-button"
                    onClick={() => {
                      setDeleteError('');
                      setEntryToDelete(entry);
                    }}
                    disabled={isDeleting}
                    aria-label={`Excluir ${entry.description}`}
                    title="Excluir entrada"
                  >
                    <Icon name="trash" size={16} />
                  </IconButton>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {!isLoading && !error && entries?.items?.length === 0 && (
        <EmptyState
          title="Nenhuma entrada neste mês."
          description="Salário e reembolsos aparecerão aqui após o cadastro."
        />
      )}
      <ConfirmDialog
        isOpen={Boolean(entryToDelete)}
        title="Deseja excluir esta entrada?"
        name={entryToDelete?.description}
        description="Esta ação removerá a entrada do seu histórico."
        error={deleteError}
        confirmLabel="Excluir entrada"
        pendingLabel="Excluindo…"
        isPending={isDeleting}
        onCancel={() => {
          if (!isDeleting) setEntryToDelete(null);
        }}
        onConfirm={confirmDelete}
      />
    </section>
  );
}
