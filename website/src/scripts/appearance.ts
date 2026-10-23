const system = matchMedia('(prefers-color-scheme: dark)');
let manual = false;
try { manual = ['light', 'dark'].includes(localStorage.getItem('bloom-appearance') || ''); } catch { /* Storage can be unavailable in private contexts. */ }
export function appearance(): 'light' | 'dark' {
  return document.documentElement.dataset.appearance === 'dark' ? 'dark' : 'light';
}
function apply(mode: 'light' | 'dark') {
  document.documentElement.dataset.appearance = mode;
  for (const source of document.querySelectorAll<HTMLSourceElement>('[data-appearance-picture] source')) {
    source.media = mode === 'dark' ? 'all' : 'not all';
  }
  const button = document.querySelector<HTMLButtonElement>('[data-appearance-toggle]');
  if (button) {
    button.hidden = false;
    button.setAttribute('aria-label', mode === 'dark' ? button.dataset.lightLabel! : button.dataset.darkLabel!);
  }
  document.dispatchEvent(new Event('bloom:appearance'));
}
document.querySelector('[data-appearance-toggle]')?.addEventListener('click', () => {
  const mode = appearance() === 'dark' ? 'light' : 'dark';
  manual = true;
  try { localStorage.setItem('bloom-appearance', mode); } catch { /* The current page still switches without persistence. */ }
  apply(mode);
});
system.addEventListener('change', () => { if (!manual) apply(system.matches ? 'dark' : 'light'); });
apply(document.documentElement.dataset.appearance === 'dark' ? 'dark' : 'light');
