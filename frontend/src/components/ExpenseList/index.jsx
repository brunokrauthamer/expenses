import './index.css';
import { useCallback, useState } from 'react';
import EmptyState from '../ui/EmptyState.jsx';
import Icon from '../ui/Icon.jsx';
import CategoryIcon from '../ui/CategoryIcon.jsx';
import ConfirmDialog from '../ConfirmDialog/index.jsx';
import IconButton from '../IconButton/index.jsx';
import { formatDate, formatMoney } from '../../shared/format.js';
import { sumMovementAmounts } from '../../shared/money.js';
import { getQueryErrorMessage } from '../../shared/errors.js';
import { removeExpense as removeExpenseRecord } from '../../store/mutations/expenses.js';
import { removeIncomeEntry as removeIncomeEntryRecord } from '../../store/mutations/incomeEntries.js';
import { categoryColor } from '../../shared/categoryColors.js';

export function ExpenseList({
  userId,
  expenses,
  categories,
  paymentMethods,
  isLoading,
  error,
  refetch,
  onEdit,
  title = 'Pagamentos do mês',
  description = 'Cada parcela aparece no mês do vencimento, pelo valor daquela parcela.',
  emptyTitle = 'Tudo começa com um registro.',
  emptyDescription = (
    <>
      Adicione sua primeira despesa
      <br />e ela aparece aqui.
    </>
  ),
  countLabel = 'pagamentos no mês',
  totalLabel = 'Total de pagamentos do mês',
}) {
  const [deletingId, setDeletingId] = useState(null);
  const [expenseToDelete, setExpenseToDelete] = useState(null);
  const [deleteError, setDeleteError] = useState('');
  const [message, setMessage] = useState('');
  const openDeleteDialog = useCallback((expense) => {
    setDeleteError('');
    setExpenseToDelete(expense);
  }, []);

  const closeDeleteDialog = useCallback(() => {
    if (deletingId !== null) return;
    setDeleteError('');
    setExpenseToDelete(null);
  }, [deletingId]);

  const removeExpense = useCallback(async () => {
    if (!expenseToDelete) return;
    const expense = expenseToDelete;
    setDeletingId(expense.id);
    setMessage('');
    setDeleteError('');
    try {
      if (expense.kind === 'reimbursement') {
        await removeIncomeEntryRecord(userId, expense.id);
        setMessage('Reembolso excluído.');
      } else {
        await removeExpenseRecord(userId, expense.id);
        setMessage('Despesa excluída.');
      }
      setExpenseToDelete(null);
    } catch (requestError) {
      setDeleteError(
        requestError.message ||
          (expense.kind === 'reimbursement'
            ? 'Não foi possível excluir este reembolso. Tente novamente.'
            : 'Não foi possível excluir esta despesa. Tente novamente.'),
      );
    } finally {
      setDeletingId(null);
    }
  }, [expenseToDelete, userId]);

  return (
    <>
      <div className="section-heading list-heading">
        <span className="step-number">02</span>
        <div className="list-heading-copy">
          <h2 id="monthly-payments-heading">{title}</h2>
          <p>{description}</p>
        </div>
        <strong
          className="monthly-payment-total"
          aria-label={`${totalLabel}: ${formatMoney(sumMovementAmounts(expenses))}`}
        >
          {formatMoney(sumMovementAmounts(expenses))}
        </strong>
        <span className="count-badge" aria-label={`${expenses?.length ?? 0} ${countLabel}`}>
          {expenses?.length ?? 0}
        </span>
      </div>
      {message && (
        <p className="form-message" role="status">
          {message}
        </p>
      )}
      {error && !expenses && (
        <div className="query-state error-state" role="alert">
          <p>{getQueryErrorMessage(error)}</p>
          <button className="text-button" type="button" onClick={refetch}>
            Tentar novamente
          </button>
        </div>
      )}
      {error && expenses && (
        <div className="query-state error-state" role="status">
          <p>Não foi possível atualizar a lista de compras.</p>
          <button className="text-button" type="button" onClick={refetch}>
            Tentar novamente
          </button>
        </div>
      )}
      {isLoading && !expenses ? (
        <div className="query-state" role="status">
          Buscando os pagamentos deste mês…
        </div>
      ) : null}
      {!isLoading && expenses?.length === 0 && (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      )}
      {expenses?.length > 0 && (
        <ul
          className={`expense-list scroll-region${isLoading ? ' list-updating' : ''}`}
          tabIndex="0"
          aria-labelledby="monthly-payments-heading"
        >
          {expenses.map((expense) => {
            const isReimbursement = expense.kind === 'reimbursement';
            const categoryRecord = categories.find((item) => item.id === expense.category_id);
            const category = expense.category_name ?? categoryRecord?.name ?? 'Categoria';
            const categoryLabel = `${category}${expense.category_deleted || categoryRecord?.deleted_at ? ' (excluída)' : ''}`;
            const methodRecord = paymentMethods.find(
              (item) => item.id === expense.payment_method_id,
            );
            const method = expense.payment_method_name ?? methodRecord?.name;
            const methodLabel = method
              ? `${method}${expense.payment_method_deleted || methodRecord?.deleted_at ? ' (excluído)' : ''}`
              : 'Pagamento';
            const eventDate = expense.event_date ?? expense.due_date ?? expense.expense_date;
            const amount = expense.amount_due ?? expense.installment_amount ?? expense.amount;
            return (
              <li
                className="expense-item"
                key={`${expense.kind ?? 'expense'}-${expense.id}-${expense.installment_id ?? expense.installment_number ?? ''}`}
              >
                <span
                  className="expense-symbol"
                  style={{ '--category-color': categoryColor(expense.category_id) }}
                  aria-hidden="true"
                >
                  <CategoryIcon name={category} size={18} />
                </span>
                <div className="expense-details">
                  <strong title={expense.description}>{expense.description}</strong>
                  <span
                    title={
                      isReimbursement
                        ? `Reembolso · ${categoryLabel}`
                        : `${categoryLabel} · ${methodLabel}`
                    }
                  >
                    {isReimbursement ? (
                      <>
                        Reembolso<i>·</i>
                        {categoryLabel}
                      </>
                    ) : (
                      <>
                        {categoryLabel}
                        <i>·</i>
                        {methodLabel}
                      </>
                    )}
                    <i>·</i>
                    {formatDate(eventDate)}
                    {!isReimbursement && expense.installment_count > 1 && (
                      <i>
                        Parcela {expense.installment_number} de {expense.installment_count}
                      </i>
                    )}
                  </span>
                </div>
                <strong
                  className={`expense-amount${isReimbursement ? ' reimbursement-amount' : ''}`}
                >
                  {isReimbursement ? '−' : ''}
                  {formatMoney(amount)}
                </strong>
                <div className="expense-actions">
                  <IconButton
                    onClick={() => onEdit(expense)}
                    aria-label={`Editar ${isReimbursement ? 'reembolso' : 'compra'} ${expense.description}`}
                    title={isReimbursement ? 'Editar reembolso' : 'Editar compra'}
                  >
                    <Icon name="edit" size={16} />
                  </IconButton>
                  <IconButton
                    className="delete-button"
                    onClick={() => openDeleteDialog(expense)}
                    disabled={deletingId !== null}
                    aria-label={`Excluir ${isReimbursement ? 'reembolso' : 'compra'} ${expense.description}`}
                    title={isReimbursement ? 'Excluir reembolso' : 'Excluir compra'}
                  >
                    <Icon name="trash" size={16} />
                  </IconButton>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <ConfirmDialog
        isOpen={Boolean(expenseToDelete)}
        title={
          expenseToDelete?.kind === 'reimbursement'
            ? 'Deseja excluir este reembolso?'
            : 'Deseja excluir esta compra?'
        }
        name={expenseToDelete?.description}
        description={
          expenseToDelete?.kind === 'reimbursement'
            ? 'Esta ação removerá o reembolso do seu histórico.'
            : expenseToDelete?.installment_count > 1
              ? `Esta compra tem ${expenseToDelete.installment_count} parcelas. A exclusão removerá todas elas.`
              : 'Esta ação removerá a despesa do seu histórico.'
        }
        error={deleteError}
        confirmLabel={
          expenseToDelete?.kind === 'reimbursement' ? 'Excluir reembolso' : 'Excluir despesa'
        }
        pendingLabel="Excluindo…"
        isPending={deletingId !== null}
        onCancel={closeDeleteDialog}
        onConfirm={removeExpense}
      />
    </>
  );
}

export default ExpenseList;
