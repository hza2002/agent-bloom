import { test, expect } from '@playwright/test';

for (const lang of ['zh', 'en']) {
  for (const width of [320, 375, 1280]) {
    test(`${lang} single-page layout at ${width}px`, async ({ page }, testInfo) => {
      await page.emulateMedia({reducedMotion: 'reduce'});
      await page.setViewportSize({width, height: 900});
      const errors: string[] = [];
      const clips: string[] = [];
      page.on('pageerror', error => errors.push(error.message));
      page.on('request', request => {
        if (/generated\/media\/.*\.json/.test(request.url())) clips.push(request.url());
      });
      await page.goto(`/agent-bloom/${lang}/`);
      await expect(page.locator('[data-poster]')).toBeVisible();
      await expect(page.locator('select')).toHaveCount(0);
      await expect(page.locator('#install')).toBeHidden();
      await page.locator('[data-theme-id=apple]').click();
      await expect(page.locator('[data-selected-name]')).toHaveText('apple');
      await expect(page).toHaveURL(new RegExp(`/${lang}/\\?theme=apple$`));
      await page.evaluate(() => scrollTo(0, 0));
      if (width !== 320) await page.screenshot({path: testInfo.outputPath('showcase.png'), fullPage: true});
      await page.locator('[data-use]').click();
      await expect(page.locator('#install')).toBeVisible();
      await expect(page.locator('[data-launch-command]')).toContainText('--theme apple');
      await expect(page.locator('#agent-prompt')).toHaveValue(/apple \(apple\)/);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      if (width !== 320) await page.screenshot({path: testInfo.outputPath('install.png'), fullPage: true});
      for (const slug of ['get-started', 'usage', 'reference']) {
        await page.goto(`/agent-bloom/${lang}/docs/${slug}/`);
        await expect(page.locator('h1')).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      }
      expect(clips).toEqual([]);
      expect(errors).toEqual([]);
    });
  }
}

test('only the selected entrance loads, plays once and settles', async ({ page }) => {
  const clips: string[] = [];
  page.on('request', request => {
    if (/generated\/media\/.*\.json/.test(request.url())) clips.push(request.url());
  });
  await page.goto('/agent-bloom/en/?theme=apple');
  await expect(page.locator('[data-selected-name]')).toHaveText('apple');
  await expect(page.locator('canvas')).toBeVisible();
  await expect(page.locator('canvas')).toBeHidden({timeout: 8000});
  await expect(page.locator('[data-poster]')).toBeVisible();
  expect(clips).toHaveLength(1);
  await page.locator('[data-theme-id=huawei]').click();
  await expect(page.locator('canvas')).toBeVisible();
  expect(clips).toHaveLength(2);
  await page.locator('[data-use]').click();
  await expect(page.locator('canvas')).toBeHidden();
});

test('a failed entrance still lets the user choose and install', async ({ page }) => {
  await page.route('**/generated/media/*.json', route => route.abort());
  await page.goto('/agent-bloom/en/');
  await expect(page.locator('[data-status]')).toContainText('still preview');
  await expect(page.locator('[data-poster]')).toBeVisible();
  await page.locator('[data-theme-id=apple]').click();
  await expect(page.locator('[data-selected-name]')).toHaveText('apple');
  await page.locator('[data-use]').click();
  await expect(page.locator('[data-launch-command]')).toContainText('--theme apple');
});

test('agent instructions carry the selected theme and canonical guide', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.goto('/agent-bloom/en/?theme=apple#install');
  await page.locator('[data-copy=agent-prompt]').click();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain('/raw/docs/user/en/get-started.md');
  expect(copied).toContain('apple (apple)');
  const source = await page.request.get('/agent-bloom/raw/docs/user/en/get-started.md');
  const quickstart = (await source.text()).split('<!-- quickstart:start -->')[1].split('<!-- quickstart:end -->')[0].trim().replace(/^```sh\n|\n```$/g, '');
  await expect(page.locator('#install-command')).toHaveText(quickstart);
});

test('old detail links open the selected theme in the single page', async ({ page }) => {
  await page.goto('/agent-bloom/en/themes/apple/');
  await expect(page).toHaveURL(/\/en\/\?theme=apple$/);
  await expect(page.locator('[data-selected-name]')).toHaveText('apple');
});

test('without JavaScript the default preview and install remain readable', async ({ browser }) => {
  const context = await browser.newContext({javaScriptEnabled: false});
  const page = await context.newPage();
  await page.goto('http://127.0.0.1:4321/agent-bloom/zh/');
  await expect(page.locator('[data-poster]')).toBeVisible();
  await expect(page.locator('#install-command')).toBeVisible();
  await context.close();
});

