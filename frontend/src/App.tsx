import { useState, useRef, useCallback } from 'react';
import type { Scene, JobSummary } from './types/api';
import { describeScene, buildTtsUrl, ApiError } from './api/client';
import { useJobs } from './hooks/useJobs';
import { useVideoArtifacts } from './hooks/useVideoArtifacts';
import { useAccessibilitySettings } from './hooks/useAccessibilitySettings';
import { usePlayerKeyboard } from './hooks/usePlayerKeyboard';
import CustomVideoPlayer from './components/VideoPlayer/CustomVideoPlayer';
import type { VideoPlayerHandle } from './components/VideoPlayer/CustomVideoPlayer';
import ProcessPanel from './components/ProcessPanel';
import JobPanel from './components/JobPanel';
import AccessibilityPanel from './components/AccessibilityPanel';
import SummaryTabs from './components/SummaryTabs';
import SceneDescriptionPanel from './components/SceneDescriptionPanel';

export default function App() {
  const { jobs, loading: jobsLoading, error: jobsError, refresh: refreshJobs } = useJobs();
  const {
    segments,
    scenes,
    chapters,
    summaryPoints,
    loadArtifacts,
    clearArtifacts,
  } = useVideoArtifacts();

  const a11y = useAccessibilitySettings();
  const playerRef = useRef<VideoPlayerHandle>(null);

  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedJobLang, setSelectedJobLang] = useState('en');
  const [descriptionText, setDescriptionText] = useState('');
  const [descriptionSceneId, setDescriptionSceneId] = useState<number | null>(null);
  const [descriptionTime, setDescriptionTime] = useState<number | null>(null);
  const [descriptionTtsDuration, setDescriptionTtsDuration] = useState<number | null>(null);
  const [descriptionLoading, setDescriptionLoading] = useState(false);
  const [descriptionPlaying, setDescriptionPlaying] = useState(false);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);
  const [descriptionActive, setDescriptionActive] = useState(false);
  const [descriptionRequestPending, setDescriptionRequestPending] = useState(false);
  const [descriptionShouldResume, setDescriptionShouldResume] = useState(false);
  const [activeSceneId, setActiveSceneId] = useState<number | null>(null);

  const descriptionFlowToken = useRef(0);
  const ttsAudioRef = useRef<HTMLAudioElement | null>(null);
  const [srMessage, setSrMessage] = useState('');

  function announce(text: string) {
    setSrMessage('');
    setTimeout(() => setSrMessage(text), 30);
  }

  // Clean up TTS audio
  const clearTtsAudio = useCallback((resetTime = true) => {
    const audio = ttsAudioRef.current;
    if (!audio) return;
    audio.pause();
    if (resetTime) audio.currentTime = 0;
    audio.onended = null;
    audio.onerror = null;
    ttsAudioRef.current = null;
  }, []);

  // Stop description flow
  const stopDescription = useCallback(
    (shouldAnnounce = true) => {
      descriptionFlowToken.current += 1;
      setDescriptionRequestPending(false);
      setDescriptionShouldResume(false);
      setDescriptionActive(false);
      setDescriptionPlaying(false);
      clearTtsAudio(true);
      if (shouldAnnounce) announce('Description stopped');
    },
    [clearTtsAudio],
  );

  // Load a job
  const handleSelectJob = useCallback(
    (jobId: string) => {
      setSelectedJobId(jobId);
      const job = jobs.find((j: JobSummary) => j.job_id === jobId);
      setSelectedJobLang(job?.language || 'en');
      stopDescription(false);
      clearArtifacts();
      loadArtifacts(jobId);
      setDescriptionText('');
      setDescriptionSceneId(null);
      setDescriptionTime(null);
      setDescriptionTtsDuration(null);
      setDescriptionError(null);
      setActiveSceneId(null);
      setDescriptionActive(false);
      announce(`Loaded job ${jobId}`);
    },
    [jobs, stopDescription, clearArtifacts, loadArtifacts],
  );

  // Cancel description when video plays
  const handleVideoPlay = useCallback(() => {
    if (descriptionRequestPending || descriptionActive) {
      stopDescription(false);
      setDescriptionText('Description stopped because video playback resumed.');
      setDescriptionError(null);
      announce('Description stopped because video playback resumed');
    }
  }, [descriptionRequestPending, descriptionActive, stopDescription]);

  // Describe current scene
  const handleDescribe = useCallback(async () => {
    if (!selectedJobId || !playerRef.current) return;

    const token = ++descriptionFlowToken.current;
    const shouldResume = !playerRef.current.isPaused();
    stopDescription(false);
    descriptionFlowToken.current = token;

    setDescriptionRequestPending(true);
    setDescriptionActive(true);
    setDescriptionShouldResume(shouldResume);
    playerRef.current.pause();
    setDescriptionLoading(true);
    setDescriptionError(null);
    setDescriptionText('Generating a scene description…');

    try {
      const currentTime = playerRef.current.getCurrentTime();
      const response = await describeScene(
        selectedJobId,
        { time: currentTime, language: selectedJobLang },
      );

      if (token !== descriptionFlowToken.current) return;

      setDescriptionRequestPending(false);
      setDescriptionText(response.description);
      setDescriptionSceneId(response.scene_id);
      setDescriptionTime(response.time);
      setDescriptionTtsDuration(response.tts_duration_sec);
      setDescriptionLoading(false);
      setActiveSceneId(response.scene_id);

      if (response.tts_audio_url) {
        // Start TTS playback
        clearTtsAudio(true);

        const audio = new Audio(buildTtsUrl(selectedJobId, response.scene_id, selectedJobLang));
        audio.playbackRate = playerRef.current?.getPlaybackRate() ?? 1;
        ttsAudioRef.current = audio;

        audio.onended = () => {
          const resume = descriptionActive && descriptionShouldResume;
          setDescriptionActive(false);
          setDescriptionPlaying(false);
          setDescriptionShouldResume(false);
          clearTtsAudio(false);
          if (resume) {
            playerRef.current?.play();
          }
        };

        audio.onerror = () => {
          setDescriptionText((prev) => `${prev} Audio playback failed.`);
          setDescriptionActive(false);
          setDescriptionPlaying(false);
          setDescriptionShouldResume(false);
          clearTtsAudio(false);
        };

        setDescriptionPlaying(true);
        announce(`Description ready for scene ${response.scene_id}`);

        const playPromise = audio.play();
        if (playPromise) {
          playPromise.catch(() => {
            setDescriptionText((prev) => `${prev} Audio playback was blocked.`);
            setDescriptionActive(false);
            setDescriptionPlaying(false);
            setDescriptionShouldResume(false);
            clearTtsAudio(false);
            if (shouldResume) {
              playerRef.current?.play();
            }
          });
        }
      } else {
        announce(`Description ready for scene ${response.scene_id}`);
        setDescriptionActive(false);
        if (shouldResume) {
          playerRef.current?.play();
        }
      }
    } catch (err) {
      if (token !== descriptionFlowToken.current) return;
      setDescriptionRequestPending(false);
      setDescriptionLoading(false);
      setDescriptionActive(false);
      setDescriptionError(err instanceof ApiError ? err.message : 'Description request failed.');
      if (shouldResume) {
        playerRef.current?.play();
      }
      announce('Description request failed');
    }
  }, [selectedJobId, selectedJobLang, stopDescription, clearTtsAudio]);

  // Stop description handler (from UI/keyboard)
  const handleStopDescription = useCallback(() => {
    stopDescription(true);
    setDescriptionText('');
    setDescriptionError(null);
  }, [stopDescription]);

  // Chapter click
  const handleChapterClick = useCallback((time: number) => {
    playerRef.current?.seek(time);
    playerRef.current?.play();
  }, []);

  // Scene click
  const handleSceneClick = useCallback(
    (scene: Scene) => {
      playerRef.current?.seek(scene.time || 0);
      // Small delay so video seek completes before describe
      setTimeout(() => handleDescribe(), 100);
    },
    [handleDescribe],
  );

  // Keyboard shortcuts
  usePlayerKeyboard({
    onPlayPause: () => playerRef.current?.togglePlay(),
    onSeekBack: (seconds) => {
      if (playerRef.current) {
        playerRef.current.seek(playerRef.current.getCurrentTime() - seconds);
      }
    },
    onSeekForward: (seconds) => {
      if (playerRef.current) {
        playerRef.current.seek(playerRef.current.getCurrentTime() + seconds);
      }
    },
    onMute: () => playerRef.current?.toggleMute(),
    onFullscreen: () => playerRef.current?.requestFullscreen(),
    onDescribe: handleDescribe,
    onStopDescription: handleStopDescription,
  });

  // Sync subtitle mode changes from accessibility panel to player
  // (this is handled by passing a11y.settings.subtitleMode directly)

  // When subtitle mode changes in the a11y panel, we need to sync it back
  // But the CustomVideoPlayer has its own internal state for subtitle mode.
  // We'll handle this by having the player read from a shared source.
  // For now, the player's subtitle mode changes are independent.
  // The a11y panel setting controls the default, and PlayerControls exposes a selector.
  // The a11y panel's subtitleMode triggers a change in the player via useEffect in CustomVideoPlayer.

  return (
    <div className="page-shell" id="uiSurface">
      <header className="page-header">
        <h1 className="page-title">Prototype — Accessible Video Review</h1>
        <p className="page-subtitle">
          Process a video, review the output, and use accessible subtitles with scene descriptions,
          chapters, and summary support.
        </p>
      </header>

      <main className="layout-grid">
        <ProcessPanel onJobQueued={refreshJobs} />

        <JobPanel
          jobs={jobs}
          loading={jobsLoading}
          error={jobsError}
          selectedJobId={selectedJobId}
          onSelect={handleSelectJob}
          onRefresh={refreshJobs}
        />

        <AccessibilityPanel
          settings={a11y.settings}
          onChangeUiFontSize={a11y.changeUiFontSize}
          onChangeSubtitleFontSize={a11y.changeSubtitleFontSize}
          onSetSubtitleMode={a11y.setSubtitleMode}
          onToggleDyslexiaFont={a11y.toggleDyslexiaFont}
          onToggleWideSpacing={a11y.toggleWideSpacing}
          onToggleHighContrast={a11y.toggleHighContrast}
        />

        <CustomVideoPlayer
          ref={playerRef}
          jobId={selectedJobId}
          segments={segments}
          subtitleMode={a11y.settings.subtitleMode}
          onTimeUpdate={() => {}}
          onPlay={handleVideoPlay}
          onPause={() => {}}
          onDescribe={handleDescribe}
          onStopDescription={handleStopDescription}
          descriptionActive={descriptionActive || descriptionPlaying}
          descriptionRequestPending={descriptionRequestPending}
        />

        <SceneDescriptionPanel
          description={descriptionText}
          sceneId={descriptionSceneId}
          time={descriptionTime}
          ttsDuration={descriptionTtsDuration}
          loading={descriptionLoading}
          playing={descriptionPlaying}
          error={descriptionError}
        />

        <SummaryTabs
          summaryPoints={summaryPoints}
          chapters={chapters}
          scenes={scenes}
          activeSceneId={activeSceneId}
          onChapterClick={handleChapterClick}
          onSceneClick={handleSceneClick}
        />
      </main>

      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {srMessage}
      </div>
    </div>
  );
}
