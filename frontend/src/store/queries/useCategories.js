import { useCallback } from 'react';
import { getCategories } from '../../services/catalogs.js';
import { queryKeys } from '../queryKeys.js';
import { useApiQuery } from '../useApiQuery.js';

export function useCategories(userId, { includeDeleted = false } = {}) {
  const fetchCategories = useCallback(
    ({ signal }) => getCategories(signal, includeDeleted),
    [includeDeleted],
  );
  const query = useApiQuery(queryKeys.categories(userId, includeDeleted), fetchCategories, {
    staleTime: 30 * 60 * 1000,
    enabled: Boolean(userId),
  });
  return query;
}
