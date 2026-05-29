import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  buildProcessPayload,
  buildProcessUploadUrl,
  processVideo,
  processUpload,
  fetchJobs,
  fetchWords,
  fetchScenes,
  fetchSummary,
  describeScene,
  ApiError,
} from '../api/client';

function mockFetchOnce(response: Response) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response));
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('API client', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('buildProcessPayload', () => {
    it('builds correct /process payload', () => {
      const { url, init } = buildProcessPayload('./input/test.mp4', 'ru', false);
      expect(url).toBe('/process');
      expect(init.method).toBe('POST');
      expect(init.headers).toEqual({ 'Content-Type': 'application/json' });
      const body = JSON.parse(init.body as string);
      expect(body.video_path).toBe('./input/test.mp4');
      expect(body.language).toBe('ru');
      expect(body.enable_visual).toBe(false);
    });

    it('defaults enable_visual to true when passed true', () => {
      const { init } = buildProcessPayload('./input/test.mp4', 'en', true);
      const body = JSON.parse(init.body as string);
      expect(body.enable_visual).toBe(true);
    });
  });

  describe('buildProcessUploadUrl', () => {
    it('builds correct /process-upload URL with query params', () => {
      const url = buildProcessUploadUrl('en', true);
      expect(url).toBe('/process-upload?language=en&enable_visual=true');
    });

    it('handles disable_visual', () => {
      const url = buildProcessUploadUrl('ru', false);
      expect(url).toBe('/process-upload?language=ru&enable_visual=false');
    });
  });

  describe('processVideo', () => {
    it('calls fetch and returns parsed JSON on success', async () => {
      mockFetchOnce(jsonResponse({ job_id: 'test_123', status: 'queued', processing_time_sec: null, artifacts: {} }));

      const result = await processVideo('./input/test.mp4', 'en', true);
      expect(result.job_id).toBe('test_123');
      expect(result.status).toBe('queued');
    });

    it('throws ApiError on non-OK JSON response', async () => {
      mockFetchOnce(jsonResponse({ detail: 'File not found' }, 404));

      await expect(processVideo('./input/missing.mp4', 'en', true)).rejects.toThrow(ApiError);
    });

    it('throws with status from error response', async () => {
      mockFetchOnce(jsonResponse({ detail: 'File not found' }, 404));

      try {
        await processVideo('./input/missing.mp4', 'en', true);
        expect.fail('Should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        expect((err as ApiError).status).toBe(404);
      }
    });

    it('handles non-JSON error responses', async () => {
      mockFetchOnce(new Response('Internal Server Error', { status: 500 }));

      await expect(processVideo('./input/test.mp4', 'en', true)).rejects.toThrow(ApiError);
    });
  });

  describe('processUpload', () => {
    it('calls fetch with correct headers and body', async () => {
      const fn = vi.fn().mockResolvedValueOnce(
        jsonResponse({ job_id: 'upload_456', status: 'queued', processing_time_sec: null, artifacts: {} }),
      );
      vi.stubGlobal('fetch', fn);

      const file = new File(['fake-video-data'], 'test-video.mp4', { type: 'video/mp4' });
      const result = await processUpload(file, 'en', true);

      expect(result.job_id).toBe('upload_456');
      expect(fn).toHaveBeenCalledWith(
        '/process-upload?language=en&enable_visual=true',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'video/mp4',
            'X-Upload-Filename': 'test-video.mp4',
          },
          body: file,
        }),
      );
    });
  });

  describe('fetchJobs', () => {
    it('returns jobs list', async () => {
      mockFetchOnce(jsonResponse({ jobs: [{ job_id: 'j1', status: 'completed' }] }));

      const result = await fetchJobs();
      expect(result.jobs).toHaveLength(1);
      expect(result.jobs[0].job_id).toBe('j1');
    });
  });

  describe('409 processing state handling', () => {
    it('fetchWords throws ApiError with 409 status', async () => {
      mockFetchOnce(jsonResponse({ detail: 'Job is still processing; words is not ready yet.' }, 409));

      try {
        await fetchWords('processing-job');
        expect.fail('Should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        expect((err as ApiError).status).toBe(409);
      }
    });

    it('fetchScenes throws ApiError with 409 during processing', async () => {
      mockFetchOnce(jsonResponse({ detail: 'Job is still processing; scene index is not ready yet.' }, 409));

      try {
        await fetchScenes('processing-job');
        expect.fail('Should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        expect((err as ApiError).status).toBe(409);
      }
    });

    it('fetchSummary throws ApiError with 409 during processing', async () => {
      mockFetchOnce(jsonResponse({ detail: 'Job is still processing; summary is not ready yet.' }, 409));

      try {
        await fetchSummary('processing-job');
        expect.fail('Should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        expect((err as ApiError).status).toBe(409);
      }
    });
  });

  describe('describeScene', () => {
    it('sends POST with time and language', async () => {
      const fn = vi.fn().mockResolvedValueOnce(
        jsonResponse({
          scene_id: 1,
          time: 42.5,
          description: 'A person at a desk',
          tts_audio_url: '/jobs/j1/tts/1?language=en',
          tts_duration_sec: 3.2,
        }),
      );
      vi.stubGlobal('fetch', fn);

      const result = await describeScene('j1', { time: 42.5, language: 'en' });
      expect(result.scene_id).toBe(1);
      expect(result.description).toBe('A person at a desk');

      expect(fn).toHaveBeenCalledWith(
        '/jobs/j1/describe',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ time: 42.5, language: 'en' }),
        }),
      );
    });
  });
});
