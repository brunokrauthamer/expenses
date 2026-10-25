import { request } from './httpClient.js';

export function getRecentExpenses(month, signal) {
  return request(`/expenses/month?month=${month}`, { signal });
}

export function getExpenseHistory(filters, signal) {
  const params = new URLSearchParams();
  params.set('month', filters.month);
  params.set('page', String(filters.page ?? 1));
  params.set('page_size', String(filters.pageSize ?? 100));
  if (filters.categoryId) params.set('category_id', filters.categoryId);
  if (filters.paymentMethodId) params.set('payment_method_id', filters.paymentMethodId);
  if (filters.search) params.set('search', filters.search);
  return request(`/expenses/history?${params}`, { signal });
}

export function getExpenses(filters, signal) {
  const params = new URLSearchParams();
  params.set('month', filters.month);
  params.set('page', String(filters.page ?? 1));
  params.set('page_size', String(filters.pageSize ?? 100));
  if (filters.categoryId) params.set('category_id', filters.categoryId);
  if (filters.paymentMethodId) params.set('payment_method_id', filters.paymentMethodId);
  if (filters.search) params.set('search', filters.search);
  return request(`/expenses?${params}`, { signal });
}

export function getSummary(filters, signal) {
  const params = new URLSearchParams();
  params.set('start_month', filters.startMonth);
  params.set('end_month', filters.endMonth);
  if (filters.categoryId) params.set('category_id', filters.categoryId);
  if (filters.paymentMethodId) params.set('payment_method_id', filters.paymentMethodId);
  if (filters.search) params.set('search', filters.search);
  return request(`/expenses/summary?${params}`, { signal });
}

export const createExpense = (expense) => request('/expenses', { method: 'POST', body: expense });
export const updateExpense = (expenseId, expense) =>
  request(`/expenses/${expenseId}`, { method: 'PUT', body: expense });
export const deleteExpense = (expenseId) => request(`/expenses/${expenseId}`, { method: 'DELETE' });
