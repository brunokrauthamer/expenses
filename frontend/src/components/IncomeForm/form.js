import { normalizeMoneyAmount } from '../../shared/money.js';

export function buildIncomePayload({
  description,
  amount,
  receivedDate,
  incomeCategoryId,
  expenseCategoryId,
  selectedCategory,
}) {
  const normalizedAmount = normalizeMoneyAmount(amount);
  if (!normalizedAmount) return { error: 'Informe um valor maior que zero.' };
  return {
    payload: {
      description: description.trim(),
      amount: normalizedAmount,
      received_date: receivedDate,
      income_category_id: Number(incomeCategoryId),
      ...(selectedCategory?.requires_expense_category
        ? { expense_category_id: Number(expenseCategoryId) }
        : {}),
    },
  };
}
