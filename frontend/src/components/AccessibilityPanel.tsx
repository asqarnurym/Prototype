import type { AccessibilitySettings, SubtitleMode } from '../types/api';

interface AccessibilityPanelProps {
  settings: AccessibilitySettings;
  onChangeUiFontSize: (direction: number) => void;
  onChangeSubtitleFontSize: (direction: number) => void;
  onSetSubtitleMode: (mode: SubtitleMode) => void;
  onToggleDyslexiaFont: () => void;
  onToggleWideSpacing: () => void;
  onToggleHighContrast: () => void;
}

export default function AccessibilityPanel({
  settings,
  onChangeUiFontSize,
  onChangeSubtitleFontSize,
  onSetSubtitleMode,
  onToggleDyslexiaFont,
  onToggleWideSpacing,
  onToggleHighContrast,
}: AccessibilityPanelProps) {
  return (
    <section className="panel" aria-labelledby="settingsTitle">
      <h2 id="settingsTitle">Accessibility settings</h2>
      <div className="settings-grid">
        <div className="setting-card">
          <div className="setting-head">
            <span className="setting-title">UI text size</span>
            <span className="setting-value">{settings.uiFontSize}%</span>
          </div>
          <div className="button-cluster">
            <button
              type="button"
              className="a11y-btn"
              onClick={() => onChangeUiFontSize(-1)}
              aria-label="Decrease interface text size"
            >
              A-
            </button>
            <button
              type="button"
              className="a11y-btn"
              onClick={() => onChangeUiFontSize(0)}
              aria-label="Reset interface text size"
            >
              A
            </button>
            <button
              type="button"
              className="a11y-btn"
              onClick={() => onChangeUiFontSize(1)}
              aria-label="Increase interface text size"
            >
              A+
            </button>
          </div>
        </div>

        <div className="setting-card">
          <div className="setting-head">
            <span className="setting-title">Subtitle size</span>
            <span className="setting-value">{settings.subtitleFontSize}%</span>
          </div>
          <div className="button-cluster">
            <button
              type="button"
              className="a11y-btn"
              onClick={() => onChangeSubtitleFontSize(-1)}
              aria-label="Decrease subtitle size"
            >
              A-
            </button>
            <button
              type="button"
              className="a11y-btn"
              onClick={() => onChangeSubtitleFontSize(0)}
              aria-label="Reset subtitle size"
            >
              A
            </button>
            <button
              type="button"
              className="a11y-btn"
              onClick={() => onChangeSubtitleFontSize(1)}
              aria-label="Increase subtitle size"
            >
              A+
            </button>
          </div>
        </div>

        <div className="setting-card">
          <div className="setting-head">
            <span className="setting-title">Subtitle mode</span>
          </div>
          <select
            id="subtitleModeSelect"
            value={settings.subtitleMode}
            onChange={(e) => onSetSubtitleMode(e.target.value as SubtitleMode)}
            aria-label="Subtitle display mode"
          >
            <option value="word">Word-by-word</option>
            <option value="standard">Standard</option>
            <option value="off">Off</option>
          </select>
        </div>

        <div className="setting-card">
          <div className="setting-head">
            <span className="setting-title">Reading support</span>
          </div>
          <div className="button-cluster">
            <button
              type="button"
              className={`a11y-btn${settings.dyslexiaFont ? ' is-active' : ''}`}
              onClick={onToggleDyslexiaFont}
              aria-pressed={settings.dyslexiaFont}
            >
              Dyslexia font
            </button>
            <button
              type="button"
              className={`a11y-btn${settings.wideSpacing ? ' is-active' : ''}`}
              onClick={onToggleWideSpacing}
              aria-pressed={settings.wideSpacing}
            >
              Wide spacing
            </button>
            <button
              type="button"
              className={`a11y-btn${settings.highContrast ? ' is-active' : ''}`}
              onClick={onToggleHighContrast}
              aria-pressed={settings.highContrast}
            >
              High contrast
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
