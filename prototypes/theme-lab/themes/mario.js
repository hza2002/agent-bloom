// Independent pixel adaptations, drawn against Nintendo's public Mario references.
// This is not an official Nintendo asset package or an official animation.
const C = {
  r: '#e73535', d: '#b5212c', w: '#fff2d8', s: '#f0c795',
  e: '#352a2b', g: '#28ae54', h: '#70dd78', k: '#16733e',
  y: '#ffd14a', o: '#d99120', q: '#fff1bc',
  a: '#ff6054', b: '#603725', n: '#9c6038', f: '#d99560',
  v: '#fffaf0', c: '#d5dae4', u: '#2266d7', l: '#3484f4', z: '#174b9c',
};

// Original 32x32 pixel adaptation of Mario's red cap, moustache,
// blue overalls, white gloves and brown shoes. Not a ripped game sprite.
function makeMario() {
  const pixels = Array.from({ length: 32 }, () => Array(32).fill('.'));
  const rect = (x, y, w, h, c) => {
    for (let j = y; j < y + h; j++) for (let i = x; i < x + w; i++) pixels[j][i] = c;
  };
  // Cap, white emblem, hair, ear and broad nose.
  rect(10, 0, 12, 1, 'r'); rect(8, 1, 16, 1, 'r');
  rect(7, 2, 18, 2, 'r'); rect(7, 4, 21, 1, 'd');
  rect(9, 1, 5, 1, 'a'); rect(18, 1, 5, 3, 'v');
  for (const [x, y] of [[19, 1], [21, 1], [18, 2], [20, 2], [22, 2], [18, 3], [22, 3]]) rect(x, y, 1, 1, 'r');
  rect(8, 5, 8, 2, 'b'); rect(8, 7, 5, 5, 'b');
  rect(15, 5, 8, 1, 's'); rect(13, 6, 12, 5, 's');
  rect(11, 8, 3, 3, 's'); rect(10, 9, 2, 1, 'f');
  rect(21, 6, 2, 3, 'e'); rect(20, 5, 4, 1, 'b');
  rect(24, 8, 4, 3, 's'); rect(27, 9, 2, 2, 's');
  rect(18, 10, 6, 1, 'b'); rect(15, 11, 10, 2, 'b');
  rect(13, 13, 11, 1, 's'); rect(14, 14, 7, 1, 's');
  // Red shirt and arms under blue straps.
  rect(11, 15, 11, 1, 'r'); rect(8, 16, 17, 3, 'r');
  rect(6, 18, 5, 3, 'd'); rect(23, 18, 4, 3, 'd');
  rect(9, 18, 15, 3, 'r'); rect(11, 16, 3, 5, 'u');
  rect(20, 16, 3, 5, 'u'); rect(10, 20, 14, 5, 'u');
  rect(11, 20, 10, 4, 'l'); rect(21, 20, 3, 5, 'z');
  rect(12, 20, 2, 2, 'y'); rect(20, 20, 2, 2, 'y');
  // Separate gloves and two trouser legs keep the silhouette readable.
  rect(4, 19, 4, 1, 'v'); rect(3, 20, 6, 3, 'v');
  rect(4, 23, 4, 1, 'c'); rect(7, 20, 2, 2, 'c');
  rect(26, 19, 3, 1, 'v'); rect(25, 20, 5, 3, 'v');
  rect(26, 23, 3, 1, 'c'); rect(25, 21, 1, 2, 'c');
  rect(10, 25, 5, 4, 'u'); rect(19, 25, 5, 4, 'u');
  rect(13, 25, 2, 4, 'z'); rect(22, 25, 2, 4, 'z');
  rect(9, 29, 6, 1, 'b'); rect(7, 30, 9, 2, 'b');
  rect(19, 29, 6, 1, 'b'); rect(18, 30, 10, 2, 'b');
  rect(8, 30, 5, 1, 'n'); rect(20, 30, 5, 1, 'n');
  return pixels.map(row => row.join(''));
}
const MARIO = makeMario();
// A dedicated raised-glove pose keeps the gesture readable without rotating pixels.
const CELEBRATE = MARIO.map(row => [...row]);
for(let y=18;y<24;y++)for(let x=25;x<30;x++)CELEBRATE[y][x]='.';
for(let y=14;y<20;y++)for(let x=24;x<27;x++)CELEBRATE[y][x]='r';
for(let y=10;y<15;y++)for(let x=25;x<29;x++)CELEBRATE[y][x]='v';
const RAISED_MARIO = CELEBRATE.map(row => row.join(''));


// A separate 18x12 red M cap, not a downscaled full character.
function makeCap() {
  const pixels = Array.from({ length: 12 }, () => Array(18).fill('.'));
  const spans = [[6, 12], [4, 14], [3, 15], [2, 16], [2, 16], [2, 16],
    [2, 16], [2, 16], [1, 17], [0, 18], [2, 16], [4, 14]];
  spans.forEach(([a, b], y) => { for (let x = a; x < b; x++) pixels[y][x] = y >= 10 ? 'd' : 'r'; });
  for (let y = 2; y <= 8; y++) {
    const margin = y === 2 || y === 8 ? 1 : 0;
    for (let x = 6 + margin; x < 13 - margin; x++) pixels[y][x] = 'v';
  }
  const emblem = ['r...r', 'rr.rr', 'r.r.r', 'r...r', 'r...r'];
  emblem.forEach((line, y) => { for (let x = 0; x < 5; x++) if (line[x] === 'r') pixels[y + 3][x + 7] = 'r'; });
  return pixels.map(row => row.join(''));
}
const CAP = makeCap();

