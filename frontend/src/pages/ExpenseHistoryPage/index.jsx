import './index.css';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Panel from '../../components/ui/Panel.jsx';
import FinancialSummaryCard from '../../components/FinancialSummaryCard/index.jsx';
import SectionSwitcher from '../../components/ui/SectionSwitcher.jsx';
import ExpenseForm from '../../components/ExpenseForm/index.jsx';
import ExpenseList from '../../components/ExpenseList/index.jsx';
import IncomeForm from '../../components/IncomeForm/index.jsx';
import HistoryFilters from './HistoryFilters/index.jsx';
import { readHistoryFilters, historyFilterPath } from './filters.js';
import { formatMoney, formatMonth, currentMonthISO } from '../../shared/format.js';
import { useExpenseHistory } from '../../store/queries/useExpenseHistory.js';
import { navigate, useLocation } from '../../store/navigation.js';
import { useAuth } from '../../store/auth/useAuth.js';
import { useCategories } from '../../store/queries/useCategories.js';
import { usePaymentMethods } from '../../store/queries/usePaymentMethods.js';
import { useIncomeCategories } from '../../store/queries/useIncomeCategories.js';

export default function ExpenseHistoryPage() {
  const location = useLocation();
  const separator = location.indexOf('?');
  const search = separator < 0 ? '' : location.slice(separator + 1);
  const filters = useMemo(() => readHistoryFilters(search), [search]);
  const [editingExpense, setEditingExpense] = useState(null);
  const [editingReimbursement, setEditingReimbursement] = useState(null);
  const [activeSection, setActiveSection] = useState('list');
  const { user } = useAuth();
  const userId = user?.id;
  const categoriesQuery = useCategories(userId);
  const paymentMethodsQuery = usePaymentMethods(userId);
  const incomeCategoriesQuery = useIncomeCategories(userId);
  const categoryReferencesQuery = useCategories(userId, { includeDeleted: true });
  const paymentMethodReferencesQuery = usePaymentMethods(userId, { includeDeleted: true });
  const incomeCategoryReferencesQuery = useIncomeCategories(userId, { includeDeleted: true });
  const activeCategories = categoriesQuery.data ?? [];
  const activePaymentMethods = paymentMethodsQuery.data ?? [];
  const incomeCategories = incomeCategoriesQuery.data ?? [];
  const categoryReferences = categoryReferencesQuery.data ?? [];
  const paymentMethodReferences = paymentMethodReferencesQuery.data ?? [];
  const incomeCategoryReferences = incomeCategoryReferencesQuery.data ?? [];
  const historyQuery = useExpenseHistory(userId, filters);
  const history = historyQuery.data;
  const isEditing = Boolean(editingExpense || editingReimbursement);

  const changeFilters = useCallback(
    (changes) => {
      const next = { ...filters, ...changes };
      if (!Object.hasOwn(changes, 'page')) next.page = 1;
      navigate(historyFilterPath(next), { replace: true, scroll: false });
    },
    [filters],
  );
  const resetFilters = useCallback(
    () => navigate(`/gastos?month=${currentMonthISO()}`, { replace: true, scroll: false }),
    [],
  );

  useEffect(() => {
    if (history && filters.page > Math.max(1, history.total_pages))
      changeFilters({ page: Math.max(1, history.total_pages) });
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
    finishEditing();
  }, [finishEditing]);

  return (
    <>
      <section className="intro history-intro">
        <p className="eyebrow">HISTÓRICO DE DESPESAS</p>
        <h1>
          Seus gastos, <span>mês a mês.</span>
        </h1>
        <p className="intro-copy">Consulte suas movimentações e reembolsos do mês escolhido.</p>
      </section>
      <SectionSwitcher
        label="Seções dos gastos"
        value={activeSection}
        onChange={setActiveSection}
        options={
          isEditing
            ? [
                {
                  value: 'form',
                  label: editingExpense ? 'Editar despesa' : 'Editar reembolso',
                  controls: 'expense-history-form',
                },
              ]
            : [
                {
                  value: 'list',
                  label: `Lista (${history?.total ?? 0})`,
                  controls: 'expense-history-list',
                },
                { value: 'filters', label: 'Filtros', controls: 'expense-history-filters' },
              ]
        }
      />
      <div
        className={`history-layout${isEditing ? ' is-editing' : ''}`}
        data-active-section={activeSection}
      >
        {!isEditing && (
          <HistoryFilters
            filters={filters}
            categories={categoryReferences}
            paymentMethods={paymentMethodReferences}
            onChange={changeFilters}
            onReset={resetFilters}
          />
        )}
        {editingExpense && (
          <Panel className="history-form-panel" id="expense-history-form">
            <ExpenseForm
              key={editingExpense.id}
              userId={userId}
              categories={activeCategories}
              categoryReferences={categoryReferences}
              paymentMethods={activePaymentMethods}
              paymentMethodReferences={paymentMethodReferences}
              expenseToEdit={editingExpense}
              onCancelEdit={finishEditing}
              onSaved={finishEditing}
            />
          </Panel>
        )}
        {editingReimbursement && (
          <Panel className="history-form-panel" id="expense-history-form">
            <IncomeForm
              key={editingReimbursement.id}
              userId={userId}
              categories={activeCategories}
              categoryReferences={categoryReferences}
              incomeCategories={incomeCategories}
              incomeCategoryReferences={incomeCategoryReferences}
              entryToEdit={editingReimbursement}
              onCancel={finishEditing}
              onSaved={refreshReimbursements}
            />
          </Panel>
        )}
        {!isEditing && (
          <div className="history-results">
            <FinancialSummaryCard
              className="summary-card history-net-total"
              aria-label="Resumo líquido do mês"
            >
              {history ? (
                <div>
                  <p className="summary-label">GASTO LÍQUIDO NO MÊS</p>
                  <p className="summary-total">{formatMoney(history.net_expense_amount)}</p>
                  <p className="summary-caption">
                    Bruto {formatMoney(history.gross_expense_amount)} · Reembolsos{' '}
                    {formatMoney(history.reimbursement_amount)} · Cobranças por vencimento e
                    reembolsos por recebimento
                    {filters.paymentMethodId
                      ? '; o filtro de pagamento afeta apenas cobranças.'
                      : '.'}
                  </p>
                </div>
              ) : (
                <p className="query-state" role="status">
                  {historyQuery.error ? 'Resumo indisponível.' : 'Calculando o total líquido…'}
                </p>
              )}
            </FinancialSummaryCard>
            <Panel className="history-list-panel" id="expense-history-list">
              <ExpenseList
                userId={userId}
                expenses={history?.items}
                categories={categoryReferences}
                paymentMethods={paymentMethodReferences}
                isLoading={historyQuery.isLoading || historyQuery.isFetching}
                error={historyQuery.error}
                refetch={historyQuery.refetch}
                onEdit={startEditing}
                title={`Movimentações de ${formatMonth(filters.month)}`}
                description="Cobranças por vencimento e reembolsos por recebimento."
                emptyTitle="Nenhuma movimentação encontrada."
                emptyDescription="Ajuste os filtros ou escolha outro mês."
                countLabel="itens visíveis"
                totalLabel="Saldo líquido desta página"
              />
              {history?.total_pages > 1 && (
                <nav className="history-pagination" aria-label="Paginação das movimentações">
                  <button
                    className="text-button"
                    type="button"
                    disabled={filters.page <= 1}
                    onClick={() => changeFilters({ page: filters.page - 1 })}
                  >
                    Anterior
                  </button>
                  <span>
                    Página {history.page} de {history.total_pages} · {history.total} itens
                  </span>
                  <button
                    className="text-button"
                    type="button"
                    disabled={filters.page >= history.total_pages}
                    onClick={() => changeFilters({ page: filters.page + 1 })}
                  >
                    Próxima
                  </button>
                </nav>
              )}
            </Panel>
          </div>
        )}
      </div>
    </>
  );
}
