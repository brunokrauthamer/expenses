import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AppLink, navigate, useLocation } from '../shared/router.jsx';
import CategoryChart from '../components/charts/CategoryChart.jsx';
import MonthlyChart from '../components/charts/MonthlyChart.jsx';
import DebouncedSearchField from '../components/ui/DebouncedSearchField.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import Panel from '../components/ui/Panel.jsx';
import SectionHeading from '../components/ui/SectionHeading.jsx';
import SectionSwitcher from '../components/ui/SectionSwitcher.jsx';
import Icon from '../components/ui/Icon.jsx';
import { currentMonthISO, formatMoney, formatMonth, monthDistance, shiftMonth } from '../shared/format.js';
import { getQueryErrorMessage, useApiQuery } from '../shared/queryCache.js';
import { useExpenseLookups } from '../shared/useExpenseLookups.js';
import { api } from '../services/api.js';

function validMonth(value) {
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(value ?? '') && Number(value.slice(0, 4)) > 0;
}

function defaultFilters() {
  const endMonth = currentMonthISO();
  return { startMonth: endMonth, endMonth, categoryId: '', paymentMethodId: '', search: '' };
}

function readFilters(search) {
  const params = new URLSearchParams(search);
  const defaults = defaultFilters();
  const requestedStart = params.get('start_month');
  const requestedEnd = params.get('end_month');
  const startMonth = validMonth(requestedStart) ? requestedStart : defaults.startMonth;
  const endMonth = validMonth(requestedEnd) ? requestedEnd : defaults.endMonth;
  const rangeIsValid = monthDistance(startMonth, endMonth) >= 0 && monthDistance(startMonth, endMonth) < 120;

  return {
    startMonth: rangeIsValid ? startMonth : defaults.startMonth,
    endMonth: rangeIsValid ? endMonth : defaults.endMonth,
    categoryId: /^\d+$/.test(params.get('category') ?? '') ? params.get('category') : '',
    paymentMethodId: /^\d+$/.test(params.get('payment_method') ?? '') ? params.get('payment_method') : '',
    search: (params.get('search') ?? '').trim(),
  };
}

function makeFilterPath(filters) {
  const params = new URLSearchParams();
  params.set('start_month', filters.startMonth);
  params.set('end_month', filters.endMonth);
  if (filters.categoryId) params.set('category', filters.categoryId);
  if (filters.paymentMethodId) params.set('payment_method', filters.paymentMethodId);
  if (filters.search) params.set('search', filters.search);
  return `/consolidado?${params}`;
}

function SummarySkeleton() {
  return (
    <div className="summary-skeleton" role="status" aria-label="Carregando o total do período">
      <span className="skeleton-line skeleton-label" />
      <span className="skeleton-line skeleton-value" />
      <span className="skeleton-line skeleton-caption" />
    </div>
  );
}

