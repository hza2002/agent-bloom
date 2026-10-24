import { THEME_IDS } from './catalogue.js';
import { terminalPixels } from './pixels.js';

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function same(a, b) { return a.length === b.length && a.every((v, i) => v === b[i]); }
// Allow one subpixel of raster stepping, but reject disappearing shapes or colour layers.
function difference(a,b){
  const equal=(x,i,y,j)=>x[i+3]===y[j+3]&&(!x[i+3]||(x[i]===y[j]&&x[i+1]===y[j+1]&&x[i+2]===y[j+2]));
  const nearby=(x,i,y)=>{const px=(i/4)%192,py=Math.floor(i/4/192);for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const nx=px+dx,ny=py+dy;if(nx>=0&&nx<192&&ny>=0&&ny<128&&equal(x,i,y,(ny*192+nx)*4))return true;}return false;};
  let count=0;for(let i=0;i<a.length;i+=4)if(!equal(a,i,b,i)&&(!nearby(a,i,b)||!nearby(b,i,a)))count++;
  return count;
}
function nonempty(pixels) { return pixels.some((v, i) => i % 4 === 3 && v !== 0); }
function frame(theme, state, mode, mini = false) {
  const canvas = document.createElement('canvas');
  canvas.width = mini ? 18 : 192;
  canvas.height = mini ? 12 : 128;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  theme[mini ? 'mini' : 'render'](ctx, state);
  if (mini) ctx.clearRect(16, 0, 2, 4);
  terminalPixels(ctx, mode, !mini && theme.preserveColours===true);
  return ctx.getImageData(0, 0, canvas.width, canvas.height).data;
}

// Xbox's continuous-lighting experiment overwhelmed two-colour cells and shimmered in motion.
// This budget catches that regression; it is not a general aesthetic score.
export function checkXboxPalette(theme) {
  const canvas=document.createElement('canvas');canvas.width=192;canvas.height=128;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});
  let occupied=0,overloaded=0;
  for(const t of [.4,.8,1.2,1.6,2]){
    ctx.clearRect(0,0,192,128);theme.render(ctx,{phase:'intro',t,variant:'awaken',light:false});
    const data=ctx.getImageData(0,0,192,128).data;
    for(let y=0;y<128;y+=4)for(let x=0;x<192;x+=2){
      const colors=new Set();let transparent=false;
      for(let dy=0;dy<4;dy++)for(let dx=0;dx<2;dx++){
        const i=((y+dy)*192+x+dx)*4;
        if(!data[i+3])transparent=true;
        else colors.add((data[i]<<16)|(data[i+1]<<8)|data[i+2]);
      }
      if(colors.size){occupied++;if(colors.size>(transparent?1:2))overloaded++;}
    }
  }
  assert(occupied>0,'Xbox palette probe rendered no pixels');
  const ratio=overloaded/occupied;
  assert(ratio<.25,`Xbox shading overloads ${Math.round(ratio*100)}% of terminal cells (limit 25%)`);
  return {occupied,overloaded};
}

// Run from the browser, using the same raster conversion as the gallery.
// Passing these checks does not replace visual or actual-terminal acceptance.
export function checkTheme(theme) {
  if(theme.id==='xbox')checkXboxPalette(theme);
  assert(/^[a-z][a-z0-9-]*$/.test(theme.id), 'invalid theme id');
  assert(theme.footer.length === 3 && theme.footer.every(s => typeof s === 'string' && s.trim()), 'three footer lines required');
  assert(theme.sources.length > 0, 'source references required');
  assert(theme.variants.length > 0, 'at least one intro required');
  const keys = theme.variants.map(v => v.id);
  assert(new Set(keys).size === keys.length, 'duplicate animation ids');
  const badges = theme.badges?.map(b => b.id) ?? [undefined];
  assert(badges.length > 0 && new Set(badges).size === badges.length, 'empty or duplicate badge ids');
  let cases = 0;
  for (const light of [false, true]) for (const mode of ['octant', 'quadrant']) {
    const miniFrames = [];
    let baseline;
    for (const badge of badges) {
      const state = { light, badge, variant: keys[0], phase: 'still', t: 1 };
      const still = frame(theme, state, mode);
      assert(nonempty(still), `${mode}: empty settled artwork`);
      if (baseline) assert(same(still, baseline), 'badge selection changed large artwork');
      baseline = still;
      const mini = frame(theme, state, mode, true);
      assert(nonempty(mini), `${mode}: empty badge`);
      assert(!miniFrames.some(other => same(other, mini)), `${mode}: badge choices collapse to identical pixels`);
      miniFrames.push(mini);
      for (const variant of keys) {
        const s = { ...state, variant };
        assert(same(frame(theme, { ...s, phase: 'intro', t: 3 }, mode), still), `${variant}/${mode}: intro endpoint differs from static`);
        // The final hold must already be settled, not repaired by the t >= 3 branch.
        for(const t of [2.9, 2.99, 2.9999]) {
          assert(same(frame(theme,{...s,phase:'intro',t},mode),still), `${variant}/${mode}: visible snap before static handoff at ${t}s`);
        }
        if(badge===badges[0] && !light && mode==='octant') {
          // Probe both sides of timeline boundaries; allow tiny raster threshold changes.
          for(let tick=1;tick<=60;tick++) {
            const t=tick/20;
            const delta=difference(frame(theme,{...s,phase:'intro',t:t-.0001},mode),frame(theme,{...s,phase:'intro',t},mode));
            assert(delta<=400,`${variant}: large discontinuity at ${t}s (${delta} pixels)`);
          }
        }
        let changed = false;
        for (const t of [0, .25, .5, .75, 1, 1.5, 2, 2.5]) {
          const opening = frame(theme, { ...s, phase: 'intro', t }, mode);
          if (!same(opening, still)) changed = true;
        }
        assert(changed, `${variant}/${mode}: intro has no sampled motion`);
        assert(same(frame(theme, s, mode, true), mini), 'intro selection changed badge');
        cases++;
      }
      for (const t of [0, 1]) {
        assert(same(frame(theme, { ...state, phase: 'idle', t }, mode), still), `${mode}: idle endpoint differs from static`);
      }
      assert([.2, .4, .6, .8].some(t => !same(frame(theme, { ...state, phase: 'idle', t }, mode), still)), `${mode}: idle has no sampled motion`);
    }
  }
  return cases;
}

export async function runChecks() {
  const results = [];
  for (const id of THEME_IDS) {
    try {
      const theme = (await import(`./themes/${id}.js?check=${Date.now()}`)).default;
      assert(theme.id === id, 'catalogue and module id differ');
      results.push({ id, ok: true, cases: checkTheme(theme) });
    } catch (error) {
      results.push({ id, ok: false, error: error.message });
    }
  }
  return results;
}
