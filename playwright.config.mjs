// Marco 6: configuração do Playwright (E2E). Dependência só de desenvolvimento;
// o site publicado continua sem dependências.
import {defineConfig, devices} from '@playwright/test';

const PORTA = 4173;

export default defineConfig({
  testDir: 'tests/e2e',
  testMatch: '*.spec.mjs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  outputDir: 'evidencias/playwright-resultados',
  reporter: [['list'], ['html', {outputFolder: 'evidencias/relatorio-html', open: 'never'}]],
  use: {
    baseURL: `http://127.0.0.1:${PORTA}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  projects: [
    {name: 'desktop', use: {...devices['Desktop Chrome'], viewport: {width: 1280, height: 800}}},
    {name: 'mobile', use: {...devices['Desktop Chrome'], viewport: {width: 390, height: 844}, isMobile: true, hasTouch: true}}
  ],
  // Até o build do M7, serve a raiz do projeto; no M7 trocar para `public`.
  webServer: {
    command: 'node scripts/servidor-local.mjs .',
    url: `http://127.0.0.1:${PORTA}/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000
  }
});
