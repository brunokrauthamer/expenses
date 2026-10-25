import assert from 'node:assert/strict';
import test from 'node:test';

const activeTimers = new Set();
globalThis.window = {
  addEventListener() {},
  clearTimeout(handle) {
    activeTimers.delete(handle);
    clearTimeout(handle);
  },
  setTimeout(callback, delay) {
    const handle = setTimeout(() => {
      activeTimers.delete(handle);
      callback();
    }, delay);
    activeTimers.add(handle);
    return handle;
  },
};

const {
  clearQueryCache,
  getCachedQuerySnapshot,
  subscribeToCachedQuery,
} = await import('../src/store/queryCache.js');

test.afterEach(() => {
  clearQueryCache();
  const remainingTimers = activeTimers.size;
  for (const handle of activeTimers) clearTimeout(handle);
  activeTimers.clear();
  assert.equal(remainingTimers, 0, 'logout must not leave timers attached to old account queries');
});

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

test('a response from the previous account cannot repopulate a cleared cache', async () => {
  clearQueryCache();
  const previousAccount = deferred();
  const currentAccount = deferred();
  let previousNotifications = 0;
  let currentNotifications = 0;

  const unsubscribePrevious = subscribeToCachedQuery(
    ['expenses', 'account-a'],
    () => previousAccount.promise,
    { staleTime: 60_000 },
    () => { previousNotifications += 1; },
  );

  clearQueryCache();
  const previousNotificationCount = previousNotifications;

  const unsubscribeCurrent = subscribeToCachedQuery(
    ['expenses', 'account-b'],
    () => currentAccount.promise,
    { staleTime: 60_000 },
    () => { currentNotifications += 1; },
  );

  currentAccount.resolve([{ id: 'b-private-record' }]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(getCachedQuerySnapshot(['expenses', 'account-b']).data, [{ id: 'b-private-record' }]);

  const currentSnapshot = getCachedQuerySnapshot(['expenses', 'account-b']);
  const currentNotificationCount = currentNotifications;
  previousAccount.resolve([{ id: 'a-private-record' }]);
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(getCachedQuerySnapshot(['expenses', 'account-b']), currentSnapshot);
  assert.equal(getCachedQuerySnapshot(['expenses', 'account-a']).data, undefined);
  assert.equal(currentNotifications, currentNotificationCount);
  assert.equal(previousNotifications, previousNotificationCount);

  unsubscribePrevious();
  unsubscribeCurrent();
  clearQueryCache();
});

test('clearing an account aborts its requests and detaches later unsubscriptions', () => {
  let signal;
  const unsubscribe = subscribeToCachedQuery(['expenses', 'account-a'], (request) => {
    signal = request.signal;
    return new Promise(() => {});
  }, {}, () => {});

  assert.equal(signal.aborted, false);
  clearQueryCache();
  assert.equal(signal.aborted, true);
  unsubscribe();
  assert.equal(activeTimers.size, 0);
  assert.equal(getCachedQuerySnapshot(['expenses', 'account-a']).isLoading, false);
});

test('an old subscription cannot affect a new session with the same account key', async () => {
  const oldRequest = deferred();
  const unsubscribeOld = subscribeToCachedQuery(['categories', 'account-a', 'active'], () => oldRequest.promise, {}, () => {});
  clearQueryCache();
  const unsubscribeNew = subscribeToCachedQuery(['categories', 'account-a', 'active'], async () => ['new session'], {}, () => {});
  await new Promise((resolve) => setImmediate(resolve));
  unsubscribeOld();
  oldRequest.resolve(['old session']);
  await new Promise((resolve) => setImmediate(resolve));
  assert.deepEqual(getCachedQuerySnapshot(['categories', 'account-a', 'active']).data, ['new session']);
  assert.equal(activeTimers.size, 0);
  unsubscribeNew();
});

test('active and historical catalogs use independent cached results', async () => {
  let calls = 0;
  const unsubscribeActive = subscribeToCachedQuery(['categories', 'account-a', false], async () => {
    calls += 1;
    return [{ id: 1 }];
  }, {}, () => {});
  const unsubscribeHistorical = subscribeToCachedQuery(['categories', 'account-a', true], async () => {
    calls += 1;
    return [{ id: 1 }, { id: 2, deleted_at: '2026-10-24' }];
  }, {}, () => {});
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(calls, 2);
  assert.equal(getCachedQuerySnapshot(['categories', 'account-a', false]).data.length, 1);
  assert.equal(getCachedQuerySnapshot(['categories', 'account-a', true]).data.length, 2);
  unsubscribeActive();
  unsubscribeHistorical();
});

test('deduplicated failures stay in the snapshot without unhandled rejections', async () => {
  let calls = 0;
  const error = Object.assign(new Error('invalid request'), { status: 422 });
  const query = async () => { calls += 1; throw error; };
  const unsubscribeFirst = subscribeToCachedQuery(['expenses', 'account-a'], query, {}, () => {});
  const unsubscribeSecond = subscribeToCachedQuery(['expenses', 'account-a'], query, {}, () => {});
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(calls, 1);
  assert.equal(getCachedQuerySnapshot(['expenses', 'account-a']).error, error);
  assert.equal(getCachedQuerySnapshot(['expenses', 'account-a']).isFetching, false);
  unsubscribeFirst();
  unsubscribeSecond();
});
