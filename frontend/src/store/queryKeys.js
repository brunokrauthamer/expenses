const lookupNames = Object.freeze({
  categories: 'categories',
  paymentMethods: 'payment-methods',
  incomeCategories: 'income-categories',
});

export const queryKeys = {
  categories: (userId, includeDeleted = false) => [
    userId,
    'lookups',
    lookupNames.categories,
    includeDeleted ? 'all' : 'active',
  ],
  paymentMethods: (userId, includeDeleted = false) => [
    userId,
    'lookups',
    lookupNames.paymentMethods,
    includeDeleted ? 'all' : 'active',
  ],
  incomeCategories: (userId, includeDeleted = false) => [
    userId,
    'lookups',
    lookupNames.incomeCategories,
    includeDeleted ? 'all' : 'active',
  ],
  expenses: (userId) => [userId, 'expenses'],
  monthlyExpenses: (userId, month) => [userId, 'expenses', 'month', month],
  expenseHistory: (userId, filters) => [userId, 'expenses', 'history', filters],
  expenseSummary: (userId, filters) => [userId, 'expenses', 'summary', filters],
  incomeEntries: (userId) => [userId, 'income-entries'],
  monthlyIncomeEntries: (userId, month) => [userId, 'income-entries', 'month', month],
};

export function lookupQueryPrefix(userId, catalog) {
  const name = lookupNames[catalog];
  if (!name) throw new Error(`Catálogo desconhecido: ${catalog}`);
  return [userId, 'lookups', name];
}
