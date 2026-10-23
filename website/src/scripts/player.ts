type Cell = [string, [number, number, number], boolean];
type Clip = {tokens: Cell[]; frames: [number, number[]][]};
import { appearance } from './appearance';
type Preview = {poster: string; background: number[]; intro: string; ambient: string; header: string; badge: string; foreground: number[]; muted: number[]};
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
  const context = canvas.getContext('2d')!;
  const status = root.querySelector<HTMLElement>('[data-status]')!;
  const install = root.querySelector<HTMLElement>('#install')!;
  const use = root.querySelector<HTMLAnchorElement>('[data-use]')!;
  const prompt = root.querySelector<HTMLTextAreaElement>('#agent-prompt')!;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const glyphs = new Map(Array.from(catalogue.glyphs).map((char, bits) => [char, bits]));
  const cellWidth = 8, cellHeight = cellWidth * catalogue.cellRatio;
  canvas.width = catalogue.cols * cellWidth;
  canvas.height = Math.ceil(catalogue.rows * cellHeight);
  let controller: AbortController | null = null;
  let request = 0, generation = 0;
  let selected = catalogue.themes.find(theme => theme.id === catalogue.defaultTheme)!;
  let animation = selected.animations[0].id;
  let timer = 0;
  let paused = reduced.matches;
  let inView = true;
  let ambientClip: Clip | null = null;
  const motion = root.querySelector<HTMLButtonElement>('[data-motion]')!;
  const variants = root.querySelector<HTMLElement>('[data-animations]')!;
  motion.hidden = false;
  let clip: Clip | null = null;
  let preview: Preview;

  function settle() {
    cancelAnimationFrame(request);
    clearTimeout(timer);
    controller?.abort();
    generation++;
    canvas.hidden = true;
    posterView.hidden = false;
    clip = null;
  }

  function draw(position: number, token: number) {
    const x = position % catalogue.cols * cellWidth;
    const y = Math.floor(position / catalogue.cols) * cellHeight;
    context.fillStyle = `rgb(${preview.background.join(',')})`;
    context.fillRect(x, Math.round(y), cellWidth, Math.round(y + cellHeight) - Math.round(y));
    if (token === -1) return;
    const [char, rgb, bold] = clip!.tokens[token];
    context.fillStyle = `rgb(${rgb.join(',')})`;
    const bits = glyphs.get(char);
    if (bits === undefined) {
      context.font = `${bold ? 'bold ' : ''}13px monospace`;
      context.fillText(char, x, y + cellHeight * .78);
      return;
    }
    for (let bit = 0; bit < 8; bit++) {
      if (!(bits & (1 << bit))) continue;
      const top = Math.round(y + Math.floor(bit / 2) * cellHeight / 4);
      const bottom = Math.round(y + (Math.floor(bit / 2) + 1) * cellHeight / 4);
      context.fillRect(x + bit % 2 * 4, top, 4, bottom - top);
    }
  }

  function motionLabel() {
    motion.hidden = reduced.matches;
    motion.textContent = paused ? (chinese ? '播放动效' : 'Play motion') : (chinese ? '暂停动效' : 'Pause motion');
    motion.setAttribute('aria-pressed', String(!paused));
  }

  function scheduleAmbient(delay = catalogue.ambientPeriod) {
    clearTimeout(timer);
    if (paused || reduced.matches || document.hidden || !inView) return;
    timer = window.setTimeout(() => { void play('ambient'); }, delay);
  }

  async function play(phase: 'intro' | 'ambient') {
    if (paused || reduced.matches || document.hidden) return;
    const current = generation;
    controller = new AbortController();
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
      clip = data;
      context.fillStyle = `rgb(${preview.background.join(',')})`;
      context.fillRect(0, 0, canvas.width, canvas.height);
      posterView.hidden = true;
      canvas.hidden = false;
      canvas.dataset.phase = phase;
      const start = performance.now();
      let frame = 0;
      const tick = (now: number) => {
        if (current !== generation || !clip) return;
        while (frame < clip.frames.length && clip.frames[frame][0] <= now - start) {
          const changes = clip.frames[frame++][1];
          for (let index = 0; index < changes.length; index += 2) draw(changes[index], changes[index + 1]);
        }
        if (frame === clip.frames.length) {
          settle();
          scheduleAmbient(phase === 'intro' ? catalogue.ambientPeriod : catalogue.ambientPeriod - catalogue.ambientSweep);
          return;
        }
        request = requestAnimationFrame(tick);
      };
      request = requestAnimationFrame(tick);
    } catch {
      if (current !== generation) return;
      settle();
      status.textContent = chinese ? '暂时显示静态预览，点击主题可重试。' : 'Showing the still preview. Select the theme to retry.';
    }
  }

  async function select(theme: Theme, animate: boolean, updateURL = true, variant = theme.animations[0].id) {
    settle();
    selected = theme;
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
        paused = event.detail === 0 || reduced.matches;
        motionLabel();
        void select(selected, !paused, true, item.id);
      });
      variants.append(button);
    }
    if (restoreFocus) variants.querySelector<HTMLButtonElement>('[aria-pressed=true]')?.focus({preventScroll: true});
    motionLabel();
    const key = `${animation}/${theme.apps[0]}`;
    const light = theme.previews[`${key}/light`];
    const dark = theme.previews[`${key}/dark`];
    preview = appearance() === 'dark' ? dark : light;
    poster.src = root!.dataset.media + light.poster;
    posterView.querySelector('source')!.srcset = root!.dataset.media + dark.poster;
    badge.querySelector('img')!.src = root!.dataset.media + light.badge;
    badge.querySelector('source')!.srcset = root!.dataset.media + dark.badge;
    root!.querySelector('[data-terminal-header]')!.textContent = preview.header;
    for (const [mode, data] of [['light', light], ['dark', dark]] as const) {
      stage.style.setProperty(`--terminal-${mode}`, `rgb(${data.background.join(',')})`);
      stage.style.setProperty(`--terminal-ink-${mode}`, `rgb(${data.foreground.join(',')})`);
      stage.style.setProperty(`--terminal-muted-${mode}`, `rgb(${data.muted.join(',')})`);
    }
    poster.alt = `${theme.name} · ${chinese ? '主题预览' : 'Theme preview'}`;
    canvas.setAttribute('aria-label', poster.alt);
    root!.querySelectorAll('[data-stage-name], [data-selected-name]').forEach(node => node.textContent = theme.name);
    choices.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.themeId === theme.id)));
    root!.querySelector('[data-launch-command]')!.textContent = `agent-bloom --theme ${theme.id} --animation ${animation} ${theme.apps[0]}`;
    prompt.value = `${prompt.dataset.basePrompt}\n${chinese ? '我选择的主题是' : 'My chosen theme is'} ${theme.name} (${theme.id}), --animation ${animation}.`;
    const languageLink = document.querySelector<HTMLAnchorElement>('[data-locale-link]')!;
    const languageURL = new URL(languageLink.href);
    languageURL.searchParams.set('theme', theme.id);
    languageURL.searchParams.set('animation', animation);
    languageLink.href = languageURL.href;
    status.textContent = '';
    if (updateURL) {
      const address = new URL(location.href);
      address.searchParams.set('theme', theme.id);
      if (animation === theme.animations[0].id) address.searchParams.delete('animation');
      else address.searchParams.set('animation', animation);
      address.hash = '';
      history.replaceState(null, '', address);
    }
    if (animate && !paused) await play('intro');
  }

  for (const button of choices) button.addEventListener('click', event => {
    const theme = catalogue.themes.find(item => item.id === button.dataset.themeId)!;
    const bounds = stage.getBoundingClientRect();
    if (bounds.top < 80 || bounds.top >= innerHeight) stage.scrollIntoView({block: 'start'});
    // Keyboard browsing and reduced-motion preferences keep the preview still.
    paused = event.detail === 0 || reduced.matches;
    void select(theme, !paused);
  });
  document.addEventListener('bloom:appearance', () => {
    void select(selected, false, false, animation);
    scheduleAmbient();
  });
  motion.addEventListener('click', () => {
    paused = !paused;
    settle();
    motionLabel();
    if (!paused) void play('ambient');
  });
  const search = root.querySelector<HTMLInputElement>('[data-theme-search]');
  search?.addEventListener('input', () => {
    const query = search.value.trim().toLocaleLowerCase();
    for (const choice of choices) choice.hidden = !choice.dataset.searchName!.toLocaleLowerCase().includes(query);
    root.querySelector<HTMLElement>('[data-no-results]')!.hidden = choices.some(choice => !choice.hidden);
  });
  install.hidden = location.hash !== '#install';
  use.setAttribute('aria-expanded', String(!install.hidden));
  use.setAttribute('aria-controls', 'install');
  use.addEventListener('click', () => {
    install.hidden = false;
    use.setAttribute('aria-expanded', 'true');
    settle();
  });
  document.addEventListener('visibilitychange', () => { if (document.hidden) settle(); else scheduleAmbient(); });
  reduced.addEventListener('change', () => { paused = reduced.matches; settle(); motionLabel(); if (!paused) scheduleAmbient(); });
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
