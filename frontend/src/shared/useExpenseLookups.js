import { useCallback } from 'react';
import { api } from '../services/api.js';
import { useApiQuery } from './queryCache.js';

export function useExpenseLookups() {
  const fetchCategories = useCallback(({ signal }) => api.getCategories(signal), []);
  const fetchPaymentMethods = useCallback(({ signal }) => api.getPaymentMethods(signal), []);
  const categoriesQuery = useApiQuery(
    ['lookups', 'categories'],
    fetchCategories,
    { staleTime: 30 * 60 * 1000 },
  );
  const paymentMethodsQuery = useApiQuery(
    ['lookups', 'payment-methods'],
    fetchPaymentMethods,
    { staleTime: 30 * 60 * 1000 },
  );

  return {
    categoriesQuery,
    paymentMethodsQuery,
    categories: categoriesQuery.data ?? [],
    paymentMethods: paymentMethodsQuery.data ?? [],
  };
}
