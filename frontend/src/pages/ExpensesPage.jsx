import { memo, useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api.js';
import EmptyState from '../components/ui/EmptyState.jsx';
import Panel from '../components/ui/Panel.jsx';
import SectionHeading from '../components/ui/SectionHeading.jsx';
import SectionSwitcher from '../components/ui/SectionSwitcher.jsx';
import Icon from '../components/ui/Icon.jsx';
import { categoryColor } from '../components/charts/CategoryChart.jsx';
import { formatAmountInput, formatDate, formatMoney, todayISO } from '../shared/format.js';
import { getQueryErrorMessage, invalidateCachedQueries, useApiQuery } from '../shared/queryCache.js';
import { useExpenseLookups } from '../shared/useExpenseLookups.js';

const CURRENT_MONTH = new Date().toLocaleDateString('sv-SE').slice(0, 7);
const RECENT_QUERY_KEY = ['expenses', 'recent', { month: CURRENT_MONTH }];

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
    const [whole, fraction = ''] = String(expense.installment_amount ?? '0').split('.');
    return total + BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0').slice(0, 2) || '0');
  }, 0n);
  return `${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`;
}

const ExpenseForm = memo(function ExpenseForm({ categories, paymentMethods, expenseToEdit, onCancelEdit }) {
  const [form, setForm] = useState(() => expenseToEdit ? formFromExpense(expenseToEdit) : newForm());
  const [error, setError] = useState('');
  const [errorField, setErrorField] = useState('');
  const [success, setSuccess] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [keepFields, setKeepFields] = useState(false);
  const descriptionRef = useRef(null);

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
      invalidateCachedQueries(['expenses', 'recent']);
      invalidateCachedQueries(['expenses', 'summary']);
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
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          {errorField === "categoryId" && <span className="field-error" id="category-error" role="alert">{error}</span>}
        </label>

        <label className="field">
          <span>Meio de pagamento</span>
          <select name="paymentMethodId" value={form.paymentMethodId} onChange={updateField} aria-invalid={errorField === "paymentMethodId"} aria-describedby={errorField === "paymentMethodId" ? "payment-method-error" : undefined} required>
            <option value="" disabled>Selecione</option>
            {paymentMethods.map((method) => <option key={method.id} value={method.id}>{method.name}</option>)}
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

function ExpenseList({ expenses, categories, paymentMethods, isLoading, error, refetch, onEdit }) {
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
      await api.deleteExpense(expense.id);
      setMessage('Despesa excluída.');
      invalidateCachedQueries(['expenses', 'recent']);
      invalidateCachedQueries(['expenses', 'summary']);
      setExpenseToDelete(null);
    } catch (requestError) {
      setDeleteError(requestError.message || 'Não foi possível excluir esta despesa. Tente novamente.');
    } finally {
      setDeletingId(null);
    }
  }, [expenseToDelete]);

  return (
    <>
      <div className="section-heading list-heading">
        <span className="step-number">02</span>
        <div className="list-heading-copy"><h2 id="monthly-payments-heading">Pagamentos do mês</h2><p>Cobranças com vencimento neste mês.</p></div>
        <strong className="monthly-payment-total" aria-label={`Total de pagamentos do mês: ${formatMoney(sumInstallmentAmounts(expenses))}`}>
          {formatMoney(sumInstallmentAmounts(expenses))}
        </strong>
        <span className="count-badge" aria-label={`${expenses?.length ?? 0} compras visíveis`}>{expenses?.length ?? 0}</span>
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
        <EmptyState title="Tudo começa com um registro." description={<>Adicione sua primeira despesa<br />e ela aparece aqui.</>} />
      )}
      {expenses?.length > 0 && (
        <ul className={`expense-list scroll-region${isLoading ? ' list-updating' : ''}`} tabIndex="0" aria-labelledby="monthly-payments-heading">
          {expenses.map((expense) => {
            const category = categories.find((item) => item.id === expense.category_id)?.name ?? 'Categoria';
            const method = paymentMethods.find((item) => item.id === expense.payment_method_id)?.name ?? 'Pagamento';
            return (
              <li className="expense-item" key={expense.id}>
                <span className="expense-symbol" style={{ '--category-color': categoryColor(expense.category_id) }} aria-hidden="true">{category.slice(0, 1).toLocaleUpperCase('pt-BR')}</span>
                <div className="expense-details">
                  <strong title={expense.description}>{expense.description}</strong>
                  <span title={`${category} · ${method}`}>
                    {category}<i>·</i>{method}<i>·</i>{formatDate(expense.expense_date)}
                    {expense.installment_count > 1 && <i>Parcela {expense.installment_number} de {expense.installment_count}</i>}
                  </span>
                </div>
                <strong className="expense-amount">{formatMoney(expense.installment_amount)}</strong>
                <div className="expense-actions">
                  <button className="icon-button" type="button" onClick={() => onEdit(expense)} aria-label={`Editar ${expense.description}`} title="Editar compra"><Icon name="edit" size={16} /></button>
                  <button className="icon-button delete-button" type="button" onClick={() => openDeleteDialog(expense)} disabled={deletingId !== null} aria-label={`Excluir ${expense.description}`} title="Excluir compra">
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
            <p className="delete-dialog-eyebrow">Excluir despesa</p>
            <h2 id="delete-dialog-title">Deseja excluir esta compra?</h2>
            <p className="delete-dialog-name">{expenseToDelete.description}</p>
            <p id="delete-dialog-description" className="delete-dialog-copy">
              {expenseToDelete.installment_count > 1
                ? `Esta compra tem ${expenseToDelete.installment_count} parcelas. A exclusão removerá todas elas.`
                : 'Esta ação removerá a despesa do seu histórico.'}
            </p>
            {deleteError && <p className="delete-dialog-error" role="alert">{deleteError}</p>}
            <div className="delete-dialog-actions">
              <button className="delete-dialog-cancel" type="button" onClick={closeDeleteDialog} disabled={deletingId !== null}>Cancelar</button>
              <button className="delete-dialog-confirm" type="button" onClick={removeExpense} disabled={deletingId !== null}>
                {deletingId !== null ? 'Excluindo…' : 'Excluir despesa'}
              </button>
            </div>
          </div>
        )}
      </dialog>
    </>
  );
}

export default function ExpensesPage() {
  const [editingExpense, setEditingExpense] = useState(null);
  const [activeSection, setActiveSection] = useState('form');
  const fetchRecentExpenses = useCallback(({ signal }) => api.getRecentExpenses(CURRENT_MONTH, signal), []);
  const { categoriesQuery, paymentMethodsQuery, categories, paymentMethods } = useExpenseLookups();
  const recentQuery = useApiQuery(RECENT_QUERY_KEY, fetchRecentExpenses);
  const lookupsAreReady = categories.length > 0 && paymentMethods.length > 0;
  const lookupsAreLoading = categoriesQuery.isLoading || paymentMethodsQuery.isLoading;
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
            <p className="form-message error-message" role="alert">Cadastre uma categoria antes de registrar despesas.</p>
          )}
          {paymentMethodsQuery.data?.length === 0 && !paymentMethodsQuery.isLoading && (
            <p className="form-message error-message" role="alert">Cadastre um meio de pagamento antes de continuar.</p>
          )}
          {lookupsAreReady && <ExpenseForm key={editingExpense?.id ?? 'new'} categories={categories} paymentMethods={paymentMethods} expenseToEdit={editingExpense} onCancelEdit={() => setEditingExpense(null)} />}
        </Panel>

        <Panel className="list-panel" id="monthly-payments-panel">
          <ExpenseList
            expenses={recentQuery.data}
            categories={categories}
            paymentMethods={paymentMethods}
            isLoading={recentQuery.isLoading || recentQuery.isFetching}
            error={recentQuery.error}
            refetch={recentQuery.refetch}
            onEdit={startEditing}
          />
        </Panel>
      </div>
    </>
  );
}
