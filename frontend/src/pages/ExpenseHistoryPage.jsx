import { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api.js';
import DebouncedSearchField from '../components/ui/DebouncedSearchField.jsx';
import Icon from '../components/ui/Icon.jsx';
import Panel from '../components/ui/Panel.jsx';
import SectionHeading from '../components/ui/SectionHeading.jsx';
import SectionSwitcher from '../components/ui/SectionSwitcher.jsx';
import { ExpenseForm, ExpenseList, IncomeForm } from './ExpensesPage.jsx';
import { formatMoney, formatMonth, currentMonthISO } from '../shared/format.js';
import { invalidateCachedQueries, useApiQuery } from '../shared/queryCache.js';
import { navigate, useLocation } from '../shared/router.jsx';
import { useExpenseLookups } from '../shared/useExpenseLookups.js';
import { useAuth } from '../shared/AuthContext.jsx';

function validMonth(value) {
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(value ?? '') && Number(value.slice(0, 4)) > 0;
}

function readFilters(search) {
  const params = new URLSearchParams(search);
  const month = params.get('month');
  const categoryId = params.get('category');
  const paymentMethodId = params.get('payment_method');
  const page = Number(params.get('page'));
  return {
    month: validMonth(month) ? month : currentMonthISO(),
    categoryId: /^\d+$/.test(categoryId ?? '') ? categoryId : '',
    paymentMethodId: /^\d+$/.test(paymentMethodId ?? '') ? paymentMethodId : '',
    search: (params.get('search') ?? '').trim(),
    page: Number.isInteger(page) && page > 0 ? page : 1,
    pageSize: 100,
  };
}

function filterPath(filters) {
  const params = new URLSearchParams();
  params.set('month', filters.month);
  if (filters.categoryId) params.set('category', filters.categoryId);
  if (filters.paymentMethodId) params.set('payment_method', filters.paymentMethodId);
  if (filters.search) params.set('search', filters.search);
  if (filters.page > 1) params.set('page', String(filters.page));
  return `/gastos?${params}`;
}

function HistoryFilters({ filters, categories, paymentMethods, onChange, onReset }) {
  const defaults = { month: currentMonthISO(), categoryId: '', paymentMethodId: '', search: '' };
  const commitSearch = useCallback((search) => onChange({ search }), [onChange]);
  const activeFilters = [
    ...(filters.month !== defaults.month ? [{ label: formatMonth(filters.month), onRemove: () => onChange({ month: defaults.month }) }] : []),
    ...(filters.categoryId ? [{ label: `${categories.find((item) => String(item.id) === filters.categoryId)?.name ?? 'Categoria'}${categories.find((item) => String(item.id) === filters.categoryId)?.deleted_at ? ' (excluída)' : ''}`, onRemove: () => onChange({ categoryId: '' }) }] : []),
    ...(filters.paymentMethodId ? [{ label: `${paymentMethods.find((item) => String(item.id) === filters.paymentMethodId)?.name ?? 'Pagamento'}${paymentMethods.find((item) => String(item.id) === filters.paymentMethodId)?.deleted_at ? ' (excluído)' : ''}`, onRemove: () => onChange({ paymentMethodId: '' }) }] : []),
    ...(filters.search ? [{ label: `Busca: ${filters.search}`, onRemove: () => onChange({ search: '' }) }] : []),
  ];

  return (
    <Panel className="filter-panel history-filter-panel" id="expense-history-filters">
      <SectionHeading number="01" title="Filtros" description="Escolha o mês e refine a lista." />
      <div className="filter-content scroll-region" role="region" aria-label="Filtros dos gastos" tabIndex="0">
        <div className="filter-grid">
          <label className="field"><span>Mês</span><input type="month" value={filters.month} onChange={(event) => { if (validMonth(event.target.value)) onChange({ month: event.target.value }); }} aria-label="Mês dos gastos" /></label>
          <label className="field"><span>Categoria</span><select value={filters.categoryId} onChange={(event) => onChange({ categoryId: event.target.value })}><option value="">Todas as categorias</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}{category.deleted_at ? ' (excluída)' : ''}</option>)}</select></label>
          <label className="field"><span>Meio de pagamento</span><select value={filters.paymentMethodId} onChange={(event) => onChange({ paymentMethodId: event.target.value })}><option value="">Todos os meios</option>{paymentMethods.map((method) => <option key={method.id} value={method.id}>{method.name}{method.deleted_at ? ' (excluído)' : ''}</option>)}</select></label>
          <DebouncedSearchField value={filters.search} onCommit={commitSearch} />
        </div>
        {activeFilters.length > 0 && <div className="active-filters" aria-label="Filtros ativos">
          <span className="active-filters-label">Ativos</span>
          {activeFilters.map((filter, index) => <button className="filter-tag" type="button" key={`${filter.label}-${index}`} onClick={filter.onRemove} aria-label={`Remover filtro ${filter.label}`}><span>{filter.label}</span><Icon name="close" size={14} /></button>)}
        </div>}
        <button className="text-button clear-filters" type="button" onClick={onReset} disabled={activeFilters.length === 0}>Limpar filtros</button>
      </div>
    </Panel>
  );
}

