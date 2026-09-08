"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface AsyncState<T> {
  data: T | null;
  error: unknown;
  loading: boolean;
  reload: () => void;
}

/**
 * Minimal data-fetching hook: runs `fn` on mount and whenever `deps` change,
 * ignores stale resolutions, and exposes a manual `reload`.
 */
export function useAsync<T>(
  fn: () => Promise<T>,
  deps: unknown[]
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);
  const latest = useRef(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  useEffect(() => {
    const run = ++latest.current;
    setLoading(true);
    setError(null);
    fn()
      .then((res) => {
        if (run === latest.current) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (run === latest.current) {
          setError(err);
          setData(null);
          setLoading(false);
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  return { data, error, loading, reload };
}
