import assert from 'node:assert/strict';
import test from 'node:test';
import { buildIncomePayload } from './form.js';

const values = {
  description: '  Reembolso  ',
  amount: '15,30',
  receivedDate: '2026-10-12',
  incomeCategoryId: '8',
  expenseCategoryId: '4',
};

test('includes the linked expense category only for reimbursement categories', () => {
  assert.deepEqual(
    buildIncomePayload({ ...values, selectedCategory: { requires_expense_category: true } }),
    {
      payload: {
        description: 'Reembolso',
        amount: '15.30',
        received_date: '2026-10-12',
        income_category_id: 8,
        expense_category_id: 4,
      },
    },
  );
  assert.deepEqual(
    buildIncomePayload({ ...values, selectedCategory: { requires_expense_category: false } }),
    {
      payload: {
        description: 'Reembolso',
        amount: '15.30',
        received_date: '2026-10-12',
        income_category_id: 8,
      },
    },
  );
});

test('rejects zero and malformed amounts', () => {
  assert.equal(
    buildIncomePayload({ ...values, amount: '0,00' }).error,
    'Informe um valor maior que zero.',
  );
  assert.equal(
    buildIncomePayload({ ...values, amount: '1,234' }).error,
    'Informe um valor maior que zero.',
  );
});
