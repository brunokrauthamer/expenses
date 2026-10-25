import assert from 'node:assert/strict';
import test from 'node:test';
import { safeAuthDestination } from './routes.js';

const origin = 'https://expenses.example';

test('allows internal application destinations, including settings', () => {
  assert.equal(safeAuthDestination('/despesas?month=2026-10', origin), '/despesas?month=2026-10');
  assert.equal(
    safeAuthDestination('https://expenses.example/configuracoes', origin),
    '/configuracoes',
  );
});

test('rejects external, unlisted, and malformed destinations', () => {
  assert.equal(safeAuthDestination('https://other.example/despesas', origin), '/despesas');
  assert.equal(safeAuthDestination('//other.example', origin), '/despesas');
  assert.equal(safeAuthDestination('/auth/complete', origin), '/despesas');
  assert.equal(safeAuthDestination('http://[', origin), '/despesas');
});
