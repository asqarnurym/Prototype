import { describe, it, expect } from 'vitest';
import { getActiveSegmentExport, getWordClasses } from '../components/VideoPlayer/SubtitleOverlay';
import type { SubtitleSegment } from '../types/api';

function makeSegment(words: Array<{ word: string; start: number; end: number }>): SubtitleSegment {
  return {
    start: words[0]?.start ?? 0,
    end: words[words.length - 1]?.end ?? 0,
    text: words.map((w) => w.word).join(' '),
    words,
  };
}

describe('Subtitle matching', () => {
  const hello = { word: 'Hello', start: 0.0, end: 0.5 };
  const world = { word: 'world', start: 0.6, end: 1.2 };
  const segment = makeSegment([hello, world]);

  const one = { word: 'One', start: 0.0, end: 0.3 };
  const two = { word: 'Two', start: 0.4, end: 0.7 };
  const three = { word: 'Three', start: 0.8, end: 1.2 };
  const threeWordSegment = makeSegment([one, two, three]);

  describe('getActiveSegmentExport', () => {
    it('finds segment by time', () => {
      expect(getActiveSegmentExport([segment], 0.3)).toBe(segment);
      expect(getActiveSegmentExport([segment], 0.6)).toBe(segment);
      expect(getActiveSegmentExport([segment], 1.1)).toBe(segment);
    });

    it('returns null when time is outside segment range', () => {
      expect(getActiveSegmentExport([segment], -1)).toBeNull();
      expect(getActiveSegmentExport([segment], 5)).toBeNull();
    });

    it('returns null for empty segments array', () => {
      expect(getActiveSegmentExport([], 0.5)).toBeNull();
    });
  });

  describe('getWordClasses', () => {
    it('standard mode returns uniform class for all words', () => {
      const classes = getWordClasses(segment, 0.3, 'standard');
      expect(classes).toHaveLength(2);
      for (const c of classes) {
        expect(c).toContain('uniform');
      }
    });

    it('word mode marks current word', () => {
      const classes = getWordClasses(segment, 0.3, 'word');
      expect(classes[0]).toContain('current');
      expect(classes[1]).not.toContain('current');
    });

    it('word mode marks previous word (one behind current)', () => {
      const classes = getWordClasses(segment, 0.8, 'word');
      expect(classes[0]).toContain('previous');
      expect(classes[1]).toContain('current');
    });

    it('word mode marks spoken words (two or more behind current)', () => {
      // currentTime is past all three words → currentWordIndex = 2 (Three)
      // One (index 0) is index < 2 and not previous (index !== 1), so it's "spoken"
      // Two (index 1) is index === 2-1, so it's "previous"
      // Three (index 2) is "current"
      const classes = getWordClasses(threeWordSegment, 1.5, 'word');
      expect(classes[0]).toContain('spoken');
      expect(classes[1]).toContain('previous');
      expect(classes[2]).toContain('current');
    });

    it('handles empty words array', () => {
      const emptySeg: SubtitleSegment = { start: 0, end: 0, text: '', words: [] };
      const classes = getWordClasses(emptySeg, 0.5, 'word');
      expect(classes).toEqual([]);
    });
  });
});
