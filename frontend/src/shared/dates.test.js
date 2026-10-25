import assert from 'node:assert/strict';
import test from 'node:test';
import { isValidMonth } from './dates.js';

test('accepts calendar months in the URL format', () => {
  assert.equal(isValidMonth('2026-01'), true);
  assert.equal(isValidMonth('2026-12'), true);
  assert.equal(isValidMonth('0000-01'), false);
  assert.equal(isValidMonth('2026-00'), false);
  assert.equal(isValidMonth('2026-13'), false);
  assert.equal(isValidMonth('26-01'), false);
});
