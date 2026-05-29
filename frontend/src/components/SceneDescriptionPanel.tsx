import { formatTime } from '../types/api';

interface SceneDescriptionPanelProps {
  description: string;
  sceneId: number | null;
  time: number | null;
  ttsDuration: number | null;
  loading: boolean;
  playing: boolean;
  error: string | null;
}

export default function SceneDescriptionPanel({
  description,
  sceneId,
  time,
  ttsDuration,
  loading,
  playing,
  error,
}: SceneDescriptionPanelProps) {
  if (error) {
    return (
      <section className="panel" aria-labelledby="descriptionTitle">
        <h2 id="descriptionTitle">Scene description</h2>
        <div className="reading-surface description-text" role="alert">
          {error}
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="panel" aria-labelledby="descriptionTitle">
        <h2 id="descriptionTitle">Scene description</h2>
        <div className="reading-surface description-text" role="status" aria-live="polite">
          Generating a scene description…
        </div>
      </section>
    );
  }

  if (!description) {
    return (
      <section className="panel" aria-labelledby="descriptionTitle">
        <h2 id="descriptionTitle">Scene description</h2>
        <div className="reading-surface description-text is-empty" role="status" aria-live="polite">
          Load a processed job, then press "Describe" or use the D key.
        </div>
      </section>
    );
  }

  return (
    <section className="panel" aria-labelledby="descriptionTitle">
      <h2 id="descriptionTitle">Scene description</h2>
      <div
        className="reading-surface description-text"
        role="status"
        aria-live="polite"
        aria-atomic="true"
      >
        {description}
        {playing && (
          <span className="description-playing-indicator" aria-live="polite">
            {' '}
            (audio playing)
          </span>
        )}
      </div>
      <div className="meta-row">
        {sceneId !== null && `Scene ${sceneId}`}
        {time !== null && ` · ${formatTime(time)}`}
        {ttsDuration !== null && ` · ${ttsDuration.toFixed(1)}s audio`}
      </div>
    </section>
  );
}