// Hand-drawn 18x12 Super Mushroom, with a wide cap and separate face.
const MUSHROOM_BADGE = [
  '......rrrrrr......',
  '....rrrwwrrwrr....',
  '...rrrwwwrrwwwr...',
  '..rrrrwwwrrwwwrr..',
  '.rwrrrrrrrrrrrrwr.',
  '.wwwrrrrwwrrrrwww.',
  'rwwwrrrwwwwrrrwwwr',
  'rrrrrrrwwwwrrrrrrr',
  '.ddddssssssssdddd.',
  '....ssessssess....',
  '....ssessssess....',
  '.....ssssssss.....',
];

const BLOCK_BADGE = [
  '...oooooooooooo...',
  '...oyyyyyyyyyyo...',
  '...oyyqqqqqyyyo...',
  '...oyqqyyyqqyyo...',
  '...oyyyyyyqqyyo...',
  '...oyyyyyqqyyyo...',
  '...oyyyyqqyyyyo...',
  '...oyyyyqqyyyyo...',
  '...oyyyyyyyyyyo...',
  '...oyyyyqqyyyyo...',
  '...oyyyyyyyyyyo...',
  '...oooooooooooo...',
];

const clamp = t => Math.max(0, Math.min(1, t));
const smooth = t => { t = clamp(t); return t * t * (3 - 2 * t); };
const lerp = (a, b, t) => a + (b - a) * t;

function sprite(ctx, pixels, cx, cy, sx, sy = sx) {
  const width = pixels[0].length;
  const height = pixels.length;
  const left = cx - width * sx / 2;
  const top = cy - height * sy / 2;
  pixels.forEach((line, y) => {
    for (let x = 0; x < width; x++) {
      const color = C[line[x]];
      if (!color) continue;
      const x0 = Math.round(left + x * sx);
      const y0 = Math.round(top + y * sy);
      const x1 = Math.round(left + (x + 1) * sx);
      const y1 = Math.round(top + (y + 1) * sy);
      ctx.fillStyle = color;
      ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    }
  });
}

function mario(ctx, cx = 96, cy = 64, sx = 1, sy = sx) {
  sprite(ctx, MARIO, cx, cy, 3 * sx, 3 * sy);
}

function block(ctx, cx, cy, size, assemble = 1) {
  if (size <= 0) return;
  const unit = size / 12;
  const pattern = [
    'oooooooooooo', 'oyyyyyyyyyyo', 'oyyqqqqqyyyo',
    'oyqqyyyqqyyo', 'oyyyyyyqqyyo', 'oyyyyyqqyyyo',
    'oyyyyqqyyyyo', 'oyyyyqqyyyyo', 'oyyyyyyyyyyo',
    'oyyyyqqyyyyo', 'oyyyyyyyyyyo', 'oooooooooooo',
  ];
  const visible = Math.ceil(clamp(assemble) * pattern.length);
  sprite(ctx, pattern.map((line, i) => i < visible ? line : '.'.repeat(12)), cx, cy, unit);
  if (size > 20) {
    ctx.fillStyle = C.o;
    for (const dx of [-1, 1]) for (const dy of [-1, 1]) {
      ctx.fillRect(Math.round(cx + dx * size * .34 - unit / 2),
        Math.round(cy + dy * size * .34 - unit / 2), Math.ceil(unit), Math.ceil(unit));
    }
  }
}

function coin(ctx, cx, cy, turn) {
  const width = Math.max(2, Math.round(8 * Math.abs(Math.cos(turn * Math.PI * 2))));
  ctx.fillStyle = C.o;
  ctx.fillRect(Math.round(cx - width / 2), Math.round(cy - 7), width, 14);
  ctx.fillStyle = C.y;
  ctx.fillRect(Math.round(cx - width / 2), Math.round(cy - 5), Math.max(1, width - 2), 10);
  if (width > 4) {
    ctx.fillStyle = C.q;
    ctx.fillRect(Math.round(cx - width / 2 + 2), Math.round(cy - 4), 2, 7);
  }
}

function pipe(ctx, top, height) {
  if (height < 1) return;
  const y = Math.round(top), h = Math.round(height);
  ctx.fillStyle = C.k;
  ctx.fillRect(69, y, 54, h);
  ctx.fillStyle = C.g;
  ctx.fillRect(73, y, 44, h);
  ctx.fillStyle = C.h;
  ctx.fillRect(77, y, 7, h);
  const rim = Math.min(12, h);
  ctx.fillStyle = C.k;
  ctx.fillRect(63, y, 66, rim);
  ctx.fillStyle = C.g;
  ctx.fillRect(66, y + Math.min(2, rim), 60, Math.max(0, rim - 4));
  ctx.fillStyle = C.h;
  ctx.fillRect(70, y + Math.min(2, rim), 9, Math.max(0, rim - 4));
}

