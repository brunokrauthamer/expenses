import { request } from './httpClient.js';

export function getIncomeEntries(filters = {}, signal) {
  const params = new URLSearchParams();
  if (filters.startMonth) params.set('start_month', filters.startMonth);
  if (filters.endMonth) params.set('end_month', filters.endMonth);
  if (filters.incomeCategoryId) params.set('income_category_id', filters.incomeCategoryId);
  if (filters.expenseCategoryId) params.set('expense_category_id', filters.expenseCategoryId);
  if (filters.search) params.set('search', filters.search);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.pageSize) params.set('page_size', String(filters.pageSize));
  return request(`/income-entries?${params}`, { signal });
}

export const createIncomeEntry = (entry) =>
  request('/income-entries', { method: 'POST', body: entry });
export const updateIncomeEntry = (entryId, entry) =>
  request(`/income-entries/${entryId}`, { method: 'PUT', body: entry });
export const deleteIncomeEntry = (entryId) =>
  request(`/income-entries/${entryId}`, { method: 'DELETE' });
