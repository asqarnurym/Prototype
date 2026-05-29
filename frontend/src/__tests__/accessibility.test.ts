import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAccessibilitySettings } from '../hooks/useAccessibilitySettings';

// Instead of trying to mock a getter/setter which is tricky in jsdom,
// we mock setProperty on documentElement and verify localStorage directly.

describe('useAccessibilitySettings', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.className = '';
  });

  it('returns default values initially', () => {
    const { result } = renderHook(() => useAccessibilitySettings());
    expect(result.current.settings.uiFontSize).toBe(100);
    expect(result.current.settings.subtitleFontSize).toBe(100);
    expect(result.current.settings.subtitleMode).toBe('word');
    expect(result.current.settings.dyslexiaFont).toBe(false);
    expect(result.current.settings.wideSpacing).toBe(false);
    expect(result.current.settings.highContrast).toBe(false);
  });

  it('persists settings to localStorage', () => {
    const { result } = renderHook(() => useAccessibilitySettings());

    act(() => {
      result.current.toggleDyslexiaFont();
    });

    const stored = JSON.parse(localStorage.getItem('prototype-a11y-settings')!);
    expect(stored.dyslexiaFont).toBe(true);
  });

  it('loads settings from localStorage', () => {
    localStorage.setItem(
      'prototype-a11y-settings',
      JSON.stringify({ uiFontSize: 115, subtitleFontSize: 130, subtitleMode: 'standard', dyslexiaFont: true, wideSpacing: false, highContrast: true }),
    );

    const { result } = renderHook(() => useAccessibilitySettings());
    expect(result.current.settings.uiFontSize).toBe(115);
    expect(result.current.settings.subtitleMode).toBe('standard');
    expect(result.current.settings.dyslexiaFont).toBe(true);
    expect(result.current.settings.highContrast).toBe(true);
  });

  it('clamps font sizes on load', () => {
    localStorage.setItem(
      'prototype-a11y-settings',
      JSON.stringify({ uiFontSize: 50, subtitleFontSize: 200 }),
    );

    const { result } = renderHook(() => useAccessibilitySettings());
    expect(result.current.settings.uiFontSize).toBe(70);
    expect(result.current.settings.subtitleFontSize).toBe(160);
  });

  it('changeUiFontSize with direction 0 resets to 100', () => {
    const { result } = renderHook(() => useAccessibilitySettings());

    act(() => {
      result.current.changeUiFontSize(1);
    });
    expect(result.current.settings.uiFontSize).toBe(115);

    act(() => {
      result.current.changeUiFontSize(0);
    });
    expect(result.current.settings.uiFontSize).toBe(100);
  });

  it('changeSubtitleFontSize respects bounds', () => {
    const { result } = renderHook(() => useAccessibilitySettings());

    act(() => {
      result.current.changeSubtitleFontSize(-3);
    });
    expect(result.current.settings.subtitleFontSize).toBe(70);

    act(() => {
      result.current.changeSubtitleFontSize(10);
    });
    expect(result.current.settings.subtitleFontSize).toBe(160);
  });

  it('setSubtitleMode changes mode', () => {
    const { result } = renderHook(() => useAccessibilitySettings());

    act(() => {
      result.current.setSubtitleMode('off');
    });
    expect(result.current.settings.subtitleMode).toBe('off');

    act(() => {
      result.current.setSubtitleMode('standard');
    });
    expect(result.current.settings.subtitleMode).toBe('standard');
  });

  it('toggle functions flip boolean values', () => {
    const { result } = renderHook(() => useAccessibilitySettings());

    act(() => {
      result.current.toggleWideSpacing();
    });
    expect(result.current.settings.wideSpacing).toBe(true);

    act(() => {
      result.current.toggleWideSpacing();
    });
    expect(result.current.settings.wideSpacing).toBe(false);
  });
});
