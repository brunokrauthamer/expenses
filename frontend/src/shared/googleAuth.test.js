import assert from 'node:assert/strict';
import test from 'node:test';
import { isTrustedGoogleAuthMessage } from './googleAuth.js';

const origin = 'https://expenses.example';
const popup = {};
const requestId = 'request-123';
const validEvent = {
  origin,
  source: popup,
  data: { type: 'expenses:google-auth', requestId, success: true },
};

test('accepts only a message from the active popup and matching request', () => {
  assert.equal(isTrustedGoogleAuthMessage(validEvent, { origin, popup, requestId }), true);
  assert.equal(
    isTrustedGoogleAuthMessage(
      { ...validEvent, origin: 'https://attacker.example' },
      { origin, popup, requestId },
    ),
    false,
  );
  assert.equal(
    isTrustedGoogleAuthMessage({ ...validEvent, source: {} }, { origin, popup, requestId }),
    false,
  );
  assert.equal(
    isTrustedGoogleAuthMessage(
      { ...validEvent, data: { ...validEvent.data, requestId: 'stale' } },
      { origin, popup, requestId },
    ),
    false,
  );
  assert.equal(
    isTrustedGoogleAuthMessage(
      { ...validEvent, data: { ...validEvent.data, success: 'yes' } },
      { origin, popup, requestId },
    ),
    false,
  );
});
