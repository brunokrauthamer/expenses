import assert from 'node:assert/strict';
import test from 'node:test';
import { buildExpensePayload, expenseFormFromRecord, newExpenseForm } from './form.js';

const validForm = {
  description: '  Mercado  ',
  amount: 'R$ 12,34',
  expenseDate: '2026-10-20',
  categoryId: '3',
  paymentMethodId: '2',
  paymentType: 'one_time',
  installmentCount: '2',
  amountType: 'installment',
  firstInstallmentDate: '2026-10-20',
};

test('builds a one time expense payload with normalized fields', () => {
  assert.deepEqual(buildExpensePayload(validForm), {
    payload: {
      description: 'Mercado',
      amount: '12.34',
      expense_date: '2026-10-20',
      category_id: 3,
      payment_method_id: 2,
      payment_type: 'one_time',
      amount_type: 'total',
      installment_count: 1,
    },
  });
});

test('validates installment boundaries and dates before building a payload', () => {
  assert.equal(
    buildExpensePayload({ ...validForm, paymentType: 'installments', installmentCount: '1' }).field,
    'installmentCount',
  );
  assert.equal(
    buildExpensePayload({ ...validForm, paymentType: 'installments', installmentCount: '1201' })
      .field,
    'installmentCount',
  );
  assert.equal(
    buildExpensePayload({
      ...validForm,
      paymentType: 'installments',
      firstInstallmentDate: '2026-10-19',
    }).field,
    'firstInstallmentDate',
  );
  const result = buildExpensePayload({
    ...validForm,
    paymentType: 'installments',
    installmentCount: '3',
  });
  assert.equal(result.payload.amount_type, 'installment');
  assert.equal(result.payload.installment_count, 3);
  assert.equal(result.payload.first_installment_date, '2026-10-20');
});

test('returns field errors for missing or invalid values', () => {
  assert.equal(buildExpensePayload({ ...validForm, description: ' ' }).field, 'description');
  assert.equal(buildExpensePayload({ ...validForm, amount: '0,00' }).field, 'amount');
  assert.equal(buildExpensePayload({ ...validForm, categoryId: '' }).field, 'categoryId');
  assert.equal(buildExpensePayload({ ...validForm, paymentMethodId: '' }).field, 'paymentMethodId');
});

test('initializes and restores forms without changing date or installment fields', () => {
  assert.equal(newExpenseForm('2026-10-24').expenseDate, '2026-10-24');
  assert.equal(newExpenseForm('2026-10-24').firstInstallmentDate, '2026-10-24');
  const form = expenseFormFromRecord({
    description: 'Compra',
    total_amount: '75.40',
    expense_date: '2026-10-02',
    category_id: 5,
    payment_method_id: 1,
    payment_type: 'installments',
    installment_count: 3,
    first_installment_date: '2026-11-02',
  });
  assert.equal(form.amount, '75,40');
  assert.equal(form.installmentCount, '3');
  assert.equal(form.firstInstallmentDate, '2026-11-02');
});
