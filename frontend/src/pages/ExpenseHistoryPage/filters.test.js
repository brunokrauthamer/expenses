import assert from 'node:assert/strict';
import test from 'node:test';
import { historyFilterPath, readHistoryFilters } from './filters.js';

test('reads valid history filters and applies safe defaults', () => {
  assert.deepEqual(
    readHistoryFilters(
      '?month=2026-08&category=12&payment_method=4&search=%20caf%C3%A9%20&page=3',
      '2026-10',
    ),
    {
      month: '2026-08',
      categoryId: '12',
      paymentMethodId: '4',
      search: 'café',
      page: 3,
      pageSize: 100,
    },
  );
  assert.deepEqual(readHistoryFilters('?month=2026-13&category=x&page=-1', '2026-10'), {
    month: '2026-10',
    categoryId: '',
    paymentMethodId: '',
    search: '',
    page: 1,
    pageSize: 100,
  });
});

test('serializes only applied history filters and pagination', () => {
  assert.equal(
    historyFilterPath({
      month: '2026-08',
      categoryId: '12',
      paymentMethodId: '',
      search: 'café',
      page: 2,
    }),
    '/gastos?month=2026-08&category=12&search=caf%C3%A9&page=2',
  );
});
