import { currentMonthISO, formatMonth } from '../../shared/format.js';
import { isValidMonth } from '../../shared/dates.js';

export function readHistoryFilters(search, defaultMonth = currentMonthISO()) {
  const params = new URLSearchParams(search);
  const month = params.get('month');
  const categoryId = params.get('category');
  const paymentMethodId = params.get('payment_method');
  const page = Number(params.get('page'));
  return {
    month: isValidMonth(month) ? month : defaultMonth,
    categoryId: /^\d+$/.test(categoryId ?? '') ? categoryId : '',
    paymentMethodId: /^\d+$/.test(paymentMethodId ?? '') ? paymentMethodId : '',
    search: (params.get('search') ?? '').trim(),
    page: Number.isInteger(page) && page > 0 ? page : 1,
    pageSize: 100,
  };
}

export function historyFilterPath(filters) {
  const params = new URLSearchParams();
  params.set('month', filters.month);
  if (filters.categoryId) params.set('category', filters.categoryId);
  if (filters.paymentMethodId) params.set('payment_method', filters.paymentMethodId);
  if (filters.search) params.set('search', filters.search);
  if (filters.page > 1) params.set('page', String(filters.page));
  return `/gastos?${params}`;
}

export function historyFilterChips(filters, categories, paymentMethods, defaultMonth, onChange) {
  const category = categories.find((item) => String(item.id) === filters.categoryId);
  const paymentMethod = paymentMethods.find((item) => String(item.id) === filters.paymentMethodId);
  return [
    ...(filters.month !== defaultMonth
      ? [
          {
            id: 'month',
            label: formatMonth(filters.month),
            onRemove: () => onChange({ month: defaultMonth }),
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
