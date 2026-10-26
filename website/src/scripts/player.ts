import { createTerminalPlayer, type Clip } from './terminal-player';
import { appearance } from './appearance';
type Preview = {poster: string; background: number[]; intro: string; ambient: string; header: string; badge: string; foreground: number[]; muted: number[]; icon: string; iconColour: number[]};
type Theme = {id: string; name: string; apps: string[]; animations: {id: string; name: string}[]; previews: Record<string, Preview>};
type Catalogue = {themes: Theme[]; defaultTheme: string; ambientPeriod: number; ambientSweep: number; cols: number; rows: number; cellRatio: number; glyphs: string[]};

const root = document.querySelector<HTMLElement>('[data-showcase]');
if (root) {
  const catalogue: Catalogue = JSON.parse(root.dataset.catalogue!);
  const chinese = root.dataset.lang === 'zh';
  const choices = [...root.querySelectorAll<HTMLButtonElement>('[data-theme-id]')];
  const poster = root.querySelector<HTMLImageElement>('[data-poster]')!;
  const posterView = poster.closest('picture')!;
  const badge = root.querySelector<HTMLElement>('[data-badge-picture]')!;
  const stage = root.querySelector<HTMLElement>('.stage')!;
  const canvas = root.querySelector('canvas')!;
  const player = createTerminalPlayer(canvas, catalogue);
  const status = root.querySelector<HTMLElement>('[data-status]')!;
  const use = root.querySelector<HTMLAnchorElement>('[data-use]')!;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let controller: AbortController | null = null;
  let generation = 0;
  let selected = catalogue.themes.find(theme => theme.id === catalogue.defaultTheme)!;
  let animation = selected.animations[0].id;
  let timer = 0;
  let autoplay = !reduced.matches;
  let app = new URL(location.href).searchParams.get('app') || catalogue.themes[0].apps[0];
  let inView = true;
  let ambientClip: Clip | null = null;
  const variants = root.querySelector<HTMLElement>('[data-animations]')!;
  const replay = root.querySelector<HTMLButtonElement>('[data-replay]')!;
  const ambient = root.querySelector<HTMLButtonElement>('[data-ambient]')!;
  const apps = [...root.querySelectorAll<HTMLButtonElement>('[data-app-id]')];
  replay.hidden = ambient.hidden = false;
  let preview: Preview;

  function settle() {
    player.stop();
    clearTimeout(timer);
    controller?.abort();
    generation++;
    canvas.hidden = true;
    posterView.hidden = false;
  }

  function scheduleAmbient(delay = catalogue.ambientPeriod) {
    clearTimeout(timer);
    if (!autoplay || reduced.matches || document.hidden || !inView) return;
    timer = window.setTimeout(() => { void play('ambient'); }, delay);
  }

  async function play(phase: 'intro' | 'ambient', explicit = false) {
    if ((!explicit && (!autoplay || reduced.matches)) || document.hidden) return;
    const current = generation;
    controller = new AbortController();
    status.textContent = chinese ? '加载动效…' : 'Loading motion…';
    try {
      let data = phase === 'ambient' ? ambientClip : null;
      if (!data) {
        const response = await fetch(root!.dataset.media + preview[phase], {signal: controller.signal});
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        data = await response.json() as Clip;
      }
      if (current !== generation) return;
      const bounds = canvas.parentElement!.getBoundingClientRect();
      if (document.hidden || bounds.bottom <= 0 || bounds.top >= innerHeight) return;
      if (phase === 'ambient') ambientClip = data;
      posterView.hidden = true;
      canvas.hidden = false;
      canvas.dataset.phase = phase;
      status.textContent = phase === 'intro' ? (chinese ? '开场播放中' : 'Playing opening') : (chinese ? '待机播放中' : 'Playing idle motion');
      player.play(data, preview.background, () => {
        settle();
        status.textContent = autoplay && !reduced.matches ? (chinese ? '待机中' : 'Idle') : (chinese ? '静态预览' : 'Still preview');
        scheduleAmbient(phase === 'intro' ? catalogue.ambientPeriod : catalogue.ambientPeriod - catalogue.ambientSweep);
      });
    } catch {
      if (current !== generation) return;
      settle();
      status.textContent = chinese ? '暂时显示静态预览，点击主题可重试。' : 'Showing the still preview. Select the theme to retry.';
    }
  }

  async function select(theme: Theme, animate: boolean, updateURL = true, variant = theme.animations[0].id) {
    settle();
    selected = theme;
    app = theme.apps.includes(app) ? app : theme.apps[0];
    animation = theme.animations.some(item => item.id === variant) ? variant : theme.animations[0].id;
    ambientClip = null;
    const restoreFocus = variants.contains(document.activeElement);
    variants.replaceChildren();
    variants.hidden = theme.animations.length < 2;
    for (const item of theme.animations) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = item.name;
      button.dataset.animationId = item.id;
      button.setAttribute('aria-pressed', String(item.id === animation));
      button.addEventListener('click', event => {
        autoplay = !reduced.matches;
        void select(selected, event.detail !== 0, true, item.id);
      });
      variants.append(button);
    }
    if (restoreFocus) variants.querySelector<HTMLButtonElement>('[aria-pressed=true]')?.focus({preventScroll: true});
    const key = `${animation}/${app}`;
    const light = theme.previews[`${key}/light`];
    const dark = theme.previews[`${key}/dark`];
    preview = appearance() === 'dark' ? dark : light;
    poster.src = root!.dataset.media + light.poster;
    posterView.querySelector('source')!.srcset = root!.dataset.media + dark.poster;
    badge.querySelector('img')!.src = root!.dataset.media + light.badge;
    badge.querySelector('source')!.srcset = root!.dataset.media + dark.badge;
    root!.querySelector('[data-terminal-header]')!.textContent = preview.header;
    const icon = root!.querySelector<HTMLElement>('[data-codex-icon]')!;
    icon.textContent = preview.icon;
    icon.style.color = `rgb(${preview.iconColour.join(',')})`;
    const appName = app === 'codex' ? 'Codex' : 'Claude Code';
    stage.dataset.app = app;
    stage.setAttribute('aria-label', chinese ? `${appName} 中的主题预览` : `Theme preview in ${appName}`);
    root!.querySelector('[data-app-label]')!.textContent = appName;
    root!.querySelector('[data-terminal-prompt]')!.textContent = app === 'codex' ? '›' : '❯';
    apps.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.appId === app)));
    for (const [mode, data] of [['light', light], ['dark', dark]] as const) {
      stage.style.setProperty(`--terminal-${mode}`, `rgb(${data.background.join(',')})`);
      stage.style.setProperty(`--terminal-ink-${mode}`, `rgb(${data.foreground.join(',')})`);
      stage.style.setProperty(`--terminal-muted-${mode}`, `rgb(${data.muted.join(',')})`);
    }
    poster.alt = `${theme.name} · ${appName} · ${chinese ? '主题预览' : 'Theme preview'}`;
    canvas.setAttribute('aria-label', poster.alt);
    root!.querySelectorAll('[data-stage-name], [data-selected-name]').forEach(node => node.textContent = theme.name);
    choices.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.themeId === theme.id)));
    const guideURL = new URL(use.href);
    guideURL.search = new URLSearchParams({theme: theme.id, animation, app}).toString();
    use.href = guideURL.href;
    const languageLink = document.querySelector<HTMLAnchorElement>('[data-locale-link]')!;
    const languageURL = new URL(languageLink.href);
    languageURL.searchParams.set('theme', theme.id);
    languageURL.searchParams.set('animation', animation);
    languageURL.searchParams.set('app', app);
    languageLink.href = languageURL.href;
    status.textContent = '';
    if (updateURL) {
      const address = new URL(location.href);
      address.searchParams.set('theme', theme.id);
      if (app === 'claude') address.searchParams.delete('app');
      else address.searchParams.set('app', app);
      if (animation === theme.animations[0].id) address.searchParams.delete('animation');
      else address.searchParams.set('animation', animation);
      address.hash = '';
      history.replaceState(null, '', address);
    }
    if (animate && autoplay) {
      if (updateURL) revealArt();
      await play('intro');
    } else {
      scheduleAmbient();
    }
  }

  for (const button of choices) button.addEventListener('click', event => {
    const theme = catalogue.themes.find(item => item.id === button.dataset.themeId)!;
    const bounds = stage.getBoundingClientRect();
    if (bounds.top < 80 || bounds.top >= innerHeight) stage.scrollIntoView({block: 'start'});
    // Keyboard selection skips the entrance but retains the idle lifecycle.
    autoplay = !reduced.matches;
    void select(theme, event.detail !== 0);
  });
  document.addEventListener('bloom:appearance', () => {
    void select(selected, false, false, animation);
    scheduleAmbient();
  });
  function revealArt() {
    const art = canvas.parentElement!;
    const bounds = art.getBoundingClientRect();
    if (bounds.top < 0 || bounds.bottom > innerHeight) art.scrollIntoView({block: 'center', behavior: 'instant'});
  }
  function playRequested(phase: 'intro' | 'ambient') {
    settle();
    // Controls may be visible while the art is offscreen. Do not drop an explicit request.
    revealArt();
    void play(phase, true);
  }
  replay.addEventListener('click', () => playRequested('intro'));
  ambient.addEventListener('click', () => playRequested('ambient'));
  for (const button of apps) button.addEventListener('click', event => {
    app = button.dataset.appId!;
    autoplay = !reduced.matches;
    void select(selected, event.detail !== 0, true, animation);
  });
  const search = root.querySelector<HTMLInputElement>('[data-theme-search]');
  search?.addEventListener('input', () => {
    const query = search.value.trim().toLocaleLowerCase();
    for (const choice of choices) choice.hidden = !choice.dataset.searchName!.toLocaleLowerCase().includes(query);
    root.querySelector<HTMLElement>('[data-no-results]')!.hidden = choices.some(choice => !choice.hidden);
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) settle(); else scheduleAmbient(); });
  reduced.addEventListener('change', () => { autoplay = !reduced.matches; settle(); if (autoplay) scheduleAmbient(); });
  new IntersectionObserver(entries => {
    const wasVisible = inView;
    inView = entries[0].isIntersecting;
    if (!inView) settle();
    else if (!wasVisible) scheduleAmbient();
  }).observe(canvas.parentElement!);
  const id = new URL(location.href).searchParams.get('theme');
  selected = catalogue.themes.find(theme => theme.id === id) || selected;
  void select(selected, true, false, new URL(location.href).searchParams.get('animation') || selected.animations[0].id);
}
