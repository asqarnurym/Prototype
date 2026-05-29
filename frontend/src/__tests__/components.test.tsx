import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PlayerControls from '../components/VideoPlayer/PlayerControls';
import SummaryTabs from '../components/SummaryTabs';
import SceneDescriptionPanel from '../components/SceneDescriptionPanel';
import AccessibilityPanel from '../components/AccessibilityPanel';
import type { AccessibilitySettings } from '../types/api';

const defaultA11y: AccessibilitySettings = {
  uiFontSize: 100,
  subtitleFontSize: 100,
  subtitleMode: 'word',
  dyslexiaFont: false,
  wideSpacing: false,
  highContrast: false,
};

describe('PlayerControls', () => {
  const baseProps = {
    playing: false,
    currentTime: 0,
    duration: 120,
    volume: 1,
    muted: false,
    playbackRate: 1,
    subtitleMode: 'word' as const,
    descriptionActive: false,
    descriptionRequestPending: false,
    onPlayPause: vi.fn(),
    onSeek: vi.fn(),
    onVolumeChange: vi.fn(),
    onMuteToggle: vi.fn(),
    onSpeedChange: vi.fn(),
    onFullscreen: vi.fn(),
    onSubtitleModeChange: vi.fn(),
    onDescribe: vi.fn(),
    onStopDescription: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('play button has accessible name "Play" when paused', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('button', { name: 'Play' })).toBeInTheDocument();
  });

  it('play button has accessible name "Pause" when playing', () => {
    render(<PlayerControls {...baseProps} playing />);
    expect(screen.getByRole('button', { name: 'Pause' })).toBeInTheDocument();
  });

  it('mute button has accessible name', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('button', { name: 'Mute' })).toBeInTheDocument();
  });

  it('mute button changes label when muted', () => {
    render(<PlayerControls {...baseProps} muted />);
    expect(screen.getByRole('button', { name: 'Unmute' })).toBeInTheDocument();
  });

  it('fullscreen button has accessible name', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('button', { name: 'Fullscreen' })).toBeInTheDocument();
  });

  it('describe button has accessible name', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('button', { name: 'Describe current scene' })).toBeInTheDocument();
  });

  it('stop description button has accessible name', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('button', { name: 'Stop description' })).toBeInTheDocument();
  });

  it('seek slider has accessible name', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('slider', { name: 'Seek position' })).toBeInTheDocument();
  });

  it('volume slider has accessible name', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('slider', { name: 'Volume' })).toBeInTheDocument();
  });

  it('speed selector has accessible name', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('combobox', { name: 'Playback speed' })).toBeInTheDocument();
  });

  it('subtitle mode selector has accessible name', () => {
    render(<PlayerControls {...baseProps} />);
    expect(screen.getByRole('combobox', { name: 'Subtitle mode' })).toBeInTheDocument();
  });

  it('calls onPlayPause when play button clicked', async () => {
    const onPlayPause = vi.fn();
    render(<PlayerControls {...baseProps} onPlayPause={onPlayPause} />);
    await userEvent.click(screen.getByRole('button', { name: 'Play' }));
    expect(onPlayPause).toHaveBeenCalledTimes(1);
  });

  it('calls onMuteToggle when mute button clicked', async () => {
    const onMuteToggle = vi.fn();
    render(<PlayerControls {...baseProps} onMuteToggle={onMuteToggle} />);
    await userEvent.click(screen.getByRole('button', { name: 'Mute' }));
    expect(onMuteToggle).toHaveBeenCalledTimes(1);
  });

  it('calls onDescribe when describe button clicked', async () => {
    const onDescribe = vi.fn();
    render(<PlayerControls {...baseProps} onDescribe={onDescribe} />);
    await userEvent.click(screen.getByRole('button', { name: 'Describe current scene' }));
    expect(onDescribe).toHaveBeenCalledTimes(1);
  });

  it('calls onStopDescription when stop button clicked', async () => {
    const onStopDescription = vi.fn();
    render(
      <PlayerControls {...baseProps} descriptionActive onStopDescription={onStopDescription} />,
    );
    await userEvent.click(screen.getByRole('button', { name: 'Stop description' }));
    expect(onStopDescription).toHaveBeenCalledTimes(1);
  });

  it('describe button is disabled when request is pending', () => {
    render(<PlayerControls {...baseProps} descriptionRequestPending />);
    expect(screen.getByRole('button', { name: 'Describe current scene' })).toBeDisabled();
  });
});

