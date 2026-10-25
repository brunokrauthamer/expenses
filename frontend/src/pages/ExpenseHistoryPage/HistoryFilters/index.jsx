import '../../../components/FilterControls/index.css';
import { useCallback } from 'react';
import ActiveFilters from '../../../components/ActiveFilters/index.jsx';
import Button from '../../../components/Button/index.jsx';
import FormField from '../../../components/FormField/index.jsx';
import Input from '../../../components/Input/index.jsx';
import Select from '../../../components/Select/index.jsx';
import DebouncedSearchField from '../../../components/ui/DebouncedSearchField.jsx';
import Panel from '../../../components/ui/Panel.jsx';
import SectionHeading from '../../../components/ui/SectionHeading.jsx';
import { currentMonthISO } from '../../../shared/format.js';
import { isValidMonth } from '../../../shared/dates.js';
import { historyFilterChips } from '../filters.js';

export default function HistoryFilters({ filters, categories, paymentMethods, onChange, onReset }) {
  const defaultMonth = currentMonthISO();
  const commitSearch = useCallback((search) => onChange({ search }), [onChange]);
  const activeFilters = historyFilterChips(
    filters,
    categories,
    paymentMethods,
    defaultMonth,
    onChange,
  );

  return (
    <Panel className="filter-panel history-filter-panel" id="expense-history-filters">
      <SectionHeading number="01" title="Filtros" description="Escolha o mês e refine a lista." />
      <div
        className="filter-content scroll-region"
        role="region"
        aria-label="Filtros dos gastos"
        tabIndex="0"
      >
        <div className="filter-grid">
          <FormField label="Mês">
            <Input
              type="month"
              value={filters.month}
              onChange={(event) => {
                if (isValidMonth(event.target.value)) onChange({ month: event.target.value });
              }}
              aria-label="Mês dos gastos"
            />
          </FormField>
          <FormField label="Categoria">
            <Select
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
