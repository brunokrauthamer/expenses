import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api.js';
import EmptyState from '../components/ui/EmptyState.jsx';
import Panel from '../components/ui/Panel.jsx';
import SectionHeading from '../components/ui/SectionHeading.jsx';
import SectionSwitcher from '../components/ui/SectionSwitcher.jsx';
import Icon from '../components/ui/Icon.jsx';
import CategoryIcon from '../components/ui/CategoryIcon.jsx';
import { AppLink } from '../shared/router.jsx';
import { categoryColor } from '../components/charts/CategoryChart.jsx';
import { formatAmountInput, formatDate, formatMoney, todayISO } from '../shared/format.js';
import { getQueryErrorMessage, invalidateCachedQueries, useApiQuery } from '../shared/queryCache.js';
import { useExpenseLookups } from '../shared/useExpenseLookups.js';
import { useAuth } from '../shared/AuthContext.jsx';

const CURRENT_MONTH = new Date().toLocaleDateString('sv-SE').slice(0, 7);

function newForm() {
  return {
    description: '',
    amount: '',
    expenseDate: todayISO(),
    categoryId: '',
    paymentMethodId: '',
    paymentType: 'one_time',
    installmentCount: '2',
    amountType: 'total',
    firstInstallmentDate: todayISO(),
  };
}

function formFromExpense(expense) {
  return {
    description: expense.description,
    amount: formatAmountInput(String(expense.total_amount).replace(/\D/g, '')),
    expenseDate: expense.expense_date,
    categoryId: String(expense.category_id),
    paymentMethodId: String(expense.payment_method_id),
    paymentType: expense.payment_type,
    installmentCount: String(expense.installment_count),
    amountType: 'total',
    firstInstallmentDate: expense.first_installment_date,
  };
}

function toAmountString(input) {
  let value = input.trim().replace(/[R$\s]/gi, '');
  if (value.includes(',')) value = value.replace(/\./g, '').replace(',', '.');
  if (!/^\d{1,10}(?:\.\d{1,2})?$/.test(value)) return null;
  const [integer, fraction = ''] = value.split('.');
  const cents = fraction.padEnd(2, '0');
  const normalizedInteger = integer.replace(/^0+(?=\d)/, '');
  if (normalizedInteger === '0' && cents === '00') return null;
  return `${normalizedInteger}.${cents}`;
}

function sumInstallmentAmounts(expenses = []) {
  const cents = expenses.reduce((total, expense) => {
    const [whole, fraction = ''] = String(expense.amount_due ?? expense.installment_amount ?? expense.amount ?? '0').split('.');
    const amount = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0').slice(0, 2) || '0');
    return total + (expense.kind === 'reimbursement' ? -amount : amount);
  }, 0n);
  return `${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`;
}