describe('SummaryTabs', () => {
  const baseProps = {
    summaryPoints: ['Point 1', 'Point 2'],
    chapters: [{ time: 0, title: 'Intro' }, { time: 60, title: 'Main' }],
    scenes: [
      { scene_id: 1, time: 0, description: 'Opening scene', tts_cached: false, tts_cached_languages: [] },
      { scene_id: 2, time: 30, description: 'Middle scene', tts_cached: true, tts_cached_languages: ['en'] },
    ],
    activeSceneId: null,
    onChapterClick: vi.fn(),
    onSceneClick: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders three tabs with correct roles', () => {
    render(<SummaryTabs {...baseProps} />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(3);
    expect(tabs[0]).toHaveTextContent('Summary');
    expect(tabs[1]).toHaveTextContent('Chapters');
    expect(tabs[2]).toHaveTextContent('Scenes');
  });

  it('summary tab is selected by default', () => {
    render(<SummaryTabs {...baseProps} />);
    expect(screen.getByRole('tab', { name: 'Summary' })).toHaveAttribute('aria-selected', 'true');
  });

  it('summary panel is visible by default', () => {
    render(<SummaryTabs {...baseProps} />);
    const panel = screen.getByRole('tabpanel', { name: 'Summary' });
    expect(panel).not.toHaveAttribute('hidden');
    expect(panel).toHaveTextContent('Point 1');
  });

  it('chapters panel is hidden by default', () => {
    render(<SummaryTabs {...baseProps} />);
    const chaptersPanel = document.getElementById('tabChapters');
    expect(chaptersPanel).toHaveAttribute('hidden');
  });

  it('clicking chapters tab switches panels', async () => {
    render(<SummaryTabs {...baseProps} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Chapters' }));

    expect(screen.getByRole('tab', { name: 'Chapters' })).toHaveAttribute('aria-selected', 'true');
    // tabpanels use aria-labelledby, queried by id
    const chaptersPanel = document.getElementById('tabChapters');
    const summaryPanel = document.getElementById('tabSummary');
    expect(chaptersPanel).not.toHaveAttribute('hidden');
    expect(summaryPanel).toHaveAttribute('hidden');
  });

  it('clicking scenes tab shows scenes', async () => {
    render(<SummaryTabs {...baseProps} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Scenes' }));

    const scenesPanel = document.getElementById('tabScenes');
    expect(scenesPanel).not.toHaveAttribute('hidden');
    expect(screen.getByText('Opening scene')).toBeInTheDocument();
  });

  it('ArrowRight moves to next tab', async () => {
    render(<SummaryTabs {...baseProps} />);
    const summaryTab = screen.getByRole('tab', { name: 'Summary' });
    summaryTab.focus();
    fireEvent.keyDown(summaryTab, { key: 'ArrowRight' });

    expect(screen.getByRole('tab', { name: 'Chapters' })).toHaveAttribute('aria-selected', 'true');
  });

  it('ArrowLeft from first tab wraps to last', async () => {
    render(<SummaryTabs {...baseProps} />);
    const summaryTab = screen.getByRole('tab', { name: 'Summary' });
    summaryTab.focus();
    fireEvent.keyDown(summaryTab, { key: 'ArrowLeft' });

    expect(screen.getByRole('tab', { name: 'Scenes' })).toHaveAttribute('aria-selected', 'true');
  });

  it('Home goes to first tab', async () => {
    render(<SummaryTabs {...baseProps} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Scenes' }));
    const scenesTab = screen.getByRole('tab', { name: 'Scenes' });
    scenesTab.focus();
    fireEvent.keyDown(scenesTab, { key: 'Home' });

    expect(screen.getByRole('tab', { name: 'Summary' })).toHaveAttribute('aria-selected', 'true');
  });

  it('End goes to last tab', async () => {
    render(<SummaryTabs {...baseProps} />);
    const summaryTab = screen.getByRole('tab', { name: 'Summary' });
    summaryTab.focus();
    fireEvent.keyDown(summaryTab, { key: 'End' });

    expect(screen.getByRole('tab', { name: 'Scenes' })).toHaveAttribute('aria-selected', 'true');
  });

  it('clicking chapter calls onChapterClick', async () => {
    const onChapterClick = vi.fn();
    render(<SummaryTabs {...baseProps} onChapterClick={onChapterClick} />);
    await userEvent.click(screen.getByRole('tab', { name: 'Chapters' }));
    await userEvent.click(screen.getByText('Intro'));

    expect(onChapterClick).toHaveBeenCalledWith(0);
  });

  it('shows placeholder when no summary points', () => {
    render(<SummaryTabs {...baseProps} summaryPoints={[]} />);
    expect(screen.getByText('Load a job to read the summary.')).toBeInTheDocument();
  });

  it('shows placeholder when no chapters', () => {
    render(<SummaryTabs {...baseProps} chapters={[]} />);
    expect(screen.getByText('Load a job to browse chapters.')).toBeInTheDocument();
  });

  it('shows placeholder when no scenes', () => {
    render(<SummaryTabs {...baseProps} scenes={[]} />);
    expect(screen.getByText('Load a job to browse scenes.')).toBeInTheDocument();
  });
});

describe('SceneDescriptionPanel', () => {
  it('shows placeholder when no description', () => {
    render(
      <SceneDescriptionPanel
        description=""
        sceneId={null}
        time={null}
        ttsDuration={null}
        loading={false}
        playing={false}
        error={null}
      />,
    );
    expect(screen.getByText(/Load a processed job/)).toBeInTheDocument();
  });

  it('shows description text when provided', () => {
    render(
      <SceneDescriptionPanel
        description="A person walking through a door"
        sceneId={3}
        time={45.2}
        ttsDuration={2.5}
        loading={false}
        playing={false}
        error={null}
      />,
    );
    expect(screen.getByText('A person walking through a door')).toBeInTheDocument();
    expect(screen.getByText(/Scene 3/)).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(
      <SceneDescriptionPanel
        description=""
        sceneId={null}
        time={null}
        ttsDuration={null}
        loading
        playing={false}
        error={null}
      />,
    );
    expect(screen.getByText('Generating a scene description…')).toBeInTheDocument();
  });

  it('shows error with alert role', () => {
    render(
      <SceneDescriptionPanel
        description=""
        sceneId={null}
        time={null}
        ttsDuration={null}
        loading={false}
        playing={false}
        error="Network error"
      />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('Network error');
  });

  it('shows audio playing indicator', () => {
    render(
      <SceneDescriptionPanel
        description="A scene"
        sceneId={1}
        time={0}
        ttsDuration={3}
        loading={false}
        playing
        error={null}
      />,
    );
    expect(screen.getByText(/audio playing/)).toBeInTheDocument();
  });
});

describe('AccessibilityPanel', () => {
  const baseProps = {
    settings: defaultA11y,
    onChangeUiFontSize: vi.fn(),
    onChangeSubtitleFontSize: vi.fn(),
    onSetSubtitleMode: vi.fn(),
    onToggleDyslexiaFont: vi.fn(),
    onToggleWideSpacing: vi.fn(),
    onToggleHighContrast: vi.fn(),
  };

  it('toggle buttons have aria-pressed', () => {
    render(<AccessibilityPanel {...baseProps} />);
    expect(screen.getByRole('button', { name: 'Dyslexia font' })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: 'Wide spacing' })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByRole('button', { name: 'High contrast' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('toggle buttons update aria-pressed when active', () => {
    const settings = { ...defaultA11y, dyslexiaFont: true, highContrast: true };
    render(<AccessibilityPanel {...baseProps} settings={settings} />);
    expect(screen.getByRole('button', { name: 'Dyslexia font' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'High contrast' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: 'Wide spacing' })).toHaveAttribute('aria-pressed', 'false');
  });

  it('font size buttons have accessible names', () => {
    render(<AccessibilityPanel {...baseProps} />);
    expect(screen.getByRole('button', { name: 'Decrease interface text size' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reset interface text size' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Increase interface text size' })).toBeInTheDocument();
  });

  it('subtitle mode select is labelled', () => {
    render(<AccessibilityPanel {...baseProps} />);
    expect(screen.getByRole('combobox', { name: 'Subtitle display mode' })).toBeInTheDocument();
  });
});
