import { useState, useCallback, useEffect, useRef } from 'react';
import type { JobSummary } from '../types/api';
import { fetchJobs, ApiError } from '../api/client';

interface UseJobsReturn {
  jobs: JobSummary[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useJobs(): UseJobsReturn {
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchJobs();
      if (!mountedRef.current) return;
      setJobs(data.jobs || []);

      const hasPending = (data.jobs || []).some(
        (j) => j.status === 'queued' || j.status === 'processing',
      );
      if (hasPending) {
        pollTimerRef.current = setTimeout(refresh, 3000);
      } else if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    } catch (err) {
      if (!mountedRef.current) return;
      setError(err instanceof ApiError ? err.message : 'Failed to load jobs');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    refresh();
    return () => {
      mountedRef.current = false;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, [refresh]);

  return { jobs, loading, error, refresh };
}
