import { useEffect, useRef } from 'react';

interface PlayerKeyboardCallbacks {
  onPlayPause: () => void;
  onSeekBack: (seconds: number) => void;
  onSeekForward: (seconds: number) => void;
  onMute: () => void;
  onFullscreen: () => void;
  onDescribe: () => void;
  onStopDescription: () => void;
}

export function usePlayerKeyboard(callbacks: PlayerKeyboardCallbacks) {
  const refs = useRef(callbacks);
  refs.current = callbacks;

  useEffect(() => {
    function handler(event: KeyboardEvent) {
      const tagName = (event.target as HTMLElement)?.tagName || '';
      if (tagName === 'INPUT' || tagName === 'SELECT' || tagName === 'TEXTAREA') {
        return;
      }

      const c = refs.current;

      switch (event.key) {
        case ' ':
        case 'k':
        case 'K':
          event.preventDefault();
          c.onPlayPause();
          break;
        case 'ArrowLeft':
          event.preventDefault();
          c.onSeekBack(5);
          break;
        case 'ArrowRight':
          event.preventDefault();
          c.onSeekForward(5);
          break;
        case 'j':
        case 'J':
          event.preventDefault();
          c.onSeekBack(10);
          break;
        case 'l':
        case 'L':
          event.preventDefault();
          c.onSeekForward(10);
          break;
        case 'm':
        case 'M':
          event.preventDefault();
          c.onMute();
          break;
        case 'f':
        case 'F':
          event.preventDefault();
          c.onFullscreen();
          break;
        case 'd':
        case 'D':
          event.preventDefault();
          c.onDescribe();
          break;
        case 's':
        case 'S':
        case 'Escape':
          event.preventDefault();
          c.onStopDescription();
          break;
      }
    }

    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);
}