function powerup(ctx, t) {
  const grow = smooth((t - 1.06) / 1.16);
  const scale = lerp(.78, 1, grow);
  const jumpP = clamp((t - .27) / .78);
  const jump = t >= .27 && t <= 1.05 ? 18 * Math.sin(jumpP * Math.PI) : 0;
  mario(ctx, lerp(92, 96, grow), lerp(81, 64, grow) - jump, scale);
  if (t < 1.66) {
    const exit = smooth((t - 1.08) / .58);
    const hit = t >= .53 && t < .89 ? Math.sin((t - .53) / .36 * Math.PI) * 5 : 0;
    block(ctx, 126, 26 - hit, 26 * (1 - exit), smooth(t / .22));
  }
  if (t > .62 && t < 1.42) {
    const p = (t - .62) / .8;
    coin(ctx, 147 + 9 * p, 27 - 9 * Math.sin(p * Math.PI), p * 2);
  }
}

function pipeIntro(ctx, t) {
  const rise = smooth((t - .35) / 1.38);
  const retract = smooth((t - 1.62) / .66);
  const pipeTop = lerp(81, 118, retract);
  ctx.save();
  ctx.beginPath();
  ctx.rect(8, 8, 176, Math.max(0, pipeTop - 8));
  ctx.clip();
  if (t > .35) mario(ctx, 96, lerp(111, 64, rise), lerp(.58, 1, rise));
  ctx.restore();
  const opening = smooth(t / .3);
  pipe(ctx, pipeTop + (1 - opening) * 26, 31 * opening * (1 - retract));
  if (t >= 2.28) mario(ctx);
}

function idle(ctx, t) {
  if (t <= 0 || t >= 1) { mario(ctx); return; }
  const raised=t>.16&&t<.8;
  const jump=t>.34&&t<.7?8*Math.sin((t-.34)/.36*Math.PI):0;
  const anticipation=t<.16?2*Math.sin(t/.16*Math.PI):0;
  const cy=64+2*Math.round((anticipation-jump)/2);
  sprite(ctx,raised?RAISED_MARIO:MARIO,96,cy,3);
  if(t>.18&&t<.78){
    const p=(t-.18)/.6;
    const pop=smooth(p/.15)*smooth((1-p)/.15);
    ctx.save();ctx.translate(139,52-30*Math.sin(p*Math.PI));ctx.scale(pop,pop);
    coin(ctx,0,0,p*1.5);ctx.restore();
  }
}

export default {
  id: 'mario',
  name: 'Mario',
  subtitle: '红帽、胡子与背带裤，Mario 本人的像素冒险',
  accent: '#ef4444',
  wordmark: 'MARIO',
  footer: ['Let’s-a go', 'Power up', 'Mushroom Kingdom · Nintendo'],
  headerIcon:"M",
  productionVariants:["pipe"],
  variants: [
    { id: 'pipe', label: "Warp pipe", description: 'Mario 从绿色水管升起，水管收回后落定；待机举手抛金币、轻跳庆祝' },
    { id: 'powerup', label: 'Power Up · 顶砖变大', description: 'Mario 本人跳起顶砖，金币跃出，落地后长成完整像素人物' },
  ],
  badges: [{ id: 'mushroom', label: '超级蘑菇' }, { id: 'cap', label: 'M 红帽' }, { id: 'block', label: '问号砖' }],
  sources: [
    { label: 'Nintendo 官方 Mario 人物介绍', url: 'https://www.nintendo.com/jp/character/mario/en/index.html' },
    { label: 'Nintendo 官方道具图稿参考', url: 'https://play.nintendo.com/documents/Super_Mario_window_printables.pdf' },
    { label: 'Mario 官方角色与道具', url: 'https://www.nintendo.com/jp/character/mario/en/history/new_smb_u/index.html' },
    { label: 'Nintendo 官方 Let’s-a go 用语', url: 'https://www.nintendo.com/us/whatsnew/bring-home-the-super-mario-bros-movie/' },
  ],
  note: 'Mario 本人与超级蘑菇、M 红帽、问号砖均为参考 Nintendo 图稿独立重绘的像素适配，不是官方 sprite 或授权素材包；动画为原创提案。大图和小标独立选择。Let’s-a go 为角色用语，三行文案是本主题编排。',
  render(ctx, state) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(8, 8, 176, 112);
    ctx.clip();
    if (state.phase === 'idle') idle(ctx, clamp(state.t));
    else if (state.phase === 'intro' && state.t < 3) {
      const t = Math.max(0, state.t);
      if (state.variant === 'powerup') powerup(ctx, t);
      else pipeIntro(ctx, t);
    } else mario(ctx);
    ctx.restore();
  },
  mini(ctx, state) {
    // Geometry and palette stay stable in both terminal palettes.
    const pixels = state.badge === 'block' ? BLOCK_BADGE : state.badge === 'cap' ? CAP : MUSHROOM_BADGE;
    sprite(ctx, pixels, 9, 6, 1);
  },
};
