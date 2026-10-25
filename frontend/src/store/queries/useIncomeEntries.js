import { useCallback, useMemo } from 'react';
import { getIncomeEntries } from '../../services/incomeEntries.js';
import { queryKeys } from '../queryKeys.js';
import { useApiQuery } from '../useApiQuery.js';

export function useIncomeEntries(userId, filters) {
  const filtersKey = JSON.stringify(filters);
  const stableFilters = useMemo(() => JSON.parse(filtersKey), [filtersKey]);
  const fetchEntries = useCallback(
    ({ signal }) => getIncomeEntries(stableFilters, signal),
    [stableFilters],
  );
  return useApiQuery(
    [...queryKeys.incomeEntries(userId), ...Object.values(stableFilters)],
    fetchEntries,
    { enabled: Boolean(userId) },
  );
}
