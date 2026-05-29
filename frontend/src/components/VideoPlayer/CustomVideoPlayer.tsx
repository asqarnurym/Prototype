import {
  useRef,
  useEffect,
  useCallback,
  useState,
  forwardRef,
  useImperativeHandle,
} from 'react';
import type { SubtitleSegment, SubtitleMode } from '../../types/api';
import { buildVideoUrl } from '../../api/client';
import SubtitleOverlay from './SubtitleOverlay';
import PlayerControls from './PlayerControls';

export interface VideoPlayerHandle {
  play: () => void;
  pause: () => void;
  togglePlay: () => void;
  seek: (time: number) => void;
  getCurrentTime: () => number;
  isPaused: () => boolean;
  getVolume: () => number;
  setVolume: (vol: number) => void;
  getMuted: () => boolean;
  setMuted: (muted: boolean) => void;
  toggleMute: () => void;
  getPlaybackRate: () => number;
  setPlaybackRate: (rate: number) => void;
  requestFullscreen: () => void;
  getVideoElement: () => HTMLVideoElement | null;
}

interface CustomVideoPlayerProps {
  jobId: string | null;
  segments: SubtitleSegment[];
  subtitleMode: SubtitleMode;
  onTimeUpdate: (time: number) => void;
  onPlay: () => void;
  onPause: () => void;
  onDescribe: () => void;
  onStopDescription: () => void;
  descriptionActive: boolean;
  descriptionRequestPending: boolean;
}

