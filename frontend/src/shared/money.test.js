import assert from 'node:assert/strict';
import test from 'node:test';
import {
  centsToDecimal,
  decimalToCents,
  normalizeMoneyAmount,
  sumMovementAmounts,
} from './money.js';

test('normalizes Brazilian and decimal money input without losing cents', () => {
  assert.equal(normalizeMoneyAmount('R$ 1.234,50'), '1234.50');
  assert.equal(normalizeMoneyAmount('1234.5'), '1234.50');
  assert.equal(normalizeMoneyAmount('0,01'), '0.01');
  assert.equal(normalizeMoneyAmount('0,00'), null);
  assert.equal(normalizeMoneyAmount('1,234'), null);
});

test('converts decimals to signed integer cents and back', () => {
  assert.equal(decimalToCents('12.34'), 1234n);
  assert.equal(decimalToCents('-0.50'), -50n);
  assert.equal(decimalToCents('0'), 0n);
  assert.equal(decimalToCents('1.234'), null);
  assert.equal(centsToDecimal(-50n), '-0.50');
  assert.equal(centsToDecimal(0n), '0.00');
});

test('sums charges and reimbursements exactly, including negative cents', () => {
  assert.equal(sumMovementAmounts([{ amount_due: '2.00' }]), '2.00');
  assert.equal(sumMovementAmounts([{ kind: 'reimbursement', amount: '1.50' }]), '-1.50');
  assert.equal(sumMovementAmounts([{ kind: 'reimbursement', amount: '0.50' }]), '-0.50');
  assert.equal(sumMovementAmounts([{ kind: 'reimbursement', amount: '2.00' }]), '-2.00');
  assert.equal(
    sumMovementAmounts([
      { amount_due: '10.25' },
      { kind: 'reimbursement', amount: '3.10' },
      { amount_due: '0.05' },
    ]),
    '7.20',
  );
});