test('system appearance, manual preference and production palettes stay together', async ({ page }, testInfo) => {
  await page.emulateMedia({colorScheme: 'dark', reducedMotion: 'reduce'});
  await page.goto('/agent-bloom/en/?theme=apple');
  await expect(page.locator('html')).toHaveAttribute('data-appearance', 'dark');
  await expect(page.locator('[data-terminal-header]')).toHaveText('AppleClaude');
  const darkPoster = await page.locator('[data-poster]').evaluate((image: HTMLImageElement) => image.currentSrc);
  await page.screenshot({path: testInfo.outputPath('dark-desktop.png'), fullPage: true});
  await page.locator('[data-appearance-toggle]').click();
  await expect(page.locator('html')).toHaveAttribute('data-appearance', 'light');
  await expect.poll(() => page.locator('[data-poster]').evaluate((image: HTMLImageElement) => image.currentSrc)).not.toBe(darkPoster);
  await expect.poll(() => page.locator('.stage').evaluate(node => getComputedStyle(node).backgroundColor)).toBe('rgb(250, 250, 250)');
  await page.screenshot({path: testInfo.outputPath('light-desktop.png'), fullPage: true});
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-appearance', 'light');
  await page.setViewportSize({width: 375, height: 900});
  await page.locator('[data-appearance-toggle]').click();
  await page.screenshot({path: testInfo.outputPath('dark-mobile.png'), fullPage: true});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('a large catalogue wraps and filters without downloading every animation', async ({ page }) => {
  // Exercise the production gallery and controller with test-only catalogue records.
  const html = await (await page.request.get('/agent-bloom/en/')).text();
  const stressHTML = await page.evaluate(source => {
    const document = new DOMParser().parseFromString(source, 'text/html');
    const root = document.querySelector<HTMLElement>('[data-showcase]')!;
    const data = JSON.parse(root.dataset.catalogue!);
    const grid = document.querySelector('.theme-grid')!;
    const original = grid.querySelector('button')!;
    const template = data.themes[0];
    grid.replaceChildren();
    data.themes = Array.from({length: 40}, (_, index) => {
      const theme = {...template, id: `fixture-${index}`, name: `Fixture ${index}`};
      const button = original.cloneNode(true) as HTMLButtonElement;
      button.dataset.themeId = theme.id;
      button.dataset.searchName = `${theme.name} ${theme.id}`;
      button.querySelector('span')!.textContent = theme.name;
      grid.append(button);
      return theme;
    });
    data.defaultTheme = data.themes[0].id;
    root.dataset.catalogue = JSON.stringify(data);
    const label = document.createElement('label');
    label.className = 'theme-search';
    label.innerHTML = '<input type="search" data-theme-search aria-label="Search themes" />';
    document.querySelector('.gallery-heading')!.append(label);
    return '<!doctype html>' + document.documentElement.outerHTML;
  }, html);
  await page.route(/\/en\/\?stress$/, route => route.fulfill({body: stressHTML, contentType: 'text/html'}));
  await page.emulateMedia({reducedMotion: 'reduce'});
  await page.setViewportSize({width: 375, height: 900});
  const clips: string[] = [];
  page.on('request', request => { if (/\/media\/.*\.json/.test(request.url())) clips.push(request.url()); });
  await page.goto('/agent-bloom/en/?stress');
  await expect(page.locator('[data-theme-id]')).toHaveCount(40);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('[data-theme-search]').fill('Fixture 39');
  await expect(page.locator('[data-theme-id]:visible')).toHaveCount(1);
  await page.locator('[data-theme-id=fixture-39]').click();
  await expect(page.locator('[data-selected-name]')).toHaveText('Fixture 39');
  await page.locator('[data-theme-search]').fill('no-match');
  await expect(page.locator('[data-no-results]')).toBeVisible();
  expect(clips).toEqual([]);
});


test('all Apple entrances update selection and lead into production idle motion', async ({ page }, testInfo) => {
  test.setTimeout(40000);
  const clips: string[] = [];
  page.on('request', request => { if (/generated\/media\/.*\.json/.test(request.url())) clips.push(request.url()); });
  await page.goto('/agent-bloom/en/?theme=apple');
  await expect(page.locator('[data-animation-id]')).toHaveCount(2);
  await page.locator('[data-animation-id=constellation]').click();
  await expect(page).toHaveURL(/animation=constellation/);
  await expect(page.locator('[data-launch-command]')).toContainText('--animation constellation');
  await expect(page.locator('#agent-prompt')).toHaveValue(/--animation constellation/);
  await expect(page.locator('canvas[data-phase=intro]')).toBeVisible();
  await expect(page.locator('canvas')).toBeHidden({timeout: 8000});
  const beforeIdle = clips.length;
  await expect(page.locator('canvas[data-phase=ambient]')).toBeVisible({timeout: 12000});
  expect(clips).toHaveLength(beforeIdle + 1);
  await expect(page.locator('canvas')).toBeHidden({timeout: 3000});
  await expect(page.locator('canvas[data-phase=ambient]')).toBeVisible({timeout: 8000});
  expect(clips).toHaveLength(beforeIdle + 1);
  await page.locator('[data-motion]').click();
  await expect(page.locator('canvas')).toBeHidden();
  await expect(page.locator('[data-motion]')).toHaveText('Play motion');
  await page.evaluate(() => scrollTo(0, 0));
  await page.screenshot({path: testInfo.outputPath('entrance-controls.png'), fullPage: true});
  await page.locator('[data-motion]').click();
  await expect(page.locator('canvas[data-phase=ambient]')).toBeVisible();
  await page.reload();
  await expect(page.locator('[data-animation-id=constellation]')).toHaveAttribute('aria-pressed', 'true');
});
