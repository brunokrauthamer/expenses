import './index.css';
import { useCallback, useMemo, useRef, useState } from 'react';
import AppLink from '../../components/AppLink/index.jsx';
import { navigate, useLocation } from '../../store/navigation.js';
import CategoryChart from './CategoryChart/index.jsx';
import MonthlyChart from './MonthlyChart/index.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import Panel from '../../components/ui/Panel.jsx';
import SectionHeading from '../../components/ui/SectionHeading.jsx';
import SectionSwitcher from '../../components/ui/SectionSwitcher.jsx';
import FinancialSummaryCard from '../../components/FinancialSummaryCard/index.jsx';
import ReportFilters from './ReportFilters/index.jsx';
import { readReportFilters, reportFilterPath } from './filters.js';
import { formatMoney, monthDistance } from '../../shared/format.js';
import { getQueryErrorMessage } from '../../shared/errors.js';
import { useExpenseSummary } from '../../store/queries/useExpenseSummary.js';
import { useAuth } from '../../store/auth/useAuth.js';
import { useCurrentMonth } from '../../store/useCurrentMonth.js';
import { useCategories } from '../../store/queries/useCategories.js';
import { usePaymentMethods } from '../../store/queries/usePaymentMethods.js';
import { isValidMonth } from '../../shared/dates.js';

function SummarySkeleton() {
  return (
    <div className="summary-skeleton" role="status" aria-label="Carregando o total do período">
      <span className="skeleton-line skeleton-label" />
      <span className="skeleton-line skeleton-value" />
      <span className="skeleton-line skeleton-caption" />
    </div>
  );
}

