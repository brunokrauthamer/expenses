import assert from 'node:assert/strict';
import test from 'node:test';
import { defaultReportFilters, reportFilterPath, readReportFilters } from './filters.js';

test('reads valid report filters and falls back for invalid month ranges', () => {
  assert.deepEqual(
    readReportFilters(
      '?start_month=2026-01&end_month=2026-06&category=5&payment_method=2&search=%20mercado%20',
      '2026-10',
    ),
    {
      startMonth: '2026-01',
      endMonth: '2026-06',
      categoryId: '5',
      paymentMethodId: '2',
      search: 'mercado',
    },
  );
  assert.deepEqual(
    readReportFilters('?start_month=2026-10&end_month=2026-01', '2026-10'),
    defaultReportFilters('2026-10'),
  );
  assert.deepEqual(
    readReportFilters('?start_month=2010-01&end_month=2026-10', '2026-10'),
    defaultReportFilters('2026-10'),
  );
});

test('serializes report filters for the URL without losing search text', () => {
  assert.equal(
    reportFilterPath({
      startMonth: '2026-01',
      endMonth: '2026-03',
      categoryId: '',
      paymentMethodId: '2',
      search: 'café',
    }),
    '/consolidado?start_month=2026-01&end_month=2026-03&payment_method=2&search=caf%C3%A9',
  );
});
