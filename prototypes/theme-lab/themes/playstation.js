// Silhouette: Simple Icons playstation.svg (CC0), vendored alongside this module.
// Classic colour placement and the 18x12 badge are original pixel adaptations;
// this is not an official four-colour SVG or an official boot sequence.
const P = 'M8.984 2.596v17.547l3.915 1.261V6.688c0-.69.304-1.151.794-.991.636.18.76.814.76 1.505v5.875c2.441 1.193 4.362-.002 4.362-3.152 0-3.237-1.126-4.675-4.438-5.827-1.307-.448-3.728-1.186-5.39-1.502z';
const RIGHT = 'M13.64 18.837l6.296-2.275c.715-.258.826-.625.246-.818-.586-.192-1.637-.139-2.357.123l-4.205 1.5V14.98l.24-.085s1.201-.42 2.913-.615c1.696-.18 3.785.03 5.437.661 1.848.601 2.04 1.472 1.576 2.072-.465.6-1.622 1.036-1.622 1.036l-8.544 3.107V18.86z';
const LEFT = 'M1.807 18.6c-1.9-.545-2.214-1.668-1.352-2.32.801-.586 2.16-1.052 2.16-1.052l5.615-2.013v2.313L4.205 17c-.705.271-.825.632-.239.826.586.195 1.637.15 2.343-.12L8.247 17v2.074c-.12.03-.256.044-.39.073-1.939.331-3.996.196-6.038-.479z';
let paths;
function getPaths() { return paths ||= [P, RIGHT, LEFT].map(d => new Path2D(d)); }
const LOGO = { red: '#ed1c24', yellow: '#fbc928', green: '#00a878', blue: '#1679c9' };
// Controller symbols have their own palette, distinct from the classic PS mark.
const BUTTONS = ['#42c5b4', '#f07480', '#6f9bf4', '#dc8abf'];
const clamp = t => Math.max(0, Math.min(1, t));
const smooth = t => { t = clamp(t); return t * t * (3 - 2 * t); };
function rectClip(ctx, x, y, w, h) { ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip(); }
function logoPart(ctx, index, dx = 0, dy = 0, bright = false) {
  ctx.save();
  // Source bounds 0..24 by 2.596..21.404; centre the actual mark, not its viewBox.
  ctx.translate(42 + dx, 10 + dy);
  ctx.scale(4.5, 4.5);
  const path = getPaths()[index];
  if (index === 0) {
    ctx.fillStyle = bright ? '#ff665a' : LOGO.red;
    ctx.fill(path);
  } else {
    ctx.clip(path);
    const bands = index === 1
      ? [[13, 17.8, LOGO.green], [17.8, 25, LOGO.blue]]
      : [[-1, 4.3, LOGO.yellow], [4.3, 9, LOGO.green]];
    for (const [a, b, color] of bands) {
      ctx.fillStyle = bright ? '#f9f4dc' : color;
      ctx.fillRect(a, 0, b - a, 25);
    }
  }
  ctx.restore();
}
function settled(ctx) {
  // The red upright P remains above the two pieces of the horizontal S.
  logoPart(ctx, 2); logoPart(ctx, 1); logoPart(ctx, 0);
}
function symbol(ctx, index, x, y, size = 10) {
  x = Math.round(x); y = Math.round(y); size = Math.max(4, Math.round(size));
  const h = Math.floor(size / 2);
  ctx.save(); ctx.translate(x, y);
  ctx.strokeStyle = BUTTONS[index]; ctx.fillStyle = BUTTONS[index];
  ctx.lineWidth = 2; ctx.lineJoin = 'miter'; ctx.lineCap = 'square';
  ctx.beginPath();
  if (index === 0) { ctx.moveTo(0, -h); ctx.lineTo(h, h); ctx.lineTo(-h, h); ctx.closePath(); }
  if (index === 1) { ctx.arc(0, 0, h, 0, Math.PI * 2); }
  if (index === 2) { ctx.moveTo(-h, -h); ctx.lineTo(h, h); ctx.moveTo(h, -h); ctx.lineTo(-h, h); }
  if (index === 3) { ctx.rect(-h, -h, h * 2, h * 2); }
  ctx.stroke(); ctx.restore();
}
function shapesIntro(ctx, t) {
  const reveal = smooth((t - 1.0) / 1.35);
  if (reveal > 0) {
    ctx.save(); rectClip(ctx, 96 - 60 * reveal, 16, 120 * reveal, 96);
    settled(ctx); ctx.restore();
  }
  if (t < 2.5) {
    const travel = smooth(t / 1.1);
    const exit = smooth((t - 1.6) / 0.9);
    for (let i = 0; i < 4; i++) {
      const a = -Math.PI / 2 + i * Math.PI / 2 + travel * Math.PI * 0.6;
      const radius = 61 - travel * 15 + exit * 26;
      const x = 96 + Math.cos(a) * radius;
      const y = 64 + Math.sin(a) * radius * 0.68;
      if (exit < 0.88) symbol(ctx, i, x, y, 13 - exit * 7);
    }
  }
}
function idle(ctx, t) {
  settled(ctx);
  if (t <= 0 || t >= 1) return;
  // A four-button relay: one obvious pulse per beat, with no continuous motion.
  const step = t * 4;
  const i = Math.min(3, Math.floor(step));
  const pulse = Math.sin((step - i) * Math.PI);
  const positions = [[37, 42], [158, 44], [158, 92], [35, 91]];
  if (pulse > 0.08) symbol(ctx, i, ...positions[i], 5 + 8 * pulse);
}
const MINI = [
  '......RRRR........',
  '......RRRRRR......',
  '......RR..RRR.....',
  '......RR..RRR.....',
  '......RR..RRR.....',
  '......RRRRRR......',
  '......RRRRR.GGG...',
  '....YYRR..GGGBBBB.',
  '..YYYYRR.GG..BBBB.',
  '.YYY..RR..BBBBB...',
  '..YYGGRRRBBBB.....',
  '....GGGRRRBB......',
];
// Dedicated 2x2 controller-button badge, aligned to separate 2x4 cells. Integer pixels preserve each counter;
// Circle, square and cross share a 4x4 ink box; the triangle is 5x4 for its geometry.
// No font glyphs or scaling of the large PS mark are involved.
const MINI_BUTTONS = [
  ['..#...', '.#.#..', '#...#.', '#####.'],
  ['..##..', '.#..#.', '.#..#.', '..##..'],
  ['.#..#.', '..##..', '..##..', '.#..#.'],
  ['.####.', '.#..#.', '.#..#.', '.####.'],
];
export default {
  id: 'playstation',
  name: 'PlayStation',
  subtitle: '经典四色 · 立体 PS · 四符号节拍',
  accent: '#477fe9',
  wordmark: 'PlayStation',
  footer: ['Play Has No Limits', '△ ○ × □', 'PlayStation · DualSense'],
  badges: [
    { id: 'buttons', label: '四按钮' },
    { id: 'ps', label: 'PS 标志' },
  ],
  headerIcon:"󰐔",
  variants: [
    { id: 'shapes', label: "Four-symbol interleave", description: '四个控制器符号绕行交错，从中心揭开经典四色 PS' }
  ],
  sources: [
    { label: '轮廓：Simple Icons · PlayStation（CC0）', url: 'https://github.com/simple-icons/simple-icons/blob/develop/icons/playstation.svg' },
    { label: '经典配色参考：官方 30 周年系列', url: 'https://www.youtube.com/watch?v=amdZnHooTkk' },
    { label: '品牌文案：Play Has No Limits', url: 'https://blog.playstation.com/2020/09/14/playstation-global-brand-spot-takes-gamers-beyond-the-edge-to-explore-new-worlds/' },
  ],
  note: '轮廓来自 Simple Icons，经典四色分区、小徽标与动画为像素适配；不是官方四色 SVG。正式接入需增加分区着色；短 header 建议 PS Claude / PS Codex。',
  render(ctx, state) {
    ctx.save();
    if (state.phase === 'still' || (state.phase === 'intro' && state.t >= 3)) settled(ctx);
    else if (state.phase === 'idle') idle(ctx, clamp(state.t));
    else shapesIntro(ctx, Math.max(0, state.t));
    ctx.restore();
  },
  mini(ctx, state) {
    ctx.save();
    if (state.badge === 'buttons') {
      MINI_BUTTONS.forEach((shape, index) => {
        const left = index % 2 === 0 ? 3 : 9;
        const top = index < 2 ? 0 : 6;
        ctx.fillStyle = BUTTONS[index];
        shape.forEach((row, y) => [...row].forEach((v, x) => {
          if (v === '#') ctx.fillRect(left + x, top + y, 1, 1);
        }));
      });
      ctx.restore();
      return;
    }
    const colors = { R: LOGO.red, Y: LOGO.yellow, G: LOGO.green, B: LOGO.blue };
    MINI.forEach((row, y) => [...row].forEach((v, x) => {
      if (colors[v]) { ctx.fillStyle = colors[v]; ctx.fillRect(x, y, 1, 1); }
    }));
    ctx.restore();
  },
};
