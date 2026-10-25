import { currentMonthISO, formatMonth, monthDistance } from '../../shared/format.js';
import { isValidMonth } from '../../shared/dates.js';

export function defaultReportFilters(currentMonth = currentMonthISO()) {
  return {
    startMonth: currentMonth,
    endMonth: currentMonth,
    categoryId: '',
    paymentMethodId: '',
    search: '',
  };
}

export function readReportFilters(search, currentMonth = currentMonthISO()) {
  const params = new URLSearchParams(search);
  const defaults = defaultReportFilters(currentMonth);
  const requestedStart = params.get('start_month');
  const requestedEnd = params.get('end_month');
  const startMonth = isValidMonth(requestedStart) ? requestedStart : defaults.startMonth;
  const endMonth = isValidMonth(requestedEnd) ? requestedEnd : defaults.endMonth;
  const rangeIsValid =
    monthDistance(startMonth, endMonth) >= 0 && monthDistance(startMonth, endMonth) < 120;

  return {
    startMonth: rangeIsValid ? startMonth : defaults.startMonth,
    endMonth: rangeIsValid ? endMonth : defaults.endMonth,
    categoryId: /^\d+$/.test(params.get('category') ?? '') ? params.get('category') : '',
    paymentMethodId: /^\d+$/.test(params.get('payment_method') ?? '')
      ? params.get('payment_method')
      : '',
    search: (params.get('search') ?? '').trim(),
  };
}

export function reportFilterPath(filters) {
  const params = new URLSearchParams();
  params.set('start_month', filters.startMonth);
  params.set('end_month', filters.endMonth);
  if (filters.categoryId) params.set('category', filters.categoryId);
  if (filters.paymentMethodId) params.set('payment_method', filters.paymentMethodId);
  if (filters.search) params.set('search', filters.search);
  return `/consolidado?${params}`;
}

export function reportFilterChips(filters, categories, paymentMethods, defaults, onChange) {
  const category = categories.find((item) => String(item.id) === filters.categoryId);
  const paymentMethod = paymentMethods.find((item) => String(item.id) === filters.paymentMethodId);
  return [
    ...(filters.startMonth !== defaults.startMonth || filters.endMonth !== defaults.endMonth
      ? [
          {
            id: 'period',
            label: `${formatMonth(filters.startMonth)} – ${formatMonth(filters.endMonth)}`,
            onRemove: () =>
              onChange({ startMonth: defaults.startMonth, endMonth: defaults.endMonth }),
          },
        ]
      : []),
    ...(filters.categoryId
      ? [
          {
            id: 'category',
            label: `${category?.name ?? 'Categoria'}${category?.deleted_at ? ' (excluída)' : ''}`,
            onRemove: () => onChange({ categoryId: '' }),
          },
        ]
      : []),
    ...(filters.paymentMethodId
      ? [
          {
            id: 'payment-method',
            label: `${paymentMethod?.name ?? 'Pagamento'}${paymentMethod?.deleted_at ? ' (excluído)' : ''}`,
            onRemove: () => onChange({ paymentMethodId: '' }),
          },
        ]
      : []),
    ...(filters.search
      ? [
          {
            id: 'search',
            label: `Busca: ${filters.search}`,
            onRemove: () => onChange({ search: '' }),
          },
        ]
      : []),
  ];
}
