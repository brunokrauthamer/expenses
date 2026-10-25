import { useCallback } from 'react';
import { getIncomeCategories } from '../../services/catalogs.js';
import { queryKeys } from '../queryKeys.js';
import { useApiQuery } from '../useApiQuery.js';

export function useIncomeCategories(userId, { includeDeleted = false } = {}) {
  const fetchIncomeCategories = useCallback(
    ({ signal }) => getIncomeCategories(signal, includeDeleted),
    [includeDeleted],
  );
  const query = useApiQuery(
    queryKeys.incomeCategories(userId, includeDeleted),
    fetchIncomeCategories,
    {
      staleTime: 30 * 60 * 1000,
      enabled: Boolean(userId),
    },
  );
  return query;
}
