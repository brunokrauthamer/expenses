import './index.css';
import { useCallback, useState } from 'react';
import Panel from '../../components/ui/Panel.jsx';
import SectionSwitcher from '../../components/ui/SectionSwitcher.jsx';
import ExpenseForm from '../../components/ExpenseForm/index.jsx';
import IncomeForm from '../../components/IncomeForm/index.jsx';
import ExpenseList from '../../components/ExpenseList/index.jsx';
import MonthlyIncomeList from './MonthlyIncomeList/index.jsx';
import AppLink from '../../components/AppLink/index.jsx';
import { getQueryErrorMessage } from '../../shared/errors.js';
import { useAuth } from '../../store/auth/useAuth.js';
import { useCategories } from '../../store/queries/useCategories.js';
import { usePaymentMethods } from '../../store/queries/usePaymentMethods.js';
import { useIncomeCategories } from '../../store/queries/useIncomeCategories.js';
import { useMonthlyExpenses } from '../../store/queries/useMonthlyExpenses.js';
import { useIncomeEntries } from '../../store/queries/useIncomeEntries.js';
import { useCurrentMonth } from '../../store/useCurrentMonth.js';

export default function ExpensesPage() {
  const { user } = useAuth();
  const userId = user?.id;
  const [editingExpense, setEditingExpense] = useState(null);
  const [editingEntry, setEditingEntry] = useState(null);
  const [entryMode, setEntryMode] = useState(false);
  const [activeSection, setActiveSection] = useState('form');
  const currentMonth = useCurrentMonth();
  const categoriesQuery = useCategories(userId);
  const paymentMethodsQuery = usePaymentMethods(userId);
  const incomeCategoriesQuery = useIncomeCategories(userId);
  const categoryReferencesQuery = useCategories(userId, { includeDeleted: true });
  const paymentMethodReferencesQuery = usePaymentMethods(userId, { includeDeleted: true });
  const incomeCategoryReferencesQuery = useIncomeCategories(userId, { includeDeleted: true });
  const categories = categoriesQuery.data ?? [];
  const paymentMethods = paymentMethodsQuery.data ?? [];
  const incomeCategories = incomeCategoriesQuery.data ?? [];
  const categoryReferences = categoryReferencesQuery.data ?? [];
  const paymentMethodReferences = paymentMethodReferencesQuery.data ?? [];
  const incomeCategoryReferences = incomeCategoryReferencesQuery.data ?? [];
  const recentQuery = useMonthlyExpenses(userId, currentMonth);
  const lookupsAreReady = categories.length > 0 && paymentMethods.length > 0;
  const incomeQuery = useIncomeEntries(userId, {
    startMonth: currentMonth,
    endMonth: currentMonth,
  });
  const refreshIncome = useCallback(() => {
    setEditingEntry(null);
  }, []);
  const lookupsAreLoading =
    categoriesQuery.isLoading ||
    paymentMethodsQuery.isLoading ||
    (entryMode && incomeCategoriesQuery.isLoading);
  const startEditing = useCallback((expense) => {
    setEditingExpense(expense);
    setActiveSection('form');
  }, []);

  return (
    <>
      <section className="intro" id="inicio">
        <p className="eyebrow">CONTROLE PESSOAL</p>
        <h1>
          Suas despesas, <span>no seu ritmo.</span>
        </h1>
        <p className="intro-copy">Um lugar simples para acompanhar o que você gasta.</p>
      </section>
      <SectionSwitcher
        label="Seções de despesas"
        value={activeSection}
        onChange={setActiveSection}
        options={[
          {
            value: 'form',
            label: editingExpense ? 'Editar despesa' : 'Nova despesa',
            controls: 'expense-form-panel',
          },
          {
            value: 'payments',
            label: `Pagamentos do mês (${recentQuery.data?.length ?? 0})`,
            controls: 'monthly-payments-panel',
          },
        ]}
      />
      <div className="content-grid" data-active-section={activeSection}>
        <Panel
          className={`form-panel${editingExpense ? ' is-editing' : ''}`}
          id="expense-form-panel"
        >
          {!editingExpense && (
            <div
              className="payment-choice entry-mode-choice"
              role="group"
              aria-label="Tipo de registro"
            >
              <button
                className={`choice-option${!entryMode ? ' is-selected' : ''}`}
                type="button"
                onClick={() => setEntryMode(false)}
              >
                Despesa
              </button>
              <button
                className={`choice-option${entryMode ? ' is-selected' : ''}`}
                type="button"
                onClick={() => setEntryMode(true)}
              >
                Entrada
              </button>
            </div>
          )}
          {!lookupsAreReady && (categoriesQuery.error || paymentMethodsQuery.error) && (
            <div className="query-state error-state" role="alert">
              <p>{getQueryErrorMessage(categoriesQuery.error || paymentMethodsQuery.error)}</p>
              <button
                className="text-button"
                type="button"
                onClick={() => {
                  categoriesQuery.refetch();
                  paymentMethodsQuery.refetch();
                }}
              >
                Tentar novamente
              </button>
            </div>
          )}
          {!lookupsAreReady &&
            lookupsAreLoading &&
            !categoriesQuery.error &&
            !paymentMethodsQuery.error && (
              <p className="query-state" role="status">
                Carregando categorias e meios de pagamento…
              </p>
            )}
          {categoriesQuery.data?.length === 0 && !categoriesQuery.isLoading && (
            <p className="form-message error-message" role="alert">
              Você não tem categorias ativas.{' '}
              <AppLink className="text-link" to="/configuracoes">
                Adicione uma em Configurações
              </AppLink>
              .
            </p>
          )}
          {paymentMethodsQuery.data?.length === 0 && !paymentMethodsQuery.isLoading && (
            <p className="form-message error-message" role="alert">
              Você não tem meios de pagamento ativos.{' '}
              <AppLink className="text-link" to="/configuracoes">
                Adicione um em Configurações
              </AppLink>
              .
            </p>
          )}
          {entryMode && !editingExpense && (
            <IncomeForm
              key={editingEntry?.id ?? 'new-income'}
              userId={userId}
              categories={categories}
              categoryReferences={categoryReferences}
              incomeCategories={incomeCategories}
              incomeCategoryReferences={incomeCategoryReferences}
              entryToEdit={editingEntry}
              onSaved={refreshIncome}
              onCancel={() => setEditingEntry(null)}
            />
          )}
          {!entryMode && (lookupsAreReady || editingExpense) && (
            <ExpenseForm
              key={editingExpense?.id ?? 'new'}
              userId={userId}
              categories={categories}
              categoryReferences={categoryReferences}
              paymentMethods={paymentMethods}
              paymentMethodReferences={paymentMethodReferences}
              expenseToEdit={editingExpense}
              onCancelEdit={() => setEditingExpense(null)}
              onSaved={() => setEditingExpense(null)}
            />
          )}
        </Panel>

        <Panel className="list-panel" id="monthly-payments-panel">
          <MonthlyIncomeList
            userId={userId}
            entries={incomeQuery.data}
            categories={categoryReferences}
            incomeCategories={incomeCategoryReferences}
            isLoading={incomeQuery.isLoading || incomeQuery.isFetching}
            error={incomeQuery.error}
            refetch={incomeQuery.refetch}
            onEdit={(entry) => {
              setEditingEntry(entry);
              setEntryMode(true);
              setActiveSection('form');
            }}
          />
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
