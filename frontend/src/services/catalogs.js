import { request } from './httpClient.js';

const catalogEndpoints = Object.freeze({
  categories: '/categories',
  paymentMethods: '/payment-methods',
  incomeCategories: '/income-categories',
});

function endpoint(catalog) {
  const path = catalogEndpoints[catalog];
  if (!path) throw new Error(`Catálogo desconhecido: ${catalog}`);
  return path;
}

export const getCategories = (signal, includeDeleted = false) =>
  request(`/categories${includeDeleted ? '?include_deleted=true' : ''}`, { signal });
export const getPaymentMethods = (signal, includeDeleted = false) =>
  request(`/payment-methods${includeDeleted ? '?include_deleted=true' : ''}`, { signal });
export const getIncomeCategories = (signal, includeDeleted = false) =>
  request(`/income-categories${includeDeleted ? '?include_deleted=true' : ''}`, { signal });

export const createCatalogItem = (catalog, data) =>
  request(endpoint(catalog), { method: 'POST', body: data });
export const updateCatalogItem = (catalog, id, data) =>
  request(`${endpoint(catalog)}/${id}`, { method: 'PUT', body: data });
export const deleteCatalogItem = (catalog, id) =>
  request(`${endpoint(catalog)}/${id}`, { method: 'DELETE' });
