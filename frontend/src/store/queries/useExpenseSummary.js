import { useCallback, useMemo } from 'react';
import { getSummary } from '../../services/expenses.js';
import { queryKeys } from '../queryKeys.js';
import { useApiQuery } from '../useApiQuery.js';

export function useExpenseSummary(userId, filters, { enabled = true } = {}) {
  const filtersKey = JSON.stringify(filters);
  const stableFilters = useMemo(() => JSON.parse(filtersKey), [filtersKey]);
  const fetchSummary = useCallback(
    ({ signal }) => getSummary(stableFilters, signal),
    [stableFilters],
  );
  return useApiQuery(queryKeys.expenseSummary(userId, stableFilters), fetchSummary, {
    enabled: enabled && Boolean(userId),
  });
}
