import { useRef, useEffect } from 'react';
import type { SubtitleSegment, SubtitleMode } from '../../types/api';

interface SubtitleOverlayProps {
  segments: SubtitleSegment[];
  currentTime: number;
  mode: SubtitleMode;
  visible: boolean;
}

function getActiveSegment(segments: SubtitleSegment[], currentTime: number): SubtitleSegment | null {
  for (const seg of segments) {
    if (currentTime >= seg.start - 0.05 && currentTime <= seg.end + 0.1) {
      return seg;
    }
  }
  return null;
}

export function getActiveSegmentExport(segments: SubtitleSegment[], currentTime: number) {
  return getActiveSegment(segments, currentTime);
}

export function getWordClasses(
  segment: SubtitleSegment,
  currentTime: number,
  mode: SubtitleMode,
): string[] {
  if (!segment.words || segment.words.length === 0) return [];
  if (mode === 'standard') {
    return segment.words.map(() => 'subtitle-word uniform');
  }

  let currentWordIndex = -1;
  for (let i = 0; i < segment.words.length; i++) {
    if (currentTime >= segment.words[i].start && currentTime < segment.words[i].end) {
      currentWordIndex = i;
      break;
    }
  }

  if (currentWordIndex === -1) {
    for (let i = segment.words.length - 1; i >= 0; i--) {
      if (currentTime >= segment.words[i].end) {
        currentWordIndex = i;
        break;
      }
    }
  }

  return segment.words.map((_, index) => {
    const classes = ['subtitle-word'];
    if (index === currentWordIndex) {
      classes.push('current');
    } else if (index === currentWordIndex - 1) {
      classes.push('previous');
    } else if (currentWordIndex !== -1 && index < currentWordIndex) {
      classes.push('spoken');
    }
    return classes.join(' ');
  });
}

export default function SubtitleOverlay({ segments, currentTime, mode, visible }: SubtitleOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    if (!visible || mode === 'off' || segments.length === 0) {
      el.classList.add('is-hidden');
      el.innerHTML = '';
      return;
    }

    const segment = getActiveSegment(segments, currentTime);
    if (!segment || !Array.isArray(segment.words) || segment.words.length === 0) {
      el.classList.add('is-hidden');
      el.innerHTML = '';
      return;
    }

    el.classList.remove('is-hidden');

    const wordClasses = getWordClasses(segment, currentTime, mode);
    const spans = segment.words
      .map(
        (w, i) =>
          `<span class="${wordClasses[i] || 'subtitle-word'}">${escapeHtml(w.word)} </span>`,
      )
      .join('');

    el.innerHTML = `<span class="subtitle-line">${spans}</span>`;
  }, [segments, currentTime, mode, visible]);

  return (
    <div
      ref={containerRef}
      className="subtitle-overlay is-hidden"
      aria-hidden="true"
    />
  );
}

function escapeHtml(value: string): string {
  const div = document.createElement('div');
  div.textContent = value;
  return div.innerHTML;
}
