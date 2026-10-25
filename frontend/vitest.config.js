import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.dom.test.{js,jsx}'],
    setupFiles: ['./vitest.setup.js'],
    clearMocks: true,
    restoreMocks: true,
  },
});
