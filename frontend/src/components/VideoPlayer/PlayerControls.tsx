import type { SubtitleMode } from '../../types/api';
import { formatTime } from '../../types/api';

interface PlayerControlsProps {
  playing: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  muted: boolean;
  playbackRate: number;
  subtitleMode: SubtitleMode;
  descriptionActive: boolean;
  descriptionRequestPending: boolean;
  onPlayPause: () => void;
  onSeek: (time: number) => void;
  onVolumeChange: (vol: number) => void;
  onMuteToggle: () => void;
  onSpeedChange: (speed: number) => void;
  onFullscreen: () => void;
  onSubtitleModeChange: (mode: SubtitleMode) => void;
  onDescribe: () => void;
  onStopDescription: () => void;
}

const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];

export default function PlayerControls({
  playing,
  currentTime,
  duration,
  volume,
  muted,
  playbackRate,
  subtitleMode,
  descriptionActive,
  descriptionRequestPending,
  onPlayPause,
  onSeek,
  onVolumeChange,
  onMuteToggle,
  onSpeedChange,
  onFullscreen,
  onSubtitleModeChange,
  onDescribe,
  onStopDescription,
}: PlayerControlsProps) {
  const displayDuration = Number.isFinite(duration) ? duration : 0;

  return (
    <div className="player-controls" role="group" aria-label="Video player controls">
      <button
        type="button"
        className="ctrl-btn ctrl-btn--play"
        onClick={onPlayPause}
        aria-label={playing ? 'Pause' : 'Play'}
      >
        {playing ? (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <rect x="4" y="3" width="4" height="14" rx="1" />
            <rect x="12" y="3" width="4" height="14" rx="1" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <polygon points="5,3 17,10 5,17" />
          </svg>
        )}
      </button>

      <span className="ctrl-time" aria-label={`Current time ${formatTime(currentTime)}`}>
        {formatTime(currentTime)}
      </span>

      <input
        type="range"
        className="ctrl-slider ctrl-slider--seek"
        min={0}
        max={displayDuration || 0}
        step={0.1}
        value={currentTime}
        onChange={(e) => onSeek(Number(e.target.value))}
        aria-label="Seek position"
        aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`}
      />

      <span className="ctrl-time" aria-label={`Duration ${formatTime(displayDuration)}`}>
        {formatTime(displayDuration)}
      </span>

      <button
        type="button"
        className="ctrl-btn ctrl-btn--volume"
        onClick={onMuteToggle}
        aria-label={muted ? 'Unmute' : 'Mute'}
      >
        {muted || volume === 0 ? (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <polygon points="2,7 6,7 11,2 11,18 6,13 2,13" />
            <line x1="14" y1="7" x2="18" y2="13" stroke="currentColor" strokeWidth="1.5" />
            <line x1="18" y1="7" x2="14" y2="13" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <polygon points="2,7 6,7 11,2 11,18 6,13 2,13" />
            <path d="M13,6 Q17,8 17,10 Q17,12 13,14" fill="none" stroke="currentColor" strokeWidth="1.5" />
          </svg>
        )}
      </button>

      <input
        type="range"
        className="ctrl-slider ctrl-slider--volume"
        min={0}
        max={1}
        step={0.05}
        value={muted ? 0 : volume}
        onChange={(e) => onVolumeChange(Number(e.target.value))}
        aria-label="Volume"
      />

      <select
        className="ctrl-select"
        value={playbackRate}
        onChange={(e) => onSpeedChange(Number(e.target.value))}
        aria-label="Playback speed"
      >
        {SPEEDS.map((s) => (
          <option key={s} value={s}>
            {s}x
          </option>
        ))}
      </select>

      <select
        className="ctrl-select"
        value={subtitleMode}
        onChange={(e) => onSubtitleModeChange(e.target.value as SubtitleMode)}
        aria-label="Subtitle mode"
      >
        <option value="off">Subtitles off</option>
        <option value="standard">Standard</option>
        <option value="word">Word-by-word</option>
      </select>

      <button
        type="button"
        className="ctrl-btn ctrl-btn--describe"
        onClick={onDescribe}
        disabled={descriptionRequestPending || descriptionActive}
        aria-label="Describe current scene"
      >
        {descriptionRequestPending ? 'Loading…' : 'Describe'}
      </button>

      <button
        type="button"
        className="ctrl-btn ctrl-btn--stop"
        onClick={onStopDescription}
        disabled={!descriptionActive && !descriptionRequestPending}
        aria-label="Stop description"
      >
        Stop
      </button>

      <button
        type="button"
        className="ctrl-btn ctrl-btn--fullscreen"
        onClick={onFullscreen}
        aria-label="Fullscreen"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <rect x="2" y="4" width="6" height="5" rx="1" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <rect x="12" y="4" width="6" height="5" rx="1" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <rect x="2" y="11" width="6" height="5" rx="1" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <rect x="12" y="11" width="6" height="5" rx="1" fill="none" stroke="currentColor" strokeWidth="1.5" />
        </svg>
      </button>
    </div>
  );
}
