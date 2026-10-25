import {
  createIncomeEntry,
  deleteIncomeEntry,
  updateIncomeEntry,
} from '../../services/incomeEntries.js';
import { invalidateCachedQueries } from '../queryCache.js';
import { queryKeys } from '../queryKeys.js';

function invalidateIncomeData(userId) {
  invalidateCachedQueries(queryKeys.incomeEntries(userId));
  invalidateCachedQueries(queryKeys.expenses(userId));
}

export async function saveIncomeEntry(userId, entryId, payload) {
  const result = entryId
    ? await updateIncomeEntry(entryId, payload)
    : await createIncomeEntry(payload);
  invalidateIncomeData(userId);
  return result;
}

export async function removeIncomeEntry(userId, entryId) {
  await deleteIncomeEntry(entryId);
  invalidateIncomeData(userId);
}
