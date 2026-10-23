import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  workers: 2,
  use: {baseURL: 'http://127.0.0.1:4321', browserName: 'chromium'},
  webServer: {
    command: 'npm run preview -- --port 4321 --ignore-lock',
    url: 'http://127.0.0.1:4321/agent-bloom/zh/',
    reuseExistingServer: !process.env.CI,
  },
});
