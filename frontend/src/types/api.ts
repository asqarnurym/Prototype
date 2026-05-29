export interface ProcessVideoRequest {
  video_path: string;
  language: string;
  enable_visual: boolean;
}

export interface ProcessVideoResponse {
  job_id: string;
  status: string;
  processing_time_sec: number | null;
  artifacts: Record<string, string | null>;
}

export interface JobSummary {
  job_id: string;
  language: string;
  requested_language: string;
  detected_language: string;
  video_file: string;
  scenes_count: number;
  status: JobStatus;
  processing_time_sec: number | null;
  created_at: string | null;
  completed_at: string | null;
  artifacts: Record<string, string | null>;
  error_message: string | null;
}

export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed';

export interface JobsListResponse {
  jobs: JobSummary[];
}

export interface WordTiming {
  word: string;
  start: number;
  end: number;
}

export interface SubtitleSegment {
  start: number;
  end: number;
  text: string;
  words: WordTiming[];
}

export interface WordsResponse {
  job_id: string;
  language: string;
  detected_language: string;
  segments: SubtitleSegment[];
  total_words: number;
}

export interface Scene {
  scene_id: number;
  time: number;
  description: string;
  tts_cached: boolean;
  tts_cached_languages: string[];
}

export interface ScenesResponse {
  job_id: string;
  scenes: Scene[];
}

export interface Chapter {
  time: number;
  title: string;
}

export interface SummaryResponse {
  job_id: string;
  language: string;
  summary_version: number;
  summary_points: string[];
  chapters: Chapter[];
}

export interface DescribeRequest {
  time: number;
  language: string;
}

export interface DescribeResponse {
  scene_id: number;
  time: number;
  description: string;
  tts_audio_url: string | null;
  tts_duration_sec: number | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  whisper_model: string;
  device: string;
  description_mode: string;
  tts_provider: string;
  runtime: Record<string, unknown>;
  supported_languages: string[];
}

export type SubtitleMode = 'off' | 'standard' | 'word';

export interface AccessibilitySettings {
  uiFontSize: number;
  subtitleFontSize: number;
  subtitleMode: SubtitleMode;
  dyslexiaFont: boolean;
  wideSpacing: boolean;
  highContrast: boolean;
}

export const FONT_MIN = 70;
export const FONT_MAX = 160;
export const UI_FONT_STEP = 15;
export const SUBTITLE_FONT_STEP = 15;

export const DEFAULT_A11Y_SETTINGS: AccessibilitySettings = {
  uiFontSize: 100,
  subtitleFontSize: 100,
  subtitleMode: 'word',
  dyslexiaFont: false,
  wideSpacing: false,
  highContrast: false,
};

export function clampFontSize(value: number): number {
  return Math.max(FONT_MIN, Math.min(FONT_MAX, value));
}

export function formatTime(seconds: number): string {
  const s = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = Math.floor(s % 60);
  if (h > 0) {
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  }
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}
