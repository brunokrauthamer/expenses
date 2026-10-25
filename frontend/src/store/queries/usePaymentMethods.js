import { useCallback } from 'react';
import { getPaymentMethods } from '../../services/catalogs.js';
import { queryKeys } from '../queryKeys.js';
import { useApiQuery } from '../useApiQuery.js';

export function usePaymentMethods(userId, { includeDeleted = false } = {}) {
  const fetchPaymentMethods = useCallback(
    ({ signal }) => getPaymentMethods(signal, includeDeleted),
    [includeDeleted],
  );
  const query = useApiQuery(queryKeys.paymentMethods(userId, includeDeleted), fetchPaymentMethods, {
    staleTime: 30 * 60 * 1000,
    enabled: Boolean(userId),
  });
  return query;
}