function ReportFilters({ filters, categories, paymentMethods, onChange, onReset }) {
  const currentMonth = currentMonthISO();
  const defaults = defaultFilters();
  const [draftPeriod, setDraftPeriod] = useState({ startMonth: filters.startMonth, endMonth: filters.endMonth });

  useEffect(() => setDraftPeriod({ startMonth: filters.startMonth, endMonth: filters.endMonth }), [filters.startMonth, filters.endMonth]);

  const commitSearch = useCallback((search) => onChange({ search }), [onChange]);
  const draftDistance = validMonth(draftPeriod.startMonth) && validMonth(draftPeriod.endMonth)
    ? monthDistance(draftPeriod.startMonth, draftPeriod.endMonth)
    : -1;
  const draftIsValid = draftDistance >= 0 && draftDistance < 120;
  const hasUnappliedPeriod = draftPeriod.startMonth !== filters.startMonth || draftPeriod.endMonth !== filters.endMonth;
  const activeFilters = [
    ...((filters.startMonth !== defaults.startMonth || filters.endMonth !== defaults.endMonth)
      ? [{ label: `${formatMonth(filters.startMonth)} – ${formatMonth(filters.endMonth)}`, onRemove: () => onChange({ startMonth: defaults.startMonth, endMonth: defaults.endMonth }) }]
      : []),
    ...(filters.categoryId
      ? [{ label: categories.find((item) => String(item.id) === filters.categoryId)?.name ?? 'Categoria', onRemove: () => onChange({ categoryId: '' }) }]
      : []),
    ...(filters.paymentMethodId
      ? [{ label: paymentMethods.find((item) => String(item.id) === filters.paymentMethodId)?.name ?? 'Pagamento', onRemove: () => onChange({ paymentMethodId: '' }) }]
      : []),
    ...(filters.search ? [{ label: `Busca: ${filters.search}`, onRemove: () => onChange({ search: '' }) }] : []),
  ];

  function selectRecentMonths(count) {
    onChange({ startMonth: shiftMonth(currentMonth, -(count - 1)), endMonth: currentMonth });
  }

  return (
    <Panel className="filter-panel" id="report-filters-panel">
      <SectionHeading number="01" title="Filtros" description="Refine sua consulta." />
      <div className="filter-content scroll-region" role="region" aria-label="Filtros do consolidado" tabIndex="0">
        <div className="quick-ranges" aria-label="Atalhos de período">
          {[
            { label: 'Este mês', count: 1 },
            { label: '3 meses', count: 3 },
            { label: '6 meses', count: 6 },
            { label: '12 meses', count: 12 },
          ].map((preset) => {
            const selected = filters.endMonth === currentMonth && monthDistance(filters.startMonth, filters.endMonth) === preset.count - 1;
            return <button className={`range-chip${selected ? ' is-selected' : ''}`} type="button" key={preset.count} aria-pressed={selected} onClick={() => selectRecentMonths(preset.count)}>{preset.label}</button>;
          })}
        </div>

        <div className="filter-grid">
          <label className="field">
            <span>De</span>
            <input type="month" name="startMonth" value={draftPeriod.startMonth} onChange={(event) => setDraftPeriod((current) => ({ ...current, startMonth: event.target.value }))} />
          </label>
          <label className="field">
            <span>Até</span>
            <input type="month" name="endMonth" value={draftPeriod.endMonth} onChange={(event) => setDraftPeriod((current) => ({ ...current, endMonth: event.target.value }))} />
          </label>
          <label className="field">
            <span>Categoria</span>
            <select name="category" value={filters.categoryId} onChange={(event) => onChange({ categoryId: event.target.value })}>
              <option value="">Todas as categorias</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Meio de pagamento</span>
            <select name="paymentMethod" value={filters.paymentMethodId} onChange={(event) => onChange({ paymentMethodId: event.target.value })}>
              <option value="">Todos os meios</option>
              {paymentMethods.map((method) => <option key={method.id} value={method.id}>{method.name}</option>)}
            </select>
          </label>
          <DebouncedSearchField value={filters.search} onCommit={commitSearch} />
        </div>
        {activeFilters.length > 0 && (
          <div className="active-filters" aria-label="Filtros ativos">
            <span className="active-filters-label">Ativos</span>
            {activeFilters.map((filter, index) => (
              <button className="filter-tag" type="button" key={`${filter.label}-${index}`} onClick={filter.onRemove} aria-label={`Remover filtro ${filter.label}`}>
                <span>{filter.label}</span><Icon name="close" size={14} />
              </button>
            ))}
          </div>
        )}
        {hasUnappliedPeriod && (
          <div className="period-apply">
            {!draftIsValid && <p className="form-message error-message" role="alert">Escolha um período válido de até 120 meses.</p>}
            <button className="submit-button period-apply-button" type="button" disabled={!draftIsValid} onClick={() => onChange(draftPeriod)}>Aplicar período</button>
          </div>
        )}
        <button className="text-button clear-filters" type="button" onClick={onReset} disabled={activeFilters.length === 0}>Limpar filtros</button>
      </div>
    </Panel>
  );
}