export default function ExpenseHistoryPage() {
  const location = useLocation();
  const separator = location.indexOf('?');
  const search = separator < 0 ? '' : location.slice(separator + 1);
  const filters = useMemo(() => readFilters(search), [search]);
  const [editingExpense, setEditingExpense] = useState(null);
  const [editingReimbursement, setEditingReimbursement] = useState(null);
  const [activeSection, setActiveSection] = useState('list');
  const { user } = useAuth();
  const userId = user?.id;
  const { categories: activeCategories, paymentMethods: activePaymentMethods, incomeCategories, incomeCategoryReferences, categoryReferences, paymentMethodReferences } = useExpenseLookups(userId);
  const fetchHistory = useCallback(({ signal }) => api.getExpenseHistory(filters, signal), [filters]);
  const historyQueryKey = useMemo(() => [userId, 'expenses', 'history', filters.month, filters.categoryId, filters.paymentMethodId, filters.search, filters.page], [userId, filters]);
  const historyQuery = useApiQuery(historyQueryKey, fetchHistory, { enabled: Boolean(userId) });
  const history = historyQuery.data;
  const isEditing = Boolean(editingExpense || editingReimbursement);

  const changeFilters = useCallback((changes) => {
    const next = { ...filters, ...changes };
    if (!Object.hasOwn(changes, 'page')) next.page = 1;
    navigate(filterPath(next), { replace: true, scroll: false });
  }, [filters]);
  const resetFilters = useCallback(() => navigate(`/gastos?month=${currentMonthISO()}`, { replace: true, scroll: false }), []);

  useEffect(() => {
    if (history && filters.page > Math.max(1, history.total_pages)) changeFilters({ page: Math.max(1, history.total_pages) });
  }, [history, filters.page, changeFilters]);

  const startEditing = useCallback((item) => {
    setEditingExpense(item.kind === 'reimbursement' ? null : item);
    setEditingReimbursement(item.kind === 'reimbursement' ? item : null);
    setActiveSection('form');
  }, []);
  const finishEditing = useCallback(() => {
    setEditingExpense(null);
    setEditingReimbursement(null);
    setActiveSection('list');
  }, []);
  const refreshReimbursements = useCallback(() => {
    invalidateCachedQueries([userId, 'income-entries']);
    invalidateCachedQueries([userId, 'expenses']);
    finishEditing();
  }, [finishEditing, userId]);

  return <>
    <section className="intro history-intro">
      <p className="eyebrow">HISTÓRICO DE DESPESAS</p>
      <h1>Seus gastos, <span>mês a mês.</span></h1>
      <p className="intro-copy">Consulte suas movimentações e reembolsos do mês escolhido.</p>
    </section>
    <SectionSwitcher label="Seções dos gastos" value={activeSection} onChange={setActiveSection} options={isEditing
      ? [{ value: 'form', label: editingExpense ? 'Editar despesa' : 'Editar reembolso', controls: 'expense-history-form' }]
      : [{ value: 'list', label: `Lista (${history?.total ?? 0})`, controls: 'expense-history-list' }, { value: 'filters', label: 'Filtros', controls: 'expense-history-filters' }]} />
    <div className={`history-layout${isEditing ? ' is-editing' : ''}`} data-active-section={activeSection}>
      {!isEditing && <HistoryFilters filters={filters} categories={categoryReferences} paymentMethods={paymentMethodReferences} onChange={changeFilters} onReset={resetFilters} />}
      {editingExpense && <Panel className="history-form-panel" id="expense-history-form"><ExpenseForm key={editingExpense.id} userId={userId} categories={activeCategories} categoryReferences={categoryReferences} paymentMethods={activePaymentMethods} paymentMethodReferences={paymentMethodReferences} expenseToEdit={editingExpense} onCancelEdit={finishEditing} onSaved={finishEditing} /></Panel>}
      {editingReimbursement && <Panel className="history-form-panel" id="expense-history-form"><IncomeForm key={editingReimbursement.id} categories={activeCategories} categoryReferences={categoryReferences} incomeCategories={incomeCategories} incomeCategoryReferences={incomeCategoryReferences} entryToEdit={editingReimbursement} onCancel={finishEditing} onSaved={refreshReimbursements} /></Panel>}
      {!isEditing && <div className="history-results">
        <Panel className="summary-card report-total history-net-total" aria-label="Resumo líquido do mês">
          {history ? <div>
            <p className="summary-label">GASTO LÍQUIDO NO MÊS</p>
            <p className="summary-total">{formatMoney(history.net_expense_amount)}</p>
            <p className="summary-caption">Bruto {formatMoney(history.gross_expense_amount)} · Reembolsos {formatMoney(history.reimbursement_amount)} · Cobranças por vencimento e reembolsos por recebimento{filters.paymentMethodId ? '; o filtro de pagamento afeta apenas cobranças.' : '.'}</p>
          </div> : <p className="query-state" role="status">{historyQuery.error ? 'Resumo indisponível.' : 'Calculando o total líquido…'}</p>}
        </Panel>
        <Panel className="history-list-panel" id="expense-history-list">
          <ExpenseList userId={userId} expenses={history?.items} categories={categoryReferences} paymentMethods={paymentMethodReferences} isLoading={historyQuery.isLoading || historyQuery.isFetching} error={historyQuery.error} refetch={historyQuery.refetch} onEdit={startEditing} title={`Movimentações de ${formatMonth(filters.month)}`} description="Cobranças por vencimento e reembolsos por recebimento." emptyTitle="Nenhuma movimentação encontrada." emptyDescription="Ajuste os filtros ou escolha outro mês." countLabel="itens visíveis" totalLabel="Saldo líquido desta página" />
          {history?.total_pages > 1 && <nav className="history-pagination" aria-label="Paginação das movimentações"><button className="text-button" type="button" disabled={filters.page <= 1} onClick={() => changeFilters({ page: filters.page - 1 })}>Anterior</button><span>Página {history.page} de {history.total_pages} · {history.total} itens</span><button className="text-button" type="button" disabled={filters.page >= history.total_pages} onClick={() => changeFilters({ page: filters.page + 1 })}>Próxima</button></nav>}
        </Panel>
      </div>}
    </div>
  </>;
}
