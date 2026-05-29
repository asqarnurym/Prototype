import { useState, useCallback, useRef } from 'react';
import type { SubtitleSegment, Scene, Chapter } from '../types/api';
import { fetchWords, fetchScenes, fetchSummary, ApiError } from '../api/client';

interface UseVideoArtifactsReturn {
  segments: SubtitleSegment[];
  scenes: Scene[];
  chapters: Chapter[];
  summaryPoints: string[];
  loading: boolean;
  error: string | null;
  loadArtifacts: (jobId: string) => Promise<void>;
  clearArtifacts: () => void;
}

export function useVideoArtifacts(): UseVideoArtifactsReturn {
  const [segments, setSegments] = useState<SubtitleSegment[]>([]);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [summaryPoints, setSummaryPoints] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const clearArtifacts = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setSegments([]);
    setScenes([]);
    setChapters([]);
    setSummaryPoints([]);
    setError(null);
  }, []);

  const loadArtifacts = useCallback(async (jobId: string) => {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const [wordsData, scenesData, summaryData] = await Promise.all([
        fetchWords(jobId, controller.signal).catch((err) => {
          if (err instanceof ApiError && err.status === 409) return null;
          throw err;
        }),
        fetchScenes(jobId, controller.signal).catch((err) => {
          if (err instanceof ApiError && err.status === 409) return null;
          throw err;
        }),
        fetchSummary(jobId, controller.signal).catch((err) => {
          if (err instanceof ApiError && err.status === 409) return null;
          throw err;
        }),
      ]);

      if (controller.signal.aborted) return;

      setSegments(wordsData?.segments || []);
      setScenes(scenesData?.scenes || []);
      setChapters(summaryData?.chapters || []);
      setSummaryPoints(summaryData?.summary_points || []);
    } catch (err) {
      if (controller.signal.aborted) return;
      setError(err instanceof ApiError ? err.message : 'Failed to load video artifacts');
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, []);

  return { segments, scenes, chapters, summaryPoints, loading, error, loadArtifacts, clearArtifacts };
}
