// Small drawing primitives shared by the internal prototypes, not an animation engine.
export const clamp = t => Math.max(0, Math.min(1, t));
export const ease = t => { t = clamp(t); return t * t * (3 - 2 * t); };
const cache = new Map();
export function path(d) { if (!cache.has(d)) cache.set(d, new Path2D(d)); return cache.get(d); }
export function clip(ctx, x, y, w, h) { ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip(); }
export function grid(ctx, rows, colors) {
  rows.forEach((row, y) => [...row].forEach((key, x) => {
    if (colors[key]) { ctx.fillStyle = colors[key]; ctx.fillRect(x, y, 1, 1); }
  }));
}
export function line(ctx, points, color, width = 2) {
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'butt';
  ctx.beginPath(); points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)); ctx.stroke();
}
export function settled(state) {
  return state.phase === 'still' || (state.phase === 'intro' && state.t >= 3)
    || (state.phase === 'idle' && (state.t <= 0 || state.t >= 1));
}
