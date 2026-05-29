import type { JobSummary } from '../types/api';

interface JobPanelProps {
  jobs: JobSummary[];
  loading: boolean;
  error: string | null;
  selectedJobId: string | null;
  onSelect: (jobId: string) => void;
  onRefresh: () => void;
}

export default function JobPanel({
  jobs,
  loading,
  error,
  selectedJobId,
  onSelect,
  onRefresh,
}: JobPanelProps) {
  return (
    <section className="panel" aria-labelledby="jobPanelTitle">
      <div className="action-row" style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h2 id="jobPanelTitle">Processed jobs</h2>
        <button
          type="button"
          className="btn-secondary"
          onClick={onRefresh}
          disabled={loading}
          aria-label="Refresh job list"
        >
          Refresh
        </button>
      </div>

      {error && (
        <p className="status-text error" role="alert">
          {error}
        </p>
      )}

      {loading && jobs.length === 0 ? (
        <p className="status-text">Loading jobs…</p>
      ) : jobs.length === 0 ? (
        <p className="status-text">No jobs yet. Process a video to get started.</p>
      ) : (
        <select
          id="jobSelect"
          value={selectedJobId || ''}
          onChange={(e) => {
            if (e.target.value) onSelect(e.target.value);
          }}
          aria-describedby="jobHelpText"
        >
          <option value="">Select a processed job</option>
          {jobs.map((job) => (
            <option key={job.job_id} value={job.job_id}>
              {job.video_file || job.job_id} [{job.language.toUpperCase()}]
              {job.scenes_count ? ` · ${job.scenes_count} scenes` : ''} — {job.status}
            </option>
          ))}
        </select>
      )}
      <p className="panel-intro" id="jobHelpText">
        Select an existing job to load the video, summary, chapters, scenes, and custom subtitle data.
      </p>
    </section>
  );
}
