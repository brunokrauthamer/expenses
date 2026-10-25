import { createExpense, deleteExpense, updateExpense } from '../../services/expenses.js';
import { invalidateCachedQueries } from '../queryCache.js';
import { queryKeys } from '../queryKeys.js';

export async function saveExpense(userId, expenseId, payload) {
  const result = expenseId ? await updateExpense(expenseId, payload) : await createExpense(payload);
  invalidateCachedQueries(queryKeys.expenses(userId));
  return result;
}

export async function removeExpense(userId, expenseId) {
  await deleteExpense(expenseId);
  invalidateCachedQueries(queryKeys.expenses(userId));
}
