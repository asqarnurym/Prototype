import { describe, it, expect } from 'vitest';
import { formatTime } from '../types/api';

describe('formatTime', () => {
  it('formats 0 as 00:00', () => {
    expect(formatTime(0)).toBe('00:00');
  });

  it('formats under 1 minute', () => {
    expect(formatTime(45)).toBe('00:45');
    expect(formatTime(5)).toBe('00:05');
  });

  it('formats between 1 minute and 1 hour', () => {
    expect(formatTime(65)).toBe('01:05');
    expect(formatTime(599)).toBe('09:59');
    expect(formatTime(600)).toBe('10:00');
  });

  it('formats over 1 hour', () => {
    expect(formatTime(3661)).toBe('01:01:01');
    expect(formatTime(7200)).toBe('02:00:00');
    expect(formatTime(45296)).toBe('12:34:56');
  });

  it('handles NaN', () => {
    expect(formatTime(NaN)).toBe('00:00');
  });

  it('handles negative numbers', () => {
    expect(formatTime(-10)).toBe('00:00');
  });

  it('handles Infinity', () => {
    expect(formatTime(Infinity)).toBe('00:00');
  });
});
