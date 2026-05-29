/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/process': 'http://127.0.0.1:8000',
      '/process-upload': 'http://127.0.0.1:8000',
      '/process_video': 'http://127.0.0.1:8000',
      '/jobs': 'http://127.0.0.1:8000',
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test-setup.ts',
    css: true,
    exclude: ['e2e/**', 'node_modules/**'],
  },
});
