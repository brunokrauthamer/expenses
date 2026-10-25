import '../../../components/FilterControls/index.css';
import { useCallback, useEffect, useState } from 'react';
import ActiveFilters from '../../../components/ActiveFilters/index.jsx';
import Button from '../../../components/Button/index.jsx';
import FormField from '../../../components/FormField/index.jsx';
import Input from '../../../components/Input/index.jsx';
import Select from '../../../components/Select/index.jsx';
import DebouncedSearchField from '../../../components/ui/DebouncedSearchField.jsx';
import Panel from '../../../components/ui/Panel.jsx';
import SectionHeading from '../../../components/ui/SectionHeading.jsx';
import { isValidMonth } from '../../../shared/dates.js';
import { monthDistance, shiftMonth } from '../../../shared/format.js';
import { defaultReportFilters, reportFilterChips } from '../filters.js';

export default function ReportFilters({
  filters,
  categories,
  paymentMethods,
  onChange,
  onReset,
  currentMonth,
}) {
  const defaults = defaultReportFilters(currentMonth);
  const [draftPeriod, setDraftPeriod] = useState({
    startMonth: filters.startMonth,
    endMonth: filters.endMonth,
  });

  useEffect(
    () => setDraftPeriod({ startMonth: filters.startMonth, endMonth: filters.endMonth }),
    [filters.startMonth, filters.endMonth],
  );

  const commitSearch = useCallback((search) => onChange({ search }), [onChange]);
  const draftDistance =
    isValidMonth(draftPeriod.startMonth) && isValidMonth(draftPeriod.endMonth)
      ? monthDistance(draftPeriod.startMonth, draftPeriod.endMonth)
      : -1;
  const draftIsValid = draftDistance >= 0 && draftDistance < 120;
  const hasUnappliedPeriod =
    draftPeriod.startMonth !== filters.startMonth || draftPeriod.endMonth !== filters.endMonth;
  const activeFilters = reportFilterChips(filters, categories, paymentMethods, defaults, onChange);

  function selectRecentMonths(count) {
    onChange({ startMonth: shiftMonth(currentMonth, -(count - 1)), endMonth: currentMonth });
  }

  return (
    <Panel className="filter-panel" id="report-filters-panel">
      <SectionHeading number="01" title="Filtros" description="Refine sua consulta." />
      <div
        className="filter-content scroll-region"
        role="region"
        aria-label="Filtros do consolidado"
        tabIndex="0"
      >
        <div className="quick-ranges" aria-label="Atalhos de período">
          {[
            { label: 'Este mês', count: 1 },
            { label: '3 meses', count: 3 },
            { label: '6 meses', count: 6 },
            { label: '12 meses', count: 12 },
          ].map((preset) => {
            const selected =
              filters.endMonth === currentMonth &&
              monthDistance(filters.startMonth, filters.endMonth) === preset.count - 1;
            return (
              <Button
                variant="secondary"
                className={`range-chip${selected ? ' is-selected' : ''}`}
                key={preset.count}
                aria-pressed={selected}
                onClick={() => selectRecentMonths(preset.count)}
              >
                {preset.label}
              </Button>
            );
          })}
        </div>

        <div className="filter-grid">
          <FormField label="De">
            <Input
              type="month"
              name="startMonth"
              value={draftPeriod.startMonth}
              onChange={(event) =>
                setDraftPeriod((current) => ({ ...current, startMonth: event.target.value }))
              }
            />
          </FormField>
          <FormField label="Até">
            <Input
              type="month"
              name="endMonth"
              value={draftPeriod.endMonth}
              onChange={(event) =>
                setDraftPeriod((current) => ({ ...current, endMonth: event.target.value }))
              }
            />
          </FormField>
          <FormField label="Categoria">
            <Select
              name="category"
              value={filters.categoryId}
              onChange={(event) => onChange({ categoryId: event.target.value })}
            >
              <option value="">Todas as categorias</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                  {category.deleted_at ? ' (excluída)' : ''}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Meio de pagamento">
            <Select
              name="paymentMethod"
              value={filters.paymentMethodId}
              onChange={(event) => onChange({ paymentMethodId: event.target.value })}
            >
              <option value="">Todos os meios</option>
              {paymentMethods.map((method) => (
                <option key={method.id} value={method.id}>
                  {method.name}
                  {method.deleted_at ? ' (excluído)' : ''}
                </option>
              ))}
            </Select>
          </FormField>
          <DebouncedSearchField value={filters.search} onCommit={commitSearch} />
        </div>
        <ActiveFilters filters={activeFilters} />
        {hasUnappliedPeriod && (
          <div className="period-apply">
            {!draftIsValid && (
              <p className="form-message error-message" role="alert">
                Escolha um período válido de até 120 meses.
              </p>
            )}
            <Button
              className="submit-button period-apply-button"
              disabled={!draftIsValid}
              onClick={() => onChange(draftPeriod)}
            >
              Aplicar período
            </Button>
          </div>
        )}
        <Button
          variant="text"
          className="text-button clear-filters"
          onClick={onReset}
          disabled={activeFilters.length === 0}
        >
          Limpar filtros
        </Button>
      </div>
    </Panel>
  );
}
