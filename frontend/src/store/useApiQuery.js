import { useCallback, useMemo, useSyncExternalStore } from 'react';
import {
  getCachedQuerySnapshot,
  subscribeToCachedQuery,
  refetchCachedQuery,
} from './queryCache.js';

export function useApiQuery(key, queryFn, { staleTime = 2 * 60 * 1000, enabled = true } = {}) {
  const hash = JSON.stringify(key);
  const stableKey = useMemo(() => JSON.parse(hash), [hash]);
  const connect = useCallback(
    (listener) =>
      enabled ? subscribeToCachedQuery(stableKey, queryFn, { staleTime }, listener) : () => {},
    [enabled, stableKey, queryFn, staleTime],
  );
  const read = useCallback(() => getCachedQuerySnapshot(stableKey), [stableKey]);
  const snapshot = useSyncExternalStore(connect, read, read);
  const refetch = useCallback(() => {
    return refetchCachedQuery(stableKey, queryFn);
  }, [stableKey, queryFn]);
  return { ...snapshot, refetch };
}
