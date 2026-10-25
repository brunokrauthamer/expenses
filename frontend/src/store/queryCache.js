const entries = new Map();
const EMPTY_SNAPSHOT = {
  data: undefined,
  error: null,
  isLoading: false,
  isFetching: false,
};
const CACHE_GARBAGE_COLLECTION_TIME = 5 * 60 * 1000;

function serializeKey(key) {
  return JSON.stringify(key);
}

function getEntry(key) {
  const hash = serializeKey(key);
  if (!entries.has(hash)) {
    entries.set(hash, {
      hash,
      key,
      snapshot: EMPTY_SNAPSHOT,
      updatedAt: 0,
      listeners: new Set(),
      queryFn: null,
      staleTime: 0,
      promise: null,
      controller: null,
      requestVersion: 0,
      abortTimeout: null,
      garbageCollectionTimeout: null,
      disposed: false,
    });
  }
  return entries.get(hash);
}

function notify(entry) {
  entry.listeners.forEach((listener) => listener());
}

function isRetryable(error) {
  return (
    error?.name !== 'AbortError' &&
    (error?.status === undefined || error.status === 0 || error.status >= 500)
  );
}

function waitBeforeRetry(signal) {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      const error = new Error('A consulta foi cancelada.');
      error.name = 'AbortError';
      reject(error);
      return;
    }
    const handle = window.setTimeout(done, 350);

    function done() {
      signal.removeEventListener('abort', cancel);
      resolve();
    }

    function cancel() {
      window.clearTimeout(handle);
      signal.removeEventListener('abort', cancel);
      const error = new Error('A consulta foi cancelada.');
      error.name = 'AbortError';
      reject(error);
    }

    signal.addEventListener('abort', cancel, { once: true });
  });
}

async function fetchQuery(entry, queryFn) {
  if (entry.disposed) return undefined;
  if (entry.promise && !entry.controller?.signal.aborted)
    return entry.promise.catch(() => undefined);

  const version = ++entry.requestVersion;
  const controller = new AbortController();
  entry.controller = controller;
  entry.snapshot = {
    ...entry.snapshot,
    error: null,
    isLoading: entry.snapshot.data === undefined,
    isFetching: true,
  };
  notify(entry);

  const promise = (async () => {
    try {
      return await queryFn({ signal: controller.signal });
    } catch (firstError) {
      if (!isRetryable(firstError) || controller.signal.aborted) throw firstError;
      await waitBeforeRetry(controller.signal);
      return queryFn({ signal: controller.signal });
    }
  })();
  entry.promise = promise;

  try {
    const data = await promise;
    if (entry.requestVersion === version) {
      entry.updatedAt = Date.now();
      entry.snapshot = { data, error: null, isLoading: false, isFetching: false };
      notify(entry);
    }
    return data;
  } catch (error) {
    if (entry.requestVersion === version) {
      entry.snapshot = {
        ...entry.snapshot,
        error: error?.name === 'AbortError' ? null : error,
        isLoading: false,
        isFetching: false,
      };
      notify(entry);
    }
    return undefined;
  } finally {
    if (entry.requestVersion === version) {
      entry.promise = null;
      entry.controller = null;
      if (controller.signal.aborted && entry.listeners.size) {
        queueMicrotask(() => {
          if (entry.listeners.size && !entry.promise) fetchQuery(entry, entry.queryFn);
        });
      }
    }
  }
}

function subscribe(entry, listener) {
  if (entry.disposed) return () => {};
  entry.listeners.add(listener);
  if (entry.garbageCollectionTimeout !== null) {
    window.clearTimeout(entry.garbageCollectionTimeout);
    entry.garbageCollectionTimeout = null;
  }
  if (entry.abortTimeout !== null) {
    window.clearTimeout(entry.abortTimeout);
    entry.abortTimeout = null;
  }
  if (!entry.snapshot.data || Date.now() - entry.updatedAt >= entry.staleTime) {
    fetchQuery(entry, entry.queryFn);
  }

  return () => {
    entry.listeners.delete(listener);
    if (entry.disposed) return;
    if (!entry.listeners.size && entry.promise) {
      entry.abortTimeout = window.setTimeout(() => {
        entry.abortTimeout = null;
        if (!entry.listeners.size && entry.controller) entry.controller.abort();
      }, 80);
    }
    if (!entry.listeners.size) {
      entry.garbageCollectionTimeout = window.setTimeout(() => {
        entry.garbageCollectionTimeout = null;
        if (!entry.listeners.size && !entry.promise) entries.delete(entry.hash);
      }, CACHE_GARBAGE_COLLECTION_TIME);
    }
  };
}

export function subscribeToCachedQuery(key, queryFn, { staleTime = 2 * 60 * 1000 } = {}, listener) {
  const entry = getEntry(key);
  entry.queryFn = queryFn;
  entry.staleTime = staleTime;
  return subscribe(entry, listener);
}

export function getCachedQuerySnapshot(key) {
  return getEntry(key).snapshot;
}

export function refetchCachedQuery(key, queryFn) {
  const entry = getEntry(key);
  if (queryFn) entry.queryFn = queryFn;
  entry.updatedAt = 0;
  return fetchQuery(entry, entry.queryFn);
}

export function updateCachedQuery(key, updater) {
  const entry = getEntry(key);
  const previousData = entry.snapshot.data;
  const nextData = typeof updater === 'function' ? updater(previousData) : updater;
  if (nextData === undefined) return;

  entry.requestVersion += 1;
  entry.controller?.abort();
  entry.promise = null;
  entry.controller = null;
  entry.updatedAt = Date.now();
  entry.snapshot = { data: nextData, error: null, isLoading: false, isFetching: false };
  notify(entry);
}

function hasPrefix(key, prefix) {
  return (
    prefix.length <= key.length &&
    prefix.every((part, index) => serializeKey(part) === serializeKey(key[index]))
  );
}

export function invalidateCachedQueries(prefix) {
  for (const entry of entries.values()) {
    if (!hasPrefix(entry.key, prefix)) continue;
    entry.updatedAt = 0;
    if (entry.promise) {
      entry.requestVersion += 1;
      entry.controller?.abort();
      entry.promise = null;
      entry.controller = null;
      entry.snapshot = { ...entry.snapshot, isFetching: false, isLoading: false };
    }
    notify(entry);
    if (entry.listeners.size) fetchQuery(entry, entry.queryFn);
  }
}

export function clearQueryCache() {
  for (const entry of entries.values()) {
    entry.disposed = true;
    entry.requestVersion += 1;
    entry.controller?.abort();
    entry.controller = null;
    entry.promise = null;
    if (entry.abortTimeout !== null) window.clearTimeout(entry.abortTimeout);
    if (entry.garbageCollectionTimeout !== null)
      window.clearTimeout(entry.garbageCollectionTimeout);
    entry.abortTimeout = null;
    entry.garbageCollectionTimeout = null;
    entry.updatedAt = 0;
    entry.snapshot = EMPTY_SNAPSHOT;
    notify(entry);
  }
  entries.clear();
}

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    for (const entry of entries.values()) {
      if (entry.listeners.size && Date.now() - entry.updatedAt >= entry.staleTime) {
        fetchQuery(entry, entry.queryFn);
      }
    }
  });
}
