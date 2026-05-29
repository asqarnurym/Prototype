import type {
  ProcessVideoResponse,
  JobsListResponse,
  JobSummary,
  WordsResponse,
  ScenesResponse,
  SummaryResponse,
  DescribeRequest,
  DescribeResponse,
  HealthResponse,
} from '../types/api';

const API_BASE = '';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const payload = await response.json();
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // use default detail
    }
    throw new ApiError(detail, response.status);
  }
  return response.json();
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export function buildProcessPayload(videoPath: string, language: string, enableVisual: boolean) {
  return {
    url: `${API_BASE}/process`,
    init: {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_path: videoPath, language, enable_visual: enableVisual }),
    },
  };
}

export function buildProcessUploadUrl(language: string, enableVisual: boolean) {
  return `${API_BASE}/process-upload?language=${encodeURIComponent(language)}&enable_visual=${String(enableVisual)}`;
}

export async function processVideo(videoPath: string, language: string, enableVisual: boolean): Promise<ProcessVideoResponse> {
  const { url, init } = buildProcessPayload(videoPath, language, enableVisual);
  const res = await fetch(url, init);
  return handleResponse<ProcessVideoResponse>(res);
}

export async function processUpload(
  file: File,
  language: string,
  enableVisual: boolean,
  signal?: AbortSignal,
): Promise<ProcessVideoResponse> {
  const url = buildProcessUploadUrl(language, enableVisual);
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': file.type || 'application/octet-stream',
      'X-Upload-Filename': file.name,
    },
    body: file,
    signal,
  });
  return handleResponse<ProcessVideoResponse>(res);
}

export async function fetchJobs(signal?: AbortSignal): Promise<JobsListResponse> {
  const res = await fetch(`${API_BASE}/jobs`, { signal });
  return handleResponse<JobsListResponse>(res);
}

export async function fetchJobMeta(jobId: string, signal?: AbortSignal): Promise<JobSummary> {
  const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/meta`, { signal });
  return handleResponse<JobSummary>(res);
}

export async function fetchWords(jobId: string, signal?: AbortSignal): Promise<WordsResponse> {
  const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/words`, { signal });
  return handleResponse<WordsResponse>(res);
}

export async function fetchScenes(jobId: string, signal?: AbortSignal): Promise<ScenesResponse> {
  const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/scenes`, { signal });
  return handleResponse<ScenesResponse>(res);
}

export async function fetchSummary(jobId: string, signal?: AbortSignal): Promise<SummaryResponse> {
  const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}/summary`, { signal });
  return handleResponse<SummaryResponse>(res);
}

export async function describeScene(
  jobId: string,
  request: DescribeRequest,
  signal?: AbortSignal,
): Promise<DescribeResponse> {
  const res = await fetch(
    `${API_BASE}/jobs/${encodeURIComponent(jobId)}/describe`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal,
    },
  );
  return handleResponse<DescribeResponse>(res);
}

export function buildVideoUrl(jobId: string): string {
  return `${API_BASE}/jobs/${encodeURIComponent(jobId)}/video`;
}

export function buildTtsUrl(jobId: string, sceneId: number, language: string): string {
  return `${API_BASE}/jobs/${encodeURIComponent(jobId)}/tts/${sceneId}?language=${encodeURIComponent(language)}`;
}

export async function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/health`, { signal });
  return handleResponse<HealthResponse>(res);
}
