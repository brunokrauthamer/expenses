import { useCallback, useSyncExternalStore } from 'react';

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
    });
  }
  return entries.get(hash);
}

function notify(entry) {
  entry.listeners.forEach((listener) => listener());
}

function isRetryable(error) {
  return error?.name !== 'AbortError' && (
    error?.status === undefined || error.status === 0 || error.status >= 500
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
  // A promise backed by an aborted controller cannot satisfy a new subscriber.
  // Do not deduplicate against it; start a fresh request instead.
  if (entry.promise && !entry.controller?.signal.aborted) return entry.promise;

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
      // React StrictMode and fast route changes can unsubscribe long enough for
      // the deferred abort to fire, then subscribe again while that request is
      // still settling. If anyone is waiting now, recover automatically.
      if (controller.signal.aborted && entry.listeners.size) {
        queueMicrotask(() => {
          if (entry.listeners.size && !entry.promise) fetchQuery(entry, entry.queryFn);
        });
      }
    }
  }
}

function subscribe(entry, listener) {
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

export function useApiQuery(key, queryFn, { staleTime = 2 * 60 * 1000, enabled = true } = {}) {
  const entry = getEntry(key);
  entry.queryFn = queryFn;
  entry.staleTime = staleTime;

  const connect = useCallback(
    (listener) => enabled ? subscribe(entry, listener) : () => {},
    [enabled, entry],
  );
  const read = useCallback(() => entry.snapshot, [entry]);
  const snapshot = useSyncExternalStore(connect, read, read);
  const refetch = useCallback(() => fetchQuery(entry, queryFn), [entry, queryFn]);
  return { ...snapshot, refetch };
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
  return prefix.length <= key.length && prefix.every((part, index) => serializeKey(part) === serializeKey(key[index]));
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

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    for (const entry of entries.values()) {
      if (entry.listeners.size && Date.now() - entry.updatedAt >= entry.staleTime) {
        fetchQuery(entry, entry.queryFn);
      }
    }
  });
}

export function getQueryErrorMessage(error) {
  if (!error) return 'Não foi possível carregar os dados.';
  if (error.status === 404) return 'O endereço da API não foi encontrado. Verifique se o backend está em execução.';
  if (error.status >= 500) return 'A API encontrou um problema. Tente novamente em alguns instantes.';
  return error.message || 'Não foi possível carregar os dados.';
}