export default function ReportsPage() {
  const { user } = useAuth();
  const userId = user?.id;
  const [activeSection, setActiveSection] = useState('monthly');
  const location = useLocation();
  const separator = location.indexOf('?');
  const search = separator < 0 ? '' : location.slice(separator + 1);
  const currentMonth = useCurrentMonth();
  const filters = useMemo(() => readReportFilters(search, currentMonth), [search, currentMonth]);
  const previousResult = useRef(null);

  const changeFilters = useCallback(
    (changes) => {
      navigate(reportFilterPath({ ...filters, ...changes }), { replace: true, scroll: false });
    },
    [filters],
  );

  const rangeValid =
    isValidMonth(filters.startMonth) &&
    isValidMonth(filters.endMonth) &&
    monthDistance(filters.startMonth, filters.endMonth) >= 0 &&
    monthDistance(filters.startMonth, filters.endMonth) < 120;
  const categoriesQuery = useCategories(userId, { includeDeleted: true });
  const paymentMethodsQuery = usePaymentMethods(userId, { includeDeleted: true });
  const categories = categoriesQuery.data ?? [];
  const paymentMethods = paymentMethodsQuery.data ?? [];
  const summaryQuery = useExpenseSummary(userId, filters, { enabled: rangeValid });

  if (summaryQuery.data) previousResult.current = { userId, data: summaryQuery.data, filters };

  const previousForUser = previousResult.current?.userId === userId ? previousResult.current : null;
  const visibleResult = summaryQuery.data ?? previousForUser?.data;
  const visibleFilters = summaryQuery.data ? filters : previousForUser?.filters;
  const isFetching = summaryQuery.isFetching;
  const hasLookupError =
    (categoriesQuery.error && !categoriesQuery.data) ||
    (paymentMethodsQuery.error && !paymentMethodsQuery.data);
  const hasNotices =
    !rangeValid || (isFetching && visibleResult) || hasLookupError || summaryQuery.error;

  return (
    <>
      <section className="intro report-intro">
        <p className="eyebrow">SEUS NÚMEROS EM CONTEXTO</p>
        <h1>
          Veja para onde <span>seu dinheiro vai.</span>
        </h1>
        <p className="intro-copy">Uma visão clara das cobranças no período que você escolher.</p>
      </section>

      <SectionSwitcher
        label="Seções do consolidado"
        value={activeSection}
        onChange={setActiveSection}
        options={[
          { value: 'monthly', label: 'Evolução mensal', controls: 'monthly-chart-panel' },
          { value: 'categories', label: 'Categorias', controls: 'category-chart-panel' },
          { value: 'filters', label: 'Filtros', controls: 'report-filters-panel' },
        ]}
      />
      <div className="reports-layout" data-active-section={activeSection}>
        <ReportFilters
          filters={filters}
          currentMonth={currentMonth}
          categories={categories}
          paymentMethods={paymentMethods}
          onChange={changeFilters}
          onReset={() => navigate('/consolidado', { replace: true, scroll: false })}
        />

        <section
          className="report-results"
          id="report-results-panel"
          aria-label="Resumo das despesas do período"
        >
          <FinancialSummaryCard className="summary-card">
            {visibleResult ? (
              <div className={isFetching ? 'summary-value-updating' : ''}>
                <p className="summary-label">GASTO LÍQUIDO NO PERÍODO</p>
                <p className="summary-total">
                  {formatMoney(visibleResult.net_expense_amount ?? visibleResult.total_amount_due)}
                </p>
                <p className="summary-caption">
                  Bruto{' '}
                  {formatMoney(
                    visibleResult.gross_expense_amount ?? visibleResult.total_amount_due,
                  )}{' '}
                  · Reembolsos {formatMoney(visibleResult.reimbursement_amount ?? 0)}
                  {filters.paymentMethodId
                    ? ' · Filtro por meio considera despesas; reembolsos não têm meio associado.'
                    : ''}
                  {!summaryQuery.data && visibleFilters
                    ? ` Exibindo o período anterior: ${visibleFilters.startMonth} a ${visibleFilters.endMonth}.`
                    : ' Parcelas por vencimento e reembolsos por data de recebimento.'}
                </p>
              </div>
            ) : summaryQuery.error ? (
              <div>
                <p className="summary-label">TOTAL DAS COBRANÇAS NO PERÍODO</p>
                <p className="summary-unavailable">Não foi possível carregar</p>
              </div>
            ) : (
              <SummarySkeleton />
            )}
            <div className="summary-icon" aria-hidden="true">
              ↗
            </div>
            <div className="summary-decoration" aria-hidden="true" />
          </FinancialSummaryCard>

          {hasNotices && (
            <div
              className="report-notices scroll-region"
              role="region"
              aria-label="Avisos do consolidado"
              tabIndex="0"
            >
              {!rangeValid && (
                <p className="form-message error-message" role="alert">
                  Informe um período válido de até 120 meses.
                </p>
              )}
              {isFetching && visibleResult && (
                <p className="refresh-indicator" role="status">
                  Atualizando para o recorte selecionado…
                </p>
              )}
              {hasLookupError && (
                <div className="query-state error-state" role="alert">
                  <p>Não foi possível carregar as categorias ou os meios de pagamento.</p>
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
              {summaryQuery.error && (
                <div className="query-state error-state" role="alert">
                  <p>{getQueryErrorMessage(summaryQuery.error)}</p>
                  {visibleFilters && !summaryQuery.data && (
                    <p className="previous-data-note">
                      Os gráficos mantêm os valores do filtro anterior; {visibleFilters.startMonth}{' '}
                      a {visibleFilters.endMonth}.
                    </p>
                  )}
                  <button className="text-button" type="button" onClick={summaryQuery.refetch}>
                    Tentar novamente
                  </button>
                </div>
              )}
            </div>
          )}

          {(visibleResult || summaryQuery.isLoading) && (
            <div className="chart-grid">
              <Panel className="chart-panel monthly-panel" id="monthly-chart-panel">
                <SectionHeading
                  number="02"
                  title="Evolução mês a mês"
                  description="Veja como as cobranças variam ao longo do tempo."
                />
                <div
                  className="chart-content scroll-region"
                  role="region"
                  aria-label="Evolução mensal e tabela de valores"
                  tabIndex="0"
                >
                  {!visibleResult && summaryQuery.isLoading && (
                    <div className="chart-skeleton" role="status">
                      Carregando os valores do período…
                    </div>
                  )}
                  {visibleResult &&
                    visibleResult.monthly_totals.some((item) => Number(item.amount_due) !== 0) && (
                      <MonthlyChart totals={visibleResult.monthly_totals} isUpdating={isFetching} />
                    )}
                  {visibleResult &&
                    !visibleResult.monthly_totals.some((item) => Number(item.amount_due) !== 0) && (
                      <EmptyState
                        title="Nenhuma cobrança neste período."
                        description="Experimente ampliar as datas ou remover um filtro."
                        eyebrow="Sem movimentação"
                      />
                    )}
                  {visibleResult && visibleFilters && !summaryQuery.data && (
                    <p className="previous-data-note">
                      Exibindo o recorte anterior: {visibleFilters.startMonth} a{' '}
                      {visibleFilters.endMonth}.
                    </p>
                  )}
                </div>
              </Panel>

              <Panel className="chart-panel categories-panel" id="category-chart-panel">
                <SectionHeading
                  number="03"
                  title="Gastos por categoria"
                  description="Compare os valores dentro do mesmo período."
                />
                <div
                  className="chart-content scroll-region"
                  role="region"
                  aria-label="Categorias e tabela de valores"
                  tabIndex="0"
                >
                  {!visibleResult && summaryQuery.isLoading && (
                    <div className="chart-skeleton" role="status">
                      Carregando as categorias…
                    </div>
                  )}
                  {visibleResult && visibleResult.category_totals.length > 0 && (
                    <CategoryChart
                      totals={visibleResult.category_totals}
                      categories={categories}
                      isUpdating={isFetching}
                    />
                  )}
                  {visibleResult && visibleResult.category_totals.length === 0 && (
                    <EmptyState
                      title="Nenhuma categoria encontrada."
                      description="Experimente ajustar os filtros selecionados."
                      eyebrow="Sem resultados"
                    />
                  )}
                </div>
              </Panel>
            </div>
          )}
          <div className="report-footer">
            <p className="report-footnote">
              Despesas por vencimento das parcelas e reembolsos pela data de recebimento. Salários e
              outros ganhos serão apresentados no balanço financeiro.
            </p>
            <AppLink className="text-link back-to-entry" to="/despesas">
              ＋ Registrar despesa
            </AppLink>
          </div>
        </section>
      </div>
    </>
  );
}
