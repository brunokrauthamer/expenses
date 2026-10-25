import {
  createCatalogItem,
  deleteCatalogItem,
  updateCatalogItem,
} from '../../services/catalogs.js';
import { invalidateCachedQueries } from '../queryCache.js';
import { lookupQueryPrefix, queryKeys } from '../queryKeys.js';

function invalidateCatalogData(userId, catalog) {
  invalidateCachedQueries(lookupQueryPrefix(userId, catalog));
  invalidateCachedQueries(queryKeys.expenses(userId));
  invalidateCachedQueries(queryKeys.incomeEntries(userId));
}

export async function saveCatalogItem(userId, catalog, itemId, payload) {
  const result = itemId
    ? await updateCatalogItem(catalog, itemId, payload)
    : await createCatalogItem(catalog, payload);
  invalidateCatalogData(userId, catalog);
  return result;
}

export async function removeCatalogItem(userId, catalog, itemId) {
  await deleteCatalogItem(catalog, itemId);
  invalidateCatalogData(userId, catalog);
}
