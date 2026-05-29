import { useState, useCallback, useEffect } from 'react';
import type { AccessibilitySettings, SubtitleMode } from '../types/api';
import {
  DEFAULT_A11Y_SETTINGS,
  UI_FONT_STEP,
  SUBTITLE_FONT_STEP,
  clampFontSize,
} from '../types/api';

const STORAGE_KEY = 'prototype-a11y-settings';

function loadSettings(): AccessibilitySettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        uiFontSize: clampFontSize(parsed.uiFontSize ?? DEFAULT_A11Y_SETTINGS.uiFontSize),
        subtitleFontSize: clampFontSize(parsed.subtitleFontSize ?? DEFAULT_A11Y_SETTINGS.subtitleFontSize),
        subtitleMode: parsed.subtitleMode ?? DEFAULT_A11Y_SETTINGS.subtitleMode,
        dyslexiaFont: Boolean(parsed.dyslexiaFont),
        wideSpacing: Boolean(parsed.wideSpacing),
        highContrast: Boolean(parsed.highContrast),
      };
    }
  } catch {
    // corrupted storage, fall through
  }
  return { ...DEFAULT_A11Y_SETTINGS };
}

function saveSettings(settings: AccessibilitySettings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // storage full or unavailable
  }
}

function applyBodyClasses(settings: AccessibilitySettings) {
  document.documentElement.classList.toggle('font-dyslexic', settings.dyslexiaFont);
  document.documentElement.classList.toggle('line-spacing-wide', settings.wideSpacing);
  document.documentElement.classList.toggle('high-contrast', settings.highContrast);
  document.documentElement.style.setProperty('--ui-scale', String(settings.uiFontSize / 100));
  document.documentElement.style.setProperty('--subtitle-scale', String(settings.subtitleFontSize / 100));
}

export function useAccessibilitySettings() {
  const [settings, setSettings] = useState<AccessibilitySettings>(loadSettings);

  useEffect(() => {
    applyBodyClasses(settings);
  }, [settings]);

  const update = useCallback((patch: Partial<AccessibilitySettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      saveSettings(next);
      return next;
    });
  }, []);

  const changeUiFontSize = useCallback(
    (direction: number) => {
      setSettings((prev) => {
        const next = {
          ...prev,
          uiFontSize: direction === 0 ? 100 : clampFontSize(prev.uiFontSize + direction * UI_FONT_STEP),
        };
        saveSettings(next);
        return next;
      });
    },
    [],
  );

  const changeSubtitleFontSize = useCallback(
    (direction: number) => {
      setSettings((prev) => {
        const next = {
          ...prev,
          subtitleFontSize: direction === 0 ? 100 : clampFontSize(prev.subtitleFontSize + direction * SUBTITLE_FONT_STEP),
        };
        saveSettings(next);
        return next;
      });
    },
    [],
  );

  const setSubtitleMode = useCallback(
    (mode: SubtitleMode) => update({ subtitleMode: mode }),
    [update],
  );

  const toggleDyslexiaFont = useCallback(
    () => update({ dyslexiaFont: !settings.dyslexiaFont }),
    [update, settings.dyslexiaFont],
  );

  const toggleWideSpacing = useCallback(
    () => update({ wideSpacing: !settings.wideSpacing }),
    [update, settings.wideSpacing],
  );

  const toggleHighContrast = useCallback(
    () => update({ highContrast: !settings.highContrast }),
    [update, settings.highContrast],
  );

  return {
    settings,
    changeUiFontSize,
    changeSubtitleFontSize,
    setSubtitleMode,
    toggleDyslexiaFont,
    toggleWideSpacing,
    toggleHighContrast,
  };
}
