import { useCallback } from 'react';
import { getRecentExpenses } from '../../services/expenses.js';
import { queryKeys } from '../queryKeys.js';
import { useApiQuery } from '../useApiQuery.js';

export function useMonthlyExpenses(userId, month) {
  const fetchExpenses = useCallback(
    async ({ signal }) => {
      const expenses = await getRecentExpenses(month, signal);
      return [...expenses].sort(
        (left, right) =>
          right.expense_date.localeCompare(left.expense_date) ||
          right.id - left.id ||
          left.installment_number - right.installment_number,
      );
    },
    [month],
  );
  return useApiQuery(queryKeys.monthlyExpenses(userId, month), fetchExpenses, {
    enabled: Boolean(userId),
  });
}
