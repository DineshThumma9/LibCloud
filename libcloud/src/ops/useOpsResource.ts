import { useEffect, useEffectEvent, useState } from "react";
import { describeError } from "./api";

type Snapshot<T> = {
  key: string;
  version: number;
  data: T | null;
  error: string | null;
};

type Resource<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
};

/**
 * Runs a loader whenever `key` changes or reload is requested. Keeping the
 * loader in an effect event means callers do not have to memoize their request
 * closures, and key changes drop stale data instead of showing it as fresh.
 */
export function useOpsResource<T>(key: string, load: () => Promise<T>): Resource<T> {
  const [snapshot, setSnapshot] = useState<Snapshot<T>>({
    key: "",
    version: -1,
    data: null,
    error: null,
  });
  const [version, setVersion] = useState(0);
  const loadEvent = useEffectEvent(load);

  useEffect(() => {
    let cancelled = false;

    loadEvent()
      .then((result) => {
        if (cancelled) return;
        setSnapshot({ key, version, data: result, error: null });
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setSnapshot((previous) => ({
          key,
          version,
          data: previous.key === key ? previous.data : null,
          error: describeError(reason),
        }));
      });

    return () => {
      cancelled = true;
    };
  }, [key, version]);

  const current = snapshot.key === key && snapshot.version === version;

  return {
    data: current ? snapshot.data : null,
    error: current ? snapshot.error : null,
    loading:
      !current ||
      (snapshot.data === null && snapshot.error === null),
    reload: () => setVersion((value) => value + 1),
  };
}
