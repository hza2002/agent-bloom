import { test, expect } from '@playwright/test';

test('keyboard selection retains automatic idle playback', async ({ page }) => {
  await page.goto('/agent-bloom/en/?theme=apple');
  await page.locator('[data-app-id=codex]').press('Enter');
  await expect(page.locator('[data-app-id=codex]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('canvas[data-phase=ambient]')).toBeVisible({timeout: 12000});
});


test('terminal caret blinks independently and respects reduced motion', async ({ page }) => {
  await page.goto('/agent-bloom/en/');
  const caret = page.locator('.terminal-caret');
  await expect.poll(() => caret.evaluate(node => getComputedStyle(node).animationName)).toBe('terminal-blink');
  const values = new Set<string>();
  for (let i = 0; i < 8; i++) {
    values.add(await caret.evaluate(node => getComputedStyle(node).opacity));
    await page.waitForTimeout(150);
  }
  expect(values.size).toBeGreaterThan(1);
  await page.emulateMedia({reducedMotion: 'reduce'});
  await expect.poll(() => caret.evaluate(node => getComputedStyle(node).animationName)).toBe('none');
});

test('guide keeps Codex selection through language switching', async ({ page }) => {
  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.goto('/agent-bloom/zh/?theme=apple&animation=constellation&app=codex');
  await page.locator('[data-use]').click();
  await expect(page.locator('[data-launch-command]')).toHaveText('agent-bloom --theme apple --animation constellation codex');
  await expect(page.locator('#agent-prompt')).toHaveValue(/constellation, codex/);
  await page.locator('[data-locale-link]').click();
  await expect(page.locator('[data-launch-command]')).toHaveText('agent-bloom --theme apple --animation constellation codex');
});

test('selected installation summary scrolls with the guide', async ({ page }) => {
  await page.goto('/agent-bloom/en/docs/get-started/?theme=apple&app=codex');
  const summary = page.locator('[data-install-selection]');
  await expect(summary).toBeVisible();
  await page.evaluate(() => scrollTo(0, 600));
  expect(await summary.evaluate(node => node.getBoundingClientRect().bottom)).toBeLessThan(0);
});
