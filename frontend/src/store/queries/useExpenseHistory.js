import { useCallback, useMemo } from 'react';
import { getExpenseHistory } from '../../services/expenses.js';
import { queryKeys } from '../queryKeys.js';
import { useApiQuery } from '../useApiQuery.js';

export function useExpenseHistory(userId, filters) {
  const filtersKey = JSON.stringify(filters);
  const stableFilters = useMemo(() => JSON.parse(filtersKey), [filtersKey]);
  const fetchHistory = useCallback(
    ({ signal }) => getExpenseHistory(stableFilters, signal),
    [stableFilters],
  );
  return useApiQuery(queryKeys.expenseHistory(userId, stableFilters), fetchHistory, {
    enabled: Boolean(userId),
  });
}
