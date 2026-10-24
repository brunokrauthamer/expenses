import { useCallback } from 'react';
import { api } from '../services/api.js';
import { useApiQuery } from './queryCache.js';

export function useExpenseLookups(userId) {
  const fetchCategories = useCallback(({ signal }) => api.getCategories(signal), []);
  const fetchPaymentMethods = useCallback(({ signal }) => api.getPaymentMethods(signal), []);
  const fetchIncomeCategories = useCallback(({ signal }) => api.getIncomeCategories(signal), []);
  const fetchCategoryReferences = useCallback(({ signal }) => api.getCategories(signal, true), []);
  const fetchPaymentMethodReferences = useCallback(({ signal }) => api.getPaymentMethods(signal, true), []);
  const fetchIncomeCategoryReferences = useCallback(({ signal }) => api.getIncomeCategories(signal, true), []);
  const categoriesQuery = useApiQuery(
    [userId, 'lookups', 'categories', 'active'],
    fetchCategories,
    { staleTime: 30 * 60 * 1000, enabled: Boolean(userId) },
  );
  const paymentMethodsQuery = useApiQuery(
    [userId, 'lookups', 'payment-methods', 'active'],
    fetchPaymentMethods,
    { staleTime: 30 * 60 * 1000, enabled: Boolean(userId) },
  );
  const incomeCategoriesQuery = useApiQuery(
    [userId, 'lookups', 'income-categories', 'active'],
    fetchIncomeCategories,
    { staleTime: 30 * 60 * 1000, enabled: Boolean(userId) },
  );
  const categoryReferencesQuery = useApiQuery(
    [userId, 'lookups', 'categories', 'all'],
    fetchCategoryReferences,
    { staleTime: 30 * 60 * 1000, enabled: Boolean(userId) },
  );
  const paymentMethodReferencesQuery = useApiQuery(
    [userId, 'lookups', 'payment-methods', 'all'],
    fetchPaymentMethodReferences,
    { staleTime: 30 * 60 * 1000, enabled: Boolean(userId) },
  );
  const incomeCategoryReferencesQuery = useApiQuery(
    [userId, 'lookups', 'income-categories', 'all'],
    fetchIncomeCategoryReferences,
    { staleTime: 30 * 60 * 1000, enabled: Boolean(userId) },
  );

  return {
    categoriesQuery,
    paymentMethodsQuery,
    incomeCategoriesQuery,
    categoryReferencesQuery,
    paymentMethodReferencesQuery,
    incomeCategoryReferencesQuery,
    categories: categoriesQuery.data ?? [],
    paymentMethods: paymentMethodsQuery.data ?? [],
    incomeCategories: incomeCategoriesQuery.data ?? [],
    categoryReferences: categoryReferencesQuery.data ?? [],
    paymentMethodReferences: paymentMethodReferencesQuery.data ?? [],
    incomeCategoryReferences: incomeCategoryReferencesQuery.data ?? [],
  };
}