const CustomVideoPlayer = forwardRef<VideoPlayerHandle, CustomVideoPlayerProps>(
  function CustomVideoPlayer(
    {
      jobId,
      segments,
      subtitleMode,
      onTimeUpdate,
      onPlay,
      onPause,
      onDescribe,
      onStopDescription,
      descriptionActive,
      descriptionRequestPending,
    },
    ref,
  ) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const animFrameRef = useRef<number | null>(null);

    const [playing, setPlaying] = useState(false);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [volume, setVolumeState] = useState(1);
    const [muted, setMutedState] = useState(false);
    const [playbackRate, setPlaybackRateState] = useState(1);
    const [internalSubtitleMode, setInternalSubtitleMode] = useState(subtitleMode);

    useEffect(() => {
      setInternalSubtitleMode(subtitleMode);
    }, [subtitleMode]);

    const videoUrl = jobId ? buildVideoUrl(jobId) : '';

    // Expose imperative handle
    useImperativeHandle(ref, () => ({
      play() {
        videoRef.current?.play();
      },
      pause() {
        videoRef.current?.pause();
      },
      togglePlay() {
        const v = videoRef.current;
        if (!v) return;
        if (v.paused) v.play();
        else v.pause();
      },
      seek(time: number) {
        if (videoRef.current) {
          videoRef.current.currentTime = Math.max(0, Math.min(time, videoRef.current.duration || time));
        }
      },
      getCurrentTime() {
        return videoRef.current?.currentTime || 0;
      },
      isPaused() {
        return videoRef.current?.paused ?? true;
      },
      getVolume() {
        return videoRef.current?.volume ?? 1;
      },
      setVolume(vol: number) {
        if (videoRef.current) {
          videoRef.current.volume = vol;
          setVolumeState(vol);
          if (vol > 0 && videoRef.current.muted) {
            videoRef.current.muted = false;
            setMutedState(false);
          }
        }
      },
      getMuted() {
        return videoRef.current?.muted ?? false;
      },
      setMuted(m: boolean) {
        if (videoRef.current) {
          videoRef.current.muted = m;
          setMutedState(m);
        }
      },
      toggleMute() {
        if (videoRef.current) {
          videoRef.current.muted = !videoRef.current.muted;
          setMutedState(videoRef.current.muted);
        }
      },
      getPlaybackRate() {
        return videoRef.current?.playbackRate ?? 1;
      },
      setPlaybackRate(rate: number) {
        if (videoRef.current) {
          videoRef.current.playbackRate = rate;
          setPlaybackRateState(rate);
        }
      },
      requestFullscreen() {
        containerRef.current?.requestFullscreen().catch(() => {});
      },
      getVideoElement() {
        return videoRef.current;
      },
    }));

    // rAF loop for time updates and subtitle rendering
    const tick = useCallback(() => {
      const v = videoRef.current;
      if (!v) return;
      const time = v.currentTime;
      setCurrentTime(time);
      onTimeUpdate(time);
      animFrameRef.current = requestAnimationFrame(tick);
    }, [onTimeUpdate]);

    useEffect(() => {
      if (playing) {
        animFrameRef.current = requestAnimationFrame(tick);
      } else if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
        animFrameRef.current = null;
        // Also update with current time when paused (for seeking)
        const v = videoRef.current;
        if (v) {
          setCurrentTime(v.currentTime);
          onTimeUpdate(v.currentTime);
        }
      }
      return () => {
        if (animFrameRef.current) {
          cancelAnimationFrame(animFrameRef.current);
          animFrameRef.current = null;
        }
      };
    }, [playing, tick]);

    // Reset when job changes
    useEffect(() => {
      setCurrentTime(0);
      setDuration(0);
      setPlaying(false);
    }, [jobId]);

    const handleVideoPlay = useCallback(() => {
      setPlaying(true);
      onPlay();
    }, [onPlay]);

    const handleVideoPause = useCallback(() => {
      setPlaying(false);
      onPause();
    }, [onPause]);

    const handleLoadedMetadata = useCallback(() => {
      if (videoRef.current) {
        setDuration(videoRef.current.duration);
        setVolumeState(videoRef.current.volume);
        setMutedState(videoRef.current.muted);
      }
    }, []);

    const handlePlayPause = useCallback(() => {
      const v = videoRef.current;
      if (!v) return;
      if (v.paused) v.play();
      else v.pause();
    }, []);

    const handleSeek = useCallback((time: number) => {
      if (videoRef.current) {
        videoRef.current.currentTime = time;
        setCurrentTime(time);
      }
    }, []);

    const handleVolumeChange = useCallback((vol: number) => {
      if (videoRef.current) {
        videoRef.current.volume = vol;
        setVolumeState(vol);
        if (vol > 0 && videoRef.current.muted) {
          videoRef.current.muted = false;
          setMutedState(false);
        }
      }
    }, []);

    const handleMuteToggle = useCallback(() => {
      if (videoRef.current) {
        videoRef.current.muted = !videoRef.current.muted;
        setMutedState(videoRef.current.muted);
      }
    }, []);

    const handleSpeedChange = useCallback((speed: number) => {
      if (videoRef.current) {
        videoRef.current.playbackRate = speed;
        setPlaybackRateState(speed);
      }
    }, []);

    const handleFullscreen = useCallback(() => {
      containerRef.current?.requestFullscreen().catch(() => {});
    }, []);

    const handleSubtitleModeChange = useCallback(
      (mode: SubtitleMode) => {
        setInternalSubtitleMode(mode);
      },
      [],
    );

    return (
      <section className="panel video-shell" aria-labelledby="playerTitle">
        <div className="action-row" style={{ justifyContent: 'space-between', alignItems: 'baseline' }}>
          <h2 id="playerTitle">Video player</h2>
          {!jobId && <span className="lang-badge">No job loaded</span>}
        </div>

        <div className="video-frame" ref={containerRef}>
          {jobId ? (
            <video
              ref={videoRef}
              src={videoUrl}
              className="video-element"
              onPlay={handleVideoPlay}
              onPause={handleVideoPause}
              onEnded={handleVideoPause}
              onLoadedMetadata={handleLoadedMetadata}
              onError={() => setPlaying(false)}
              playsInline
              disableRemotePlayback
            >
              Your browser does not support the video element.
            </video>
          ) : (
            <div className="video-placeholder" role="img" aria-label="No video loaded">
              <p>Select a processed job to play video</p>
            </div>
          )}
          <SubtitleOverlay
            segments={segments}
            currentTime={currentTime}
            mode={internalSubtitleMode}
            visible={!!jobId}
          />
        </div>

        <PlayerControls
          playing={playing}
          currentTime={currentTime}
          duration={duration}
          volume={volume}
          muted={muted}
          playbackRate={playbackRate}
          subtitleMode={internalSubtitleMode}
          descriptionActive={descriptionActive}
          descriptionRequestPending={descriptionRequestPending}
          onPlayPause={handlePlayPause}
          onSeek={handleSeek}
          onVolumeChange={handleVolumeChange}
          onMuteToggle={handleMuteToggle}
          onSpeedChange={handleSpeedChange}
          onFullscreen={handleFullscreen}
          onSubtitleModeChange={handleSubtitleModeChange}
          onDescribe={onDescribe}
          onStopDescription={onStopDescription}
        />

        <p className="keyboard-hint" aria-hidden="true">
          Keyboard: <kbd>Space</kbd>/<kbd>K</kbd> play/pause · <kbd>←</kbd><kbd>→</kbd> seek 5s · <kbd>J</kbd>/<kbd>L</kbd> seek 10s · <kbd>M</kbd> mute · <kbd>F</kbd> fullscreen · <kbd>D</kbd> describe · <kbd>S</kbd>/<kbd>Esc</kbd> stop
        </p>
      </section>
    );
  },
);

export default CustomVideoPlayer;