export default function ReportsPage() {
  const [activeSection, setActiveSection] = useState('monthly');
  const location = useLocation();
  const separator = location.indexOf('?');
  const search = separator < 0 ? '' : location.slice(separator + 1);
  const filters = useMemo(() => readFilters(search), [search]);
  const previousResult = useRef(null);

  const changeFilters = useCallback((changes) => {
    navigate(makeFilterPath({ ...filters, ...changes }), { replace: true, scroll: false });
  }, [filters]);

  const rangeValid = validMonth(filters.startMonth)
    && validMonth(filters.endMonth)
    && monthDistance(filters.startMonth, filters.endMonth) >= 0
    && monthDistance(filters.startMonth, filters.endMonth) < 120;
  const fetchSummary = useCallback(({ signal }) => api.getSummary(filters, signal), [filters]);
  const { categoriesQuery, paymentMethodsQuery, categories } = useExpenseLookups();
  const summaryKey = useMemo(() => ['expenses', 'summary', filters], [filters]);
  const summaryQuery = useApiQuery(summaryKey, fetchSummary, { enabled: rangeValid });

  if (summaryQuery.data) previousResult.current = { data: summaryQuery.data, filters };

  const visibleResult = summaryQuery.data ?? previousResult.current?.data;
  const visibleFilters = summaryQuery.data ? filters : previousResult.current?.filters;
  const paymentMethods = paymentMethodsQuery.data ?? [];
  const isFetching = summaryQuery.isFetching;
  const hasLookupError = (categoriesQuery.error && !categoriesQuery.data) || (paymentMethodsQuery.error && !paymentMethodsQuery.data);
  const hasNotices = !rangeValid || (isFetching && visibleResult) || hasLookupError || summaryQuery.error;

  return (
    <>
      <section className="intro report-intro">
        <p className="eyebrow">SEUS NÚMEROS EM CONTEXTO</p>
        <h1>Veja para onde <span>seu dinheiro vai.</span></h1>
        <p className="intro-copy">Uma visão clara das cobranças no período que você escolher.</p>
      </section>

      <SectionSwitcher label="Seções do consolidado" value={activeSection} onChange={setActiveSection} options={[
        { value: 'monthly', label: 'Evolução mensal', controls: 'monthly-chart-panel' },
        { value: 'categories', label: 'Categorias', controls: 'category-chart-panel' },
        { value: 'filters', label: 'Filtros', controls: 'report-filters-panel' },
      ]} />
      <div className="reports-layout" data-active-section={activeSection}>
        <ReportFilters
          filters={filters}
          categories={categories}
          paymentMethods={paymentMethods}
          onChange={changeFilters}
          onReset={() => navigate('/consolidado', { replace: true, scroll: false })}
        />

        <section className="report-results" id="report-results-panel" aria-label="Resumo das despesas do período">
          <Panel className="summary-card report-total">
            {visibleResult ? (
              <div className={isFetching ? 'summary-value-updating' : ''}>
                <p className="summary-label">GASTO LÍQUIDO NO PERÍODO</p>
                <p className="summary-total">{formatMoney(visibleResult.net_expense_amount ?? visibleResult.total_amount_due)}</p>
                <p className="summary-caption">Bruto {formatMoney(visibleResult.gross_expense_amount ?? visibleResult.total_amount_due)} · Reembolsos {formatMoney(visibleResult.reimbursement_amount ?? 0)}{filters.paymentMethodId ? ' · Filtro por meio considera despesas; reembolsos não têm meio associado.' : ''}{!summaryQuery.data && visibleFilters
                  ? ` Exibindo o período anterior: ${visibleFilters.startMonth} a ${visibleFilters.endMonth}.`
                  : ' Parcelas por vencimento e reembolsos por data de recebimento.'}</p>
              </div>
            ) : summaryQuery.error ? (
              <div>
                <p className="summary-label">TOTAL DAS COBRANÇAS NO PERÍODO</p>
                <p className="summary-unavailable">Não foi possível carregar</p>
              </div>
            ) : (
              <SummarySkeleton />
            )}
            <div className="summary-icon" aria-hidden="true">↗</div>
            <div className="summary-decoration" aria-hidden="true" />
          </Panel>

          {hasNotices && (
            <div className="report-notices scroll-region" role="region" aria-label="Avisos do consolidado" tabIndex="0">
              {!rangeValid && <p className="form-message error-message" role="alert">Informe um período válido de até 120 meses.</p>}
              {isFetching && visibleResult && <p className="refresh-indicator" role="status">Atualizando para o recorte selecionado…</p>}
              {hasLookupError && (
                <div className="query-state error-state" role="alert">
                  <p>Não foi possível carregar as categorias ou os meios de pagamento.</p>
                  <button className="text-button" type="button" onClick={() => { categoriesQuery.refetch(); paymentMethodsQuery.refetch(); }}>Tentar novamente</button>
                </div>
              )}
              {summaryQuery.error && (
                <div className="query-state error-state" role="alert">
                  <p>{getQueryErrorMessage(summaryQuery.error)}</p>
                  {visibleFilters && !summaryQuery.data && <p className="previous-data-note">Os gráficos mantêm os valores do filtro anterior; {visibleFilters.startMonth} a {visibleFilters.endMonth}.</p>}
                  <button className="text-button" type="button" onClick={summaryQuery.refetch}>Tentar novamente</button>
                </div>
              )}
            </div>
          )}

          {(visibleResult || summaryQuery.isLoading) && (
            <div className="chart-grid">
              <Panel className="chart-panel monthly-panel" id="monthly-chart-panel">
                <SectionHeading number="02" title="Evolução mês a mês" description="Veja como as cobranças variam ao longo do tempo." />
                <div className="chart-content scroll-region" role="region" aria-label="Evolução mensal e tabela de valores" tabIndex="0">
                  {!visibleResult && summaryQuery.isLoading && <div className="chart-skeleton" role="status">Carregando os valores do período…</div>}
                  {visibleResult && visibleResult.monthly_totals.some((item) => Number(item.amount_due) !== 0) && (
                    <MonthlyChart totals={visibleResult.monthly_totals} isUpdating={isFetching} />
                  )}
                  {visibleResult && !visibleResult.monthly_totals.some((item) => Number(item.amount_due) !== 0) && (
                    <EmptyState title="Nenhuma cobrança neste período." description="Experimente ampliar as datas ou remover um filtro." eyebrow="Sem movimentação" />
                  )}
                  {visibleResult && visibleFilters && !summaryQuery.data && (
                    <p className="previous-data-note">Exibindo o recorte anterior: {visibleFilters.startMonth} a {visibleFilters.endMonth}.</p>
                  )}
                </div>
              </Panel>

              <Panel className="chart-panel categories-panel" id="category-chart-panel">
                <SectionHeading number="03" title="Gastos por categoria" description="Compare os valores dentro do mesmo período." />
                <div className="chart-content scroll-region" role="region" aria-label="Categorias e tabela de valores" tabIndex="0">
                  {!visibleResult && summaryQuery.isLoading && <div className="chart-skeleton" role="status">Carregando as categorias…</div>}
                  {visibleResult && visibleResult.category_totals.length > 0 && (
                    <CategoryChart totals={visibleResult.category_totals} categories={categories} isUpdating={isFetching} />
                  )}
                  {visibleResult && visibleResult.category_totals.length === 0 && (
                    <EmptyState title="Nenhuma categoria encontrada." description="Experimente ajustar os filtros selecionados." eyebrow="Sem resultados" />
                  )}
                </div>
              </Panel>
            </div>
          )}
          <div className="report-footer">
            <p className="report-footnote">Despesas por vencimento das parcelas e reembolsos pela data de recebimento. Salários e outros ganhos serão apresentados no balanço financeiro.</p>
            <AppLink className="text-link back-to-entry" to="/despesas">＋ Registrar despesa</AppLink>
          </div>
        </section>
      </div>
    </>
  );
}
