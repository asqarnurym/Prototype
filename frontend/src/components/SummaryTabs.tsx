import { useState, useCallback } from 'react';
import type { Chapter, Scene } from '../types/api';
import { formatTime } from '../types/api';

type TabName = 'Summary' | 'Chapters' | 'Scenes';

interface SummaryTabsProps {
  summaryPoints: string[];
  chapters: Chapter[];
  scenes: Scene[];
  activeSceneId: number | null;
  onChapterClick: (time: number) => void;
  onSceneClick: (scene: Scene) => void;
}

function escapeHtml(value: string): string {
  const div = document.createElement('div');
  div.textContent = value;
  return div.innerHTML;
}

export default function SummaryTabs({
  summaryPoints,
  chapters,
  scenes,
  activeSceneId,
  onChapterClick,
  onSceneClick,
}: SummaryTabsProps) {
  const [activeTab, setActiveTab] = useState<TabName>('Summary');

  const handleTabKeyDown = useCallback(
    (event: React.KeyboardEvent, tabs: TabName[]) => {
      const currentIndex = tabs.indexOf(activeTab);
      let nextIndex = currentIndex;

      switch (event.key) {
        case 'ArrowRight':
          nextIndex = (currentIndex + 1) % tabs.length;
          break;
        case 'ArrowLeft':
          nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
          break;
        case 'Home':
          nextIndex = 0;
          break;
        case 'End':
          nextIndex = tabs.length - 1;
          break;
        default:
          return;
      }

      event.preventDefault();
      setActiveTab(tabs[nextIndex]);
    },
    [activeTab],
  );

  const tabs: TabName[] = ['Summary', 'Chapters', 'Scenes'];

  return (
    <section className="panel" aria-labelledby="navigationTitle">
      <h2 id="navigationTitle">Summary and navigation</h2>
      <div className="tab-bar" role="tablist" aria-label="Summary and navigation tabs">
        {tabs.map((tab) => (
          <button
            key={tab}
            id={`tabBtn${tab}`}
            type="button"
            className={`tab-btn${activeTab === tab ? ' is-active' : ''}`}
            role="tab"
            aria-selected={activeTab === tab}
            aria-controls={`tab${tab}`}
            tabIndex={activeTab === tab ? 0 : -1}
            onClick={() => setActiveTab(tab)}
            onKeyDown={(e) => handleTabKeyDown(e, tabs)}
          >
            {tab}
          </button>
        ))}
      </div>

      <div
        id="tabSummary"
        className={`tab-panel${activeTab === 'Summary' ? ' is-active' : ''}`}
        role="tabpanel"
        aria-labelledby="tabBtnSummary"
        hidden={activeTab !== 'Summary'}
      >
        <div className="reading-surface summary-content">
          {summaryPoints.length === 0 ? (
            <p className="summary-placeholder">Load a job to read the summary.</p>
          ) : (
            <ul>
              {summaryPoints.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div
        id="tabChapters"
        className={`tab-panel${activeTab === 'Chapters' ? ' is-active' : ''}`}
        role="tabpanel"
        aria-labelledby="tabBtnChapters"
        hidden={activeTab !== 'Chapters'}
      >
        <ul className="item-list">
          {chapters.length === 0 ? (
            <li className="list-placeholder">Load a job to browse chapters.</li>
          ) : (
            chapters.map((chapter, i) => (
              <li key={i}>
                <button
                  type="button"
                  className="item-card"
                  onClick={() => onChapterClick(chapter.time)}
                >
                  <span className="item-time">{formatTime(chapter.time || 0)}</span>
                  <span className="chapter-title">
                    {escapeHtml(chapter.title || 'Untitled chapter')}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>

      <div
        id="tabScenes"
        className={`tab-panel${activeTab === 'Scenes' ? ' is-active' : ''}`}
        role="tabpanel"
        aria-labelledby="tabBtnScenes"
        hidden={activeTab !== 'Scenes'}
      >
        <ul className="item-list">
          {scenes.length === 0 ? (
            <li className="list-placeholder">Load a job to browse scenes.</li>
          ) : (
            scenes.map((scene) => (
              <li key={scene.scene_id}>
                <button
                  type="button"
                  className={`item-card${activeSceneId === scene.scene_id ? ' is-active' : ''}`}
                  onClick={() => onSceneClick(scene)}
                >
                  <span className="item-time">{formatTime(scene.time || 0)}</span>
                  <span className="scene-desc">{escapeHtml(scene.description || '')}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </section>
  );
}
