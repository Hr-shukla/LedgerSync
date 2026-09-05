import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../lib/api';

interface UseApiDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

// Small fetch-on-mount-and-on-deps-change hook, matching this codebase's
// existing plain-React style (no react-query or similar). `fetcher` is
// re-invoked whenever `deps` changes, or when `reload()` is called.
export function useApiData<T>(fetcher: () => Promise<T>, deps: React.DependencyList): UseApiDataResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetcher()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Something went wrong talking to the backend.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, reloadToken]);

  const reload = useCallback(() => setReloadToken((k) => k + 1), []);

  return { data, loading, error, reload };
}
