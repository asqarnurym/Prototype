import { useState, useRef } from 'react';
import { processVideo, processUpload, ApiError } from '../api/client';

interface ProcessPanelProps {
  onJobQueued: () => void;
}

export default function ProcessPanel({ onJobQueued }: ProcessPanelProps) {
  const [videoPath, setVideoPath] = useState('');
  const [language, setLanguage] = useState('en');
  const [enableVisual, setEnableVisual] = useState(true);
  const [status, setStatus] = useState<{ text: string; kind: '' | 'success' | 'error' }>({
    text: 'No job started yet.',
    kind: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0] || null;

    if (!file && !videoPath.trim()) {
      setStatus({ text: 'Choose a video file or enter a server path.', kind: 'error' });
      return;
    }

    setSubmitting(true);
    setStatus({
      text: file ? 'Uploading video and queueing processing…' : 'Queueing video processing…',
      kind: '',
    });

    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      if (file) {
        await processUpload(file, language, enableVisual, controller.signal);
      } else {
        await processVideo(videoPath.trim(), language, enableVisual);
      }
      setStatus({ text: 'Job queued. Refreshing job list…', kind: 'success' });
      setVideoPath('');
      if (fileRef.current) fileRef.current.value = '';
      onJobQueued();
    } catch (err) {
      if (controller.signal.aborted) return;
      setStatus({
        text: err instanceof ApiError ? err.message : 'Processing request failed.',
        kind: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel" aria-labelledby="processPanelTitle">
      <h2 id="processPanelTitle">Process a video</h2>
      <p className="panel-intro">
        Upload a video file or enter a server-readable path to start preprocessing.
      </p>
      <form className="stack" onSubmit={handleSubmit}>
        <div>
          <label className="field-label" htmlFor="videoFileInput">
            Upload a video file
          </label>
          <input
            id="videoFileInput"
            ref={fileRef}
            type="file"
            accept="video/*"
            disabled={submitting}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="videoPathInput">
            Video path
          </label>
          <input
            id="videoPathInput"
            type="text"
            placeholder="./input/lecture.mp4"
            autoComplete="off"
            value={videoPath}
            onChange={(e) => setVideoPath(e.target.value)}
            disabled={submitting}
          />
        </div>
        <div className="inline-fields">
          <div>
            <label className="field-label" htmlFor="processLanguage">
              Language
            </label>
            <select
              id="processLanguage"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={submitting}
            >
              <option value="en">English</option>
              <option value="ru">Russian</option>
            </select>
          </div>
          <div className="checkbox-row">
            <input
              id="enableVisualInput"
              type="checkbox"
              checked={enableVisual}
              onChange={(e) => setEnableVisual(e.target.checked)}
              disabled={submitting}
            />
            <label htmlFor="enableVisualInput">Generate scenes and summary</label>
          </div>
        </div>
        <div className="action-row">
          <button className="btn-primary" type="submit" disabled={submitting}>
            {submitting ? 'Processing…' : 'Start processing'}
          </button>
          <p
            className={`status-text${status.kind ? ` ${status.kind}` : ''}`}
            role="status"
            aria-live="polite"
          >
            {status.text}
          </p>
        </div>
      </form>
    </section>
  );
}