export const ExpenseForm = memo(function ExpenseForm({ userId, categories, categoryReferences = categories, paymentMethods, paymentMethodReferences = paymentMethods, expenseToEdit, onCancelEdit, onSaved }) {
  const [form, setForm] = useState(() => expenseToEdit ? formFromExpense(expenseToEdit) : newForm());
  const [error, setError] = useState('');
  const [errorField, setErrorField] = useState('');
  const [success, setSuccess] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [keepFields, setKeepFields] = useState(false);
  const descriptionRef = useRef(null);
  const categoryOptions = [...categories, ...categoryReferences.filter((item) => item.deleted_at && item.id === expenseToEdit?.category_id)];
  const paymentMethodOptions = [...paymentMethods, ...paymentMethodReferences.filter((item) => item.deleted_at && item.id === expenseToEdit?.payment_method_id)];

  useEffect(() => {
    if (expenseToEdit) descriptionRef.current?.focus({ preventScroll: true });
  }, [expenseToEdit]);

  const updateField = (event) => {
    const { name, value } = event.target;
    const nextValue = name === 'amount' ? formatAmountInput(value) : value;
    setForm((current) => ({
      ...current,
      [name]: nextValue,
      ...(name === 'paymentType' && value === 'installments' && Number(current.installmentCount) < 2
        ? { installmentCount: '2' }
        : {}),
      ...(name === 'expenseDate' && current.firstInstallmentDate === current.expenseDate
        ? { firstInstallmentDate: value }
        : {}),
    }));
    setError('');
    setErrorField('');
    setSuccess('');
  };

  function showFieldError(field, message) {
    setErrorField(field);
    setError(message);
  }

  async function submitExpense(event) {
    event.preventDefault();
    if (!form.description.trim()) {
      showFieldError('description', 'Informe uma descrição para esta despesa.');
      return;
    }
    const normalizedAmount = toAmountString(form.amount);
    if (!normalizedAmount) {
      showFieldError('amount', 'Informe um valor maior que zero, com até duas casas decimais.');
      return;
    }

    const installmentCount = form.paymentType === 'installments' ? Number(form.installmentCount) : 1;
    const minimumInstallments = form.paymentType === 'installments' ? 2 : 1;
    if (!Number.isInteger(installmentCount) || installmentCount < minimumInstallments || installmentCount > 1200) {
      showFieldError('installmentCount', 'Informe uma quantidade válida de parcelas, de 2 a 1.200.');
      return;
    }
    if (!form.categoryId || !form.paymentMethodId) {
      showFieldError((!form.categoryId ? 'categoryId' : 'paymentMethodId'), 'Escolha uma categoria e um meio de pagamento.');
      return;
    }
    if (form.paymentType === 'installments' && form.firstInstallmentDate < form.expenseDate) {
      showFieldError('firstInstallmentDate', 'A primeira parcela não pode anteceder a data da compra.');
      return;
    }

    const payload = {
      description: form.description.trim(),
      amount: normalizedAmount,
      expense_date: form.expenseDate,
      category_id: Number(form.categoryId),
      payment_method_id: Number(form.paymentMethodId),
      payment_type: form.paymentType,
      amount_type: form.paymentType === 'installments' ? form.amountType : 'total',
      installment_count: installmentCount,
      ...(form.paymentType === 'installments'
        ? { first_installment_date: form.firstInstallmentDate }
        : {}),
    };

    setIsSaving(true);
    setError('');
    setErrorField('');
    setSuccess('');
    try {
      const saved = expenseToEdit
        ? await api.updateExpense(expenseToEdit.id, payload)
        : await api.createExpense(payload);
      invalidateCachedQueries([userId, 'expenses']);
      if (expenseToEdit) {
        setForm(formFromExpense(saved));
      } else {
        setForm(() => {
          const next = newForm();
          if (keepFields) {
            next.description = form.description;
            next.categoryId = form.categoryId;
            next.paymentMethodId = form.paymentMethodId;
            next.paymentType = form.paymentType;
          }
          return next;
        });
      }
      if (expenseToEdit) onSaved?.(saved);
      setSuccess(expenseToEdit ? 'Despesa atualizada com sucesso.' : 'Despesa salva com sucesso.');
    } catch (requestError) {
      setError(requestError.message || 'Não foi possível salvar esta despesa.');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form onSubmit={submitExpense} className="expense-form">
      <SectionHeading
        number="01"
        title={expenseToEdit ? 'Editar despesa' : 'Nova despesa'}
        description={expenseToEdit ? 'Atualize os dados desta compra.' : 'Registre uma compra do seu dia.'}
        trailing={expenseToEdit && <button className="text-button cancel-edit" type="button" onClick={onCancelEdit}>Cancelar</button>}
      />
      <div className="form-fields scroll-region" role="region" aria-label="Dados da despesa" tabIndex="0">
        <label className="field full-field">
          <span>Descrição</span>
          <input ref={descriptionRef} name="description" value={form.description} onChange={updateField} placeholder="Ex.: compras da semana" maxLength="120" autoComplete="off" aria-invalid={errorField === "description"} aria-describedby={errorField === "description" ? "description-error" : undefined} required />
          {errorField === "description" && <span className="field-error" id="description-error" role="alert">{error}</span>}
        </label>

        <div className="field-row">
          <label className="field">
            <span>{form.paymentType === 'installments' && form.amountType === 'installment' ? 'Valor da parcela' : 'Valor'}</span>
            <div className="input-with-prefix">
              <span>R$</span>
              <input name="amount" type="text" inputMode="numeric" autoComplete="off" value={form.amount} onChange={updateField} placeholder="0,00" aria-label="Valor em reais" aria-invalid={errorField === "amount"} aria-describedby={errorField === "amount" ? "amount-error" : undefined} required />
            </div>
            {errorField === "amount" && <span className="field-error" id="amount-error" role="alert">{error}</span>}
          </label>
          <label className="field">
            <span>Data da compra</span>
            <input name="expenseDate" type="date" value={form.expenseDate} onChange={updateField} aria-invalid={errorField === "expenseDate"} aria-describedby={errorField === "expenseDate" ? "expense-date-error" : undefined} required />
            {errorField === "expenseDate" && <span className="field-error" id="expense-date-error" role="alert">{error}</span>}
          </label>
        </div>

        <label className="field">
          <span>Categoria</span>
          <select name="categoryId" value={form.categoryId} onChange={updateField} aria-invalid={errorField === "categoryId"} aria-describedby={errorField === "categoryId" ? "category-error" : undefined} required>
            <option value="" disabled>Selecione</option>
            {categoryOptions.map((category) => <option key={category.id} value={category.id}>{category.name}{category.deleted_at ? ' (excluída)' : ''}</option>)}
          </select>
          {errorField === "categoryId" && <span className="field-error" id="category-error" role="alert">{error}</span>}
        </label>

        <label className="field">
          <span>Meio de pagamento</span>
          <select name="paymentMethodId" value={form.paymentMethodId} onChange={updateField} aria-invalid={errorField === "paymentMethodId"} aria-describedby={errorField === "paymentMethodId" ? "payment-method-error" : undefined} required>
            <option value="" disabled>Selecione</option>
            {paymentMethodOptions.map((method) => <option key={method.id} value={method.id}>{method.name}{method.deleted_at ? ' (excluído)' : ''}</option>)}
          </select>
          {errorField === "paymentMethodId" && <span className="field-error" id="payment-method-error" role="alert">{error}</span>}
        </label>

        <fieldset className="payment-choice">
          <legend>Pagamento</legend>
          <label className={`choice-option${form.paymentType === 'one_time' ? ' is-selected' : ''}`}>
            <input type="radio" name="paymentType" value="one_time" checked={form.paymentType === 'one_time'} onChange={updateField} />
            <span>À vista</span>
          </label>
          <label className={`choice-option${form.paymentType === 'installments' ? ' is-selected' : ''}`}>
            <input type="radio" name="paymentType" value="installments" checked={form.paymentType === 'installments'} onChange={updateField} />
            <span>Parcelado</span>
          </label>
        </fieldset>

        {form.paymentType === 'installments' && (
          <div className="installment-fields">
            <div className="field-row">
              <label className="field">
                <span>Quantidade</span>
                <input name="installmentCount" type="number" inputMode="numeric" min="2" max="1200" step="1" value={form.installmentCount} onChange={updateField} aria-invalid={errorField === "installmentCount"} aria-describedby={errorField === "installmentCount" ? "installment-count-error" : undefined} required />
                {errorField === "installmentCount" && <span className="field-error" id="installment-count-error" role="alert">{error}</span>}
              </label>
              <label className="field">
                <span>O valor informado é</span>
                <select name="amountType" value={form.amountType} onChange={updateField}>
                  <option value="total">Total da compra</option>
                  <option value="installment">Cada parcela</option>
                </select>
              </label>
            </div>
            <label className="field full-field">
              <span>Data da primeira parcela</span>
              <input name="firstInstallmentDate" type="date" min={form.expenseDate} value={form.firstInstallmentDate} onChange={updateField} aria-invalid={errorField === "firstInstallmentDate"} aria-describedby={errorField === "firstInstallmentDate" ? "first-installment-error" : undefined} required />
              {errorField === "firstInstallmentDate" && <span className="field-error" id="first-installment-error" role="alert">{error}</span>}
            </label>
          </div>
        )}
      </div>
      {!expenseToEdit && (
        <label className="keep-fields-option">
          <input type="checkbox" checked={keepFields} onChange={(event) => setKeepFields(event.target.checked)} />
          <span>Manter descrição, categoria, meio de pagamento e pagamento para a próxima despesa</span>
        </label>
      )}
      {error && !errorField && <p className="form-message error-message" role="alert">{error}</p>}
      {success && <p className="form-message success-message" role="status">{success}</p>}
      <button className="submit-button" type="submit" disabled={isSaving}>
        <span>{isSaving ? 'Salvando...' : expenseToEdit ? 'Salvar alterações' : 'Adicionar despesa'}</span>
        <Icon name={expenseToEdit ? 'edit' : 'entry'} />
      </button>
    </form>
  );
});

export const IncomeForm = memo(function IncomeForm({ categories, categoryReferences = categories, incomeCategories, incomeCategoryReferences = incomeCategories, entryToEdit, onSaved, onCancel }) {
  const [description, setDescription] = useState(entryToEdit?.description ?? '');
  const [amount, setAmount] = useState(entryToEdit ? formatAmountInput(String(entryToEdit.amount).replace(/\D/g, '')) : '');
  const [receivedDate, setReceivedDate] = useState(entryToEdit?.received_date ?? todayISO());
  const [incomeCategoryId, setIncomeCategoryId] = useState(entryToEdit ? String(entryToEdit.income_category_id) : '');
  const [expenseCategoryId, setExpenseCategoryId] = useState(entryToEdit?.expense_category_id ? String(entryToEdit.expense_category_id) : '');
  const [message, setMessage] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const categoryOptions = [...categories, ...categoryReferences.filter((item) => item.deleted_at && item.id === entryToEdit?.expense_category_id)];
  const incomeCategoryOptions = [...incomeCategories, ...incomeCategoryReferences.filter((item) => item.deleted_at && item.id === entryToEdit?.income_category_id)];
  const selectedCategory = incomeCategoryOptions.find((category) => String(category.id) === incomeCategoryId);

  async function submit(event) {
    event.preventDefault();
    const normalizedAmount = toAmountString(amount);
    if (!normalizedAmount) { setMessage('Informe um valor maior que zero.'); return; }
    setIsSaving(true);
    setMessage('');
    try {
      const payload = {
        description: description.trim(), amount: normalizedAmount, received_date: receivedDate,
        income_category_id: Number(incomeCategoryId),
        ...(selectedCategory?.requires_expense_category ? { expense_category_id: Number(expenseCategoryId) } : {}),
      };
      if (entryToEdit) await api.updateIncomeEntry(entryToEdit.id, payload);
      else await api.createIncomeEntry(payload);
      if (!entryToEdit) { setDescription(''); setAmount(''); }
      onSaved(); setMessage('Entrada salva com sucesso.');
    } catch (error) { setMessage(error.message || 'Não foi possível salvar esta entrada.'); }
    finally { setIsSaving(false); }
  }

  return <form className="expense-form" onSubmit={submit}>
    <SectionHeading number="01" title={entryToEdit ? 'Editar entrada' : 'Nova entrada'} description="Registre um valor recebido." trailing={entryToEdit && <button className="text-button" type="button" onClick={onCancel}>Cancelar</button>} />
    <div className="form-fields scroll-region" role="region" aria-label="Dados da entrada" tabIndex="0">
      <label className="field full-field"><span>Descrição</span><input value={description} onChange={(event) => setDescription(event.target.value)} maxLength="120" required placeholder="Ex.: salário de outubro" /></label>
      <div className="field-row">
        <label className="field"><span>Valor recebido</span><div className="input-with-prefix"><span>R$</span><input inputMode="numeric" value={amount} onChange={(event) => setAmount(formatAmountInput(event.target.value))} placeholder="0,00" required /></div></label>
        <label className="field"><span>Data do recebimento</span><input type="date" value={receivedDate} onChange={(event) => setReceivedDate(event.target.value)} required /></label>
      </div>
      <label className="field"><span>Categoria da entrada</span><select value={incomeCategoryId} onChange={(event) => { setIncomeCategoryId(event.target.value); setExpenseCategoryId(''); }} required><option value="" disabled>Selecione</option>{incomeCategoryOptions.map((category) => <option key={category.id} value={category.id}>{category.name}{category.deleted_at ? ' (excluída)' : ''}</option>)}</select></label>
      {!incomeCategoryOptions.length && <p className="form-message error-message">Você não tem categorias de entrada ativas. <AppLink className="text-link" to="/configuracoes">Adicione uma em Configurações</AppLink>.</p>}
      {selectedCategory?.requires_expense_category && <label className="field"><span>Categoria do gasto reembolsado</span><select value={expenseCategoryId} onChange={(event) => setExpenseCategoryId(event.target.value)} required><option value="" disabled>Selecione</option>{categoryOptions.map((category) => <option key={category.id} value={category.id}>{category.name}{category.deleted_at ? ' (excluída)' : ''}</option>)}</select></label>}
    </div>
    {message && <p className="form-message" role="status">{message}</p>}
    <button className="submit-button" type="submit" disabled={isSaving || !incomeCategories.length}><span>{isSaving ? 'Salvando…' : entryToEdit ? 'Salvar alterações' : 'Adicionar entrada'}</span><Icon name="entry" /></button>
  </form>;
});

export function ExpenseList({ userId, expenses, categories, paymentMethods, isLoading, error, refetch, onEdit, title = 'Pagamentos do mês', description = 'Cada parcela aparece no mês do vencimento, pelo valor daquela parcela.', emptyTitle = 'Tudo começa com um registro.', emptyDescription = <>Adicione sua primeira despesa<br />e ela aparece aqui.</>, countLabel = 'pagamentos no mês', totalLabel = 'Total de pagamentos do mês' }) {
  const [deletingId, setDeletingId] = useState(null);
  const [expenseToDelete, setExpenseToDelete] = useState(null);
  const [deleteError, setDeleteError] = useState('');
  const [message, setMessage] = useState('');
  const deleteDialogRef = useRef(null);

  useEffect(() => {
    const dialog = deleteDialogRef.current;
    if (!dialog) return;
    if (expenseToDelete && !dialog.open) dialog.showModal();
    if (!expenseToDelete && dialog.open) dialog.close();
  }, [expenseToDelete]);

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
        await api.deleteIncomeEntry(expense.id);
        invalidateCachedQueries([userId, 'income-entries']);
        invalidateCachedQueries([userId, 'expenses']);
        setMessage('Reembolso excluído.');
      } else {
        await api.deleteExpense(expense.id);
        invalidateCachedQueries([userId, 'expenses']);
        setMessage('Despesa excluída.');
      }
      setExpenseToDelete(null);
    } catch (requestError) {
      setDeleteError(requestError.message || (expense.kind === 'reimbursement'
        ? 'Não foi possível excluir este reembolso. Tente novamente.'
        : 'Não foi possível excluir esta despesa. Tente novamente.'));
    } finally {
      setDeletingId(null);
    }
  }, [expenseToDelete, userId]);

  return (
    <>
      <div className="section-heading list-heading">
        <span className="step-number">02</span>
        <div className="list-heading-copy"><h2 id="monthly-payments-heading">{title}</h2><p>{description}</p></div>
        <strong className="monthly-payment-total" aria-label={`${totalLabel}: ${formatMoney(sumInstallmentAmounts(expenses))}`}>
          {formatMoney(sumInstallmentAmounts(expenses))}
        </strong>
        <span className="count-badge" aria-label={`${expenses?.length ?? 0} ${countLabel}`}>{expenses?.length ?? 0}</span>
      </div>
      {message && <p className="form-message" role="status">{message}</p>}
      {error && !expenses && (
        <div className="query-state error-state" role="alert">
          <p>{getQueryErrorMessage(error)}</p>
          <button className="text-button" type="button" onClick={refetch}>Tentar novamente</button>
        </div>
      )}
      {error && expenses && (
        <div className="query-state error-state" role="status">
          <p>Não foi possível atualizar a lista de compras.</p>
          <button className="text-button" type="button" onClick={refetch}>Tentar novamente</button>
        </div>
      )}
      {isLoading && !expenses ? <div className="query-state" role="status">Buscando os pagamentos deste mês…</div> : null}
      {!isLoading && expenses?.length === 0 && (
        <EmptyState title={emptyTitle} description={emptyDescription} />
      )}
      {expenses?.length > 0 && (
        <ul className={`expense-list scroll-region${isLoading ? ' list-updating' : ''}`} tabIndex="0" aria-labelledby="monthly-payments-heading">
          {expenses.map((expense) => {
            const isReimbursement = expense.kind === 'reimbursement';
            const categoryRecord = categories.find((item) => item.id === expense.category_id);
            const category = expense.category_name ?? categoryRecord?.name ?? 'Categoria';
            const categoryLabel = `${category}${expense.category_deleted || categoryRecord?.deleted_at ? ' (excluída)' : ''}`;
            const methodRecord = paymentMethods.find((item) => item.id === expense.payment_method_id);
            const method = expense.payment_method_name ?? methodRecord?.name;
            const methodLabel = method ? `${method}${expense.payment_method_deleted || methodRecord?.deleted_at ? ' (excluído)' : ''}` : 'Pagamento';
            const eventDate = expense.event_date ?? expense.due_date ?? expense.expense_date;
            const amount = expense.amount_due ?? expense.installment_amount ?? expense.amount;
            return (
              <li className="expense-item" key={`${expense.kind ?? 'expense'}-${expense.id}-${expense.installment_id ?? expense.installment_number ?? ''}`}>
                <span className="expense-symbol" style={{ '--category-color': categoryColor(expense.category_id) }} aria-hidden="true"><CategoryIcon name={category} size={18} /></span>
                <div className="expense-details">
                  <strong title={expense.description}>{expense.description}</strong>
                  <span title={isReimbursement ? `Reembolso · ${categoryLabel}` : `${categoryLabel} · ${methodLabel}`}>
                    {isReimbursement ? <>Reembolso<i>·</i>{categoryLabel}</> : <>{categoryLabel}<i>·</i>{methodLabel}</>}<i>·</i>{formatDate(eventDate)}
                    {!isReimbursement && expense.installment_count > 1 && <i>Parcela {expense.installment_number} de {expense.installment_count}</i>}
                  </span>
                </div>
                <strong className={`expense-amount${isReimbursement ? ' reimbursement-amount' : ''}`}>{isReimbursement ? '−' : ''}{formatMoney(amount)}</strong>
                <div className="expense-actions">
                  <button className="icon-button" type="button" onClick={() => onEdit(expense)} aria-label={`Editar ${isReimbursement ? 'reembolso' : 'compra'} ${expense.description}`} title={isReimbursement ? 'Editar reembolso' : 'Editar compra'}><Icon name="edit" size={16} /></button>
                  <button className="icon-button delete-button" type="button" onClick={() => openDeleteDialog(expense)} disabled={deletingId !== null} aria-label={`Excluir ${isReimbursement ? 'reembolso' : 'compra'} ${expense.description}`} title={isReimbursement ? 'Excluir reembolso' : 'Excluir compra'}>
                    <Icon name="trash" size={16} />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      <dialog
        ref={deleteDialogRef}
        className="delete-dialog"
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
        onCancel={(event) => { event.preventDefault(); closeDeleteDialog(); }}
        onClick={(event) => { if (event.target === event.currentTarget) closeDeleteDialog(); }}
      >
        {expenseToDelete && (
          <div className="delete-dialog-content">
            <span className="delete-dialog-icon" aria-hidden="true"><Icon name="trash" size={20} /></span>
            <p className="delete-dialog-eyebrow">{expenseToDelete.kind === 'reimbursement' ? 'Excluir reembolso' : 'Excluir despesa'}</p>
            <h2 id="delete-dialog-title">{expenseToDelete.kind === 'reimbursement' ? 'Deseja excluir este reembolso?' : 'Deseja excluir esta compra?'}</h2>
            <p className="delete-dialog-name">{expenseToDelete.description}</p>
            <p id="delete-dialog-description" className="delete-dialog-copy">
              {expenseToDelete.kind === 'reimbursement'
                ? 'Esta ação removerá o reembolso do seu histórico.'
                : expenseToDelete.installment_count > 1
                ? `Esta compra tem ${expenseToDelete.installment_count} parcelas. A exclusão removerá todas elas.`
                : 'Esta ação removerá a despesa do seu histórico.'}
            </p>
            {deleteError && <p className="delete-dialog-error" role="alert">{deleteError}</p>}
            <div className="delete-dialog-actions">
              <button className="delete-dialog-cancel" type="button" onClick={closeDeleteDialog} disabled={deletingId !== null}>Cancelar</button>
              <button className="delete-dialog-confirm" type="button" onClick={removeExpense} disabled={deletingId !== null}>
                {deletingId !== null ? 'Excluindo…' : expenseToDelete.kind === 'reimbursement' ? 'Excluir reembolso' : 'Excluir despesa'}
              </button>
            </div>
          </div>
        )}
      </dialog>
    </>
  );
}

export default function ExpensesPage() {
  const { user } = useAuth();
  const userId = user?.id;
  const [editingExpense, setEditingExpense] = useState(null);
  const [editingEntry, setEditingEntry] = useState(null);
  const [entryMode, setEntryMode] = useState(false);
  const [activeSection, setActiveSection] = useState('form');
  const fetchRecentExpenses = useCallback(async ({ signal }) => {
    const expenses = await api.getRecentExpenses(CURRENT_MONTH, signal);
    return [...expenses].sort((left, right) =>
      right.expense_date.localeCompare(left.expense_date)
      || right.id - left.id
      || left.installment_number - right.installment_number
    );
  }, []);
  const lookups = useExpenseLookups(userId);
  const { categoriesQuery, paymentMethodsQuery, categories, paymentMethods, categoryReferences, paymentMethodReferences, incomeCategoriesQuery, incomeCategories, incomeCategoryReferences } = lookups;
  const recentQuery = useApiQuery([userId, 'expenses', 'month', CURRENT_MONTH], fetchRecentExpenses, { enabled: Boolean(userId) });
  const lookupsAreReady = categories.length > 0 && paymentMethods.length > 0;
  const fetchMonthlyIncome = useCallback(({ signal }) => api.getIncomeEntries({ startMonth: CURRENT_MONTH, endMonth: CURRENT_MONTH }, signal), []);
  const incomeQuery = useApiQuery([userId, 'income-entries', 'month', CURRENT_MONTH], fetchMonthlyIncome, { enabled: Boolean(userId) });
  const refreshIncome = useCallback(() => {
    invalidateCachedQueries([userId, 'income-entries']);
    invalidateCachedQueries([userId, 'expenses']);
    setEditingEntry(null);
  }, [userId]);
  const deleteIncomeEntry = useCallback(async (entry) => {
    if (!window.confirm(`Excluir a entrada “${entry.description}”?`)) return;
    try { await api.deleteIncomeEntry(entry.id); refreshIncome(); }
    catch (error) { window.alert(error.message || 'Não foi possível excluir esta entrada.'); }
  }, [refreshIncome]);
  const lookupsAreLoading = categoriesQuery.isLoading || paymentMethodsQuery.isLoading || (entryMode && incomeCategoriesQuery.isLoading);
  const startEditing = useCallback((expense) => {
    setEditingExpense(expense);
    setActiveSection('form');
  }, []);

  return (
    <>
      <section className="intro" id="inicio">
        <p className="eyebrow">CONTROLE PESSOAL</p>
        <h1>Suas despesas, <span>no seu ritmo.</span></h1>
        <p className="intro-copy">Um lugar simples para acompanhar o que você gasta.</p>
      </section>
      <SectionSwitcher label="Seções de despesas" value={activeSection} onChange={setActiveSection} options={[
        { value: 'form', label: editingExpense ? 'Editar despesa' : 'Nova despesa', controls: 'expense-form-panel' },
        { value: 'payments', label: `Pagamentos do mês (${recentQuery.data?.length ?? 0})`, controls: 'monthly-payments-panel' },
      ]} />
      <div className="content-grid" data-active-section={activeSection}>
        <Panel className={`form-panel${editingExpense ? ' is-editing' : ''}`} id="expense-form-panel">
          {!editingExpense && <div className="payment-choice entry-mode-choice" role="group" aria-label="Tipo de registro"><button className={`choice-option${!entryMode ? ' is-selected' : ''}`} type="button" onClick={() => setEntryMode(false)}>Despesa</button><button className={`choice-option${entryMode ? ' is-selected' : ''}`} type="button" onClick={() => setEntryMode(true)}>Entrada</button></div>}
          {!lookupsAreReady && (categoriesQuery.error || paymentMethodsQuery.error) && (
            <div className="query-state error-state" role="alert">
              <p>{getQueryErrorMessage(categoriesQuery.error || paymentMethodsQuery.error)}</p>
              <button className="text-button" type="button" onClick={() => { categoriesQuery.refetch(); paymentMethodsQuery.refetch(); }}>Tentar novamente</button>
            </div>
          )}
          {!lookupsAreReady && lookupsAreLoading && !categoriesQuery.error && !paymentMethodsQuery.error && (
            <p className="query-state" role="status">Carregando categorias e meios de pagamento…</p>
          )}
          {categoriesQuery.data?.length === 0 && !categoriesQuery.isLoading && (
              <p className="form-message error-message" role="alert">Você não tem categorias ativas. <AppLink className="text-link" to="/configuracoes">Adicione uma em Configurações</AppLink>.</p>
          )}
          {paymentMethodsQuery.data?.length === 0 && !paymentMethodsQuery.isLoading && (
              <p className="form-message error-message" role="alert">Você não tem meios de pagamento ativos. <AppLink className="text-link" to="/configuracoes">Adicione um em Configurações</AppLink>.</p>
          )}
          {entryMode && !editingExpense && <IncomeForm key={editingEntry?.id ?? 'new-income'} categories={categories} categoryReferences={categoryReferences} incomeCategories={incomeCategories} incomeCategoryReferences={incomeCategoryReferences} entryToEdit={editingEntry} onSaved={refreshIncome} onCancel={() => setEditingEntry(null)} />}
          {!entryMode && (lookupsAreReady || editingExpense) && <ExpenseForm key={editingExpense?.id ?? 'new'} userId={userId} categories={categories} categoryReferences={categoryReferences} paymentMethods={paymentMethods} paymentMethodReferences={paymentMethodReferences} expenseToEdit={editingExpense} onCancelEdit={() => setEditingExpense(null)} onSaved={() => setEditingExpense(null)} />}
        </Panel>

        <Panel className="list-panel" id="monthly-payments-panel">
          <section className="monthly-income-section" aria-label="Entradas do mês">
          <div className="section-heading list-heading"><div className="list-heading-copy"><h2>Entradas deste mês</h2><p>Valores recebidos no mês selecionado.</p></div></div>
          {incomeQuery.error && <p className="form-message error-message" role="alert">Não foi possível carregar as entradas.</p>}
          {incomeQuery.data?.items?.length ? <ul className="expense-list scroll-region" aria-label="Entradas recebidas neste mês">{incomeQuery.data.items.map((entry) => {
            const incomeCategory = incomeCategoryReferences.find((category) => category.id === entry.income_category_id);
            const type = entry.income_category_name ?? incomeCategory?.name ?? 'Entrada';
            const expenseCategory = entry.expense_category_name ?? categoryReferences.find((category) => category.id === entry.expense_category_id)?.name;
            const isSalary = type.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR') === 'salario';
            return <li className="expense-item" key={entry.id}><span className="expense-symbol" style={expenseCategory ? { '--category-color': categoryColor(entry.expense_category_id) } : undefined} aria-hidden="true">{incomeCategory?.requires_expense_category && expenseCategory ? <CategoryIcon name={expenseCategory} size={18} /> : <Icon name={isSalary ? 'salary' : 'wallet'} size={18} />}</span><div className="expense-details"><strong>{entry.description}</strong><span>{type}{entry.income_category_deleted ? ' (excluída)' : ''}{expenseCategory ? ` · ${expenseCategory}${entry.expense_category_deleted ? ' (excluída)' : ''}` : ''} · {formatDate(entry.received_date)}</span></div><strong className="expense-amount">{formatMoney(entry.amount)}</strong><div className="expense-actions"><button className="icon-button" type="button" onClick={() => { setEditingEntry(entry); setEntryMode(true); setActiveSection('form'); }} aria-label={`Editar ${entry.description}`} title="Editar entrada"><Icon name="edit" size={16} /></button><button className="icon-button delete-button" type="button" onClick={() => deleteIncomeEntry(entry)} aria-label={`Excluir ${entry.description}`} title="Excluir entrada"><Icon name="trash" size={16} /></button></div></li>;
          })}</ul> : <EmptyState title="Nenhuma entrada neste mês." description="Salário e reembolsos aparecerão aqui após o cadastro." />}
          </section>
          <section className="monthly-payments-section" aria-label="Pagamentos do mês">
          <ExpenseList
            expenses={recentQuery.data}
            userId={userId}
            categories={categoryReferences}
            paymentMethods={paymentMethodReferences}
            isLoading={recentQuery.isLoading || recentQuery.isFetching}
            error={recentQuery.error}
            refetch={recentQuery.refetch}
            onEdit={startEditing}
          />
          </section>
        </Panel>
      </div>
    </>
  );
}
