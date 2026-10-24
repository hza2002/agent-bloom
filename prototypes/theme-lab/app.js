import { terminalPixels } from './pixels.js';
import { THEME_IDS } from './catalogue.js';
import { createCopyMotion } from './copy-motion.js';
const ids = document.body.dataset.themes?.split(',') || THEME_IDS;
const $ = s => document.querySelector(s);
const states = [];
let light = false, precision = 'octant', raf = 0;
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const chosen = {};

function isPicked(s){return chosen[s.theme.id]?.variant===s.variant&&chosen[s.theme.id]?.badge===s.badge;}
function updateSelection(){
  const entries=states.filter(s=>chosen[s.theme.id]).map(s=>{
    const pick=chosen[s.theme.id],variant=s.theme.variants.find(v=>v.id===pick.variant);
    const badge=s.theme.badges?.find(b=>b.id===pick.badge);
    return `${s.theme.name} · ${variant.label}${badge?' · 小图 '+badge.label:''}`;
  });
  $('#chosen').textContent=entries.length?`已选：${entries.join(' / ')}。在对话中告诉我需要调整的部分即可。`:'可以分别选择大图方案、开场和 Claude 小图，选好后告诉我喜欢的搭配。';
}
function readableAccent(hex) {
  let rgb=hex.match(/[a-f0-9]{2}/gi).map(v=>parseInt(v,16));
  const luminance=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
  const bg=luminance(light?[255,254,249]:[13,16,17]);
  for(let n=0;n<35;n++){const lum=luminance(rgb);if((Math.max(lum,bg)+.05)/(Math.min(lum,bg)+.05)>=4.5)break;rgb=rgb.map(v=>light?Math.round(v*.9):Math.round(v+(255-v)*.1));}
  return `rgb(${rgb.join(',')})`;
}
function render(s){

  const state={phase:s.phase,t:s.t,variant:s.variant,badge:s.badge,light};
  s.ctx.resetTransform();s.ctx.clearRect(0,0,192,128);s.ctx.save();s.theme.render(s.ctx,state);s.ctx.restore();terminalPixels(s.ctx,precision,s.theme.preserveColours===true);
  if(s.appearance!==`${light}/${precision}/${s.badge}`){
    s.appearance=`${light}/${precision}/${s.badge}`;
    s.article.style.setProperty('--theme-accent',readableAccent(s.theme.accent));
    s.mctx.clearRect(0,0,18,12);s.mctx.save();s.theme.mini(s.mctx,state);s.mctx.restore();
    // Claude's first row has eight cells, the other rows have nine.
    s.mctx.clearRect(16,0,2,4);terminalPixels(s.mctx,precision);
  }
  s.copyMotion(state);
  s.slider.value=s.phase==='intro'?s.t:3;
  s.time.textContent=s.phase==='idle'?'待机':s.phase==='intro'?`${s.t.toFixed(1)}s`:'静态';
  s.pick.setAttribute('aria-pressed',String(isPicked(s)));
  s.pick.textContent=isPicked(s)?'已选这套搭配':s.theme.badges?'选这套搭配':'选这套开场';
}
function schedule(){if(!raf)raf=requestAnimationFrame(tick);}
function start(s,phase,now=performance.now()){
  s.phase=phase;s.t=0;s.started=now;s.lastFrame=-Infinity;s.running=true;
  if(reduced){s.phase='still';s.t=1;s.running=false;}
  render(s);schedule();
}
function stop(s){s.running=false;s.phase='still';s.t=1;render(s);}
function tick(now){raf=0;let active=false;
  for(const s of states){if(!s.running)continue;active=true;if(now-s.lastFrame<1000/30)continue;s.lastFrame=now;const duration=s.phase==='intro'?3000:1600;const p=Math.min(1,(now-s.started)/duration);s.t=s.phase==='intro'?p*3:p;if(p>=1){s.running=false;s.phase='still';s.t=1;}render(s);}
  if(active)schedule();
}
function card(theme,index){
  const article=document.createElement('article');article.className='theme';article.dataset.theme=theme.id;article.style.setProperty('--theme-accent',theme.accent);
  article.innerHTML=`<div class="theme-head"><span class="number">${String(index+1).padStart(2,'0')}</span><h2></h2><span class="subtitle"></span></div><div class="terminal"><div class="terminal-head"><canvas class="mini" width="18" height="12" role="img"></canvas><div class="terminal-title"></div><span class="terminal-meta">9 × 3 CELLS</span></div><div class="scene"><canvas class="art" width="192" height="128" role="img"></canvas><div class="lockup"><div class="wordmark"></div><div class="footer-copy"><strong></strong><span class="tagline"></span><span class="platform"></span></div></div></div><div class="terminal-prompt"><span>❯</span> 从这里开始</div></div><div class="badge-bar" role="group"></div><div class="variant-bar" role="group"></div><p class="variant-description"></p><div class="playback"><button class="replay">重播</button><button class="idle">待机</button><button class="pause">暂停</button><input type="range" min="0" max="3" step="0.01" value="3"><span class="time">静态</span></div><button class="pick" aria-pressed="false">选这套开场</button><details><summary>图形来源与设计说明</summary><p class="source-note"></p><div class="source-links"></div></details>`;
  article.querySelector('h2').textContent=theme.name;article.querySelector('.subtitle').textContent=theme.subtitle;
  article.querySelector('.wordmark').textContent=theme.wordmark;
  article.querySelector('.terminal-title').append(document.createTextNode(theme.name));
  const badgeCaption=document.createElement('span');badgeCaption.textContent='独立小图 · 实际尺寸预览';article.querySelector('.terminal-title').append(badgeCaption);
  ['strong','.tagline','.platform'].forEach((sel,i)=>article.querySelector('.footer-copy '+sel).textContent=theme.footer[i]);
  article.querySelector('.source-note').textContent=theme.note;
  for(const source of theme.sources){const a=document.createElement('a');a.textContent=source.label+' ↗';a.href=source.url;a.target='_blank';a.rel='noopener noreferrer';article.querySelector('.source-links').append(a);}
  const s={theme,article,ctx:article.querySelector('.art').getContext('2d',{willReadFrequently:true}),mctx:article.querySelector('.mini').getContext('2d',{willReadFrequently:true}),variant:theme.variants[0].id,badge:theme.badges?.[0].id,phase:'still',t:1,running:false,slider:article.querySelector('input'),time:article.querySelector('.time'),pick:article.querySelector('.pick')};
  s.copyMotion=createCopyMotion(article.querySelector('.lockup'));
  const badgeBar=article.querySelector('.badge-bar');
  if(theme.badges){
    badgeBar.setAttribute('aria-label',theme.name+' Claude 小图选择');
    const caption=document.createElement('span');caption.textContent='Claude 小图';badgeBar.append(caption);
    for(const badge of theme.badges){
      const b=document.createElement('button');b.textContent=badge.label;b.dataset.badge=badge.id;
      b.setAttribute('aria-pressed',String(badge.id===s.badge));
      b.onclick=()=>{s.badge=badge.id;badgeBar.querySelectorAll('button').forEach(el=>el.setAttribute('aria-pressed',String(el===b)));render(s);};
      badgeBar.append(b);
    }
  }else badgeBar.remove();
  if(theme.variants.length===1)article.querySelector('.variant-bar').hidden=true;
  for(const variant of theme.variants){const b=document.createElement('button');b.textContent=variant.label;b.dataset.variant=variant.id;b.setAttribute('aria-pressed',String(variant.id===s.variant));b.onclick=()=>{s.variant=variant.id;article.querySelectorAll('[data-variant]').forEach(el=>el.setAttribute('aria-pressed',String(el===b)));article.querySelector('.variant-description').textContent=variant.description;start(s,'intro');};article.querySelector('.variant-bar').append(b);}
  article.querySelector('.variant-bar').setAttribute('aria-label',theme.name+' 开场选择');
  article.querySelector('.variant-description').textContent=theme.variants[0].description;
  article.querySelector('.art').setAttribute('aria-label',theme.name+' 主图动画');article.querySelector('.mini').setAttribute('aria-label',theme.name+' 三行小图');
  for(const cls of ['replay','idle','pause'])article.querySelector('.'+cls).setAttribute('aria-label',theme.name+' '+article.querySelector('.'+cls).textContent);
  article.querySelector('.replay').onclick=()=>start(s,'intro');article.querySelector('.idle').onclick=()=>start(s,'idle');article.querySelector('.pause').onclick=()=>{s.running=false;};
  s.slider.setAttribute('aria-label',theme.name+' 开场进度');s.slider.oninput=()=>{s.running=false;s.phase='intro';s.t=Number(s.slider.value);render(s);};
  s.pick.onclick=()=>{chosen[theme.id]={variant:s.variant,badge:s.badge};render(s);updateSelection();};
  $('#gallery').append(article);states.push(s);render(s);
}
try{
  const modules=await Promise.all(ids.map(id=>import(`./themes/${id}.js`)));
  $('#loading').remove();modules.forEach((m,i)=>card(m.default,i));
}catch(error){$('#loading').textContent='主题载入失败，请刷新页面或检查本地服务';console.error(error);}
$('#play-all').onclick=()=>{const now=performance.now();states.forEach(s=>start(s,'intro',now));};
$('#idle-all').onclick=()=>{const now=performance.now();states.forEach(s=>start(s,'idle',now));};
$('#stop-all').onclick=()=>states.forEach(stop);
function applySettings(){
  light=$('#background').value==='light';precision=$('#precision').value;
  document.body.classList.toggle('light',light);
  document.body.classList.toggle('compact',$('#size').value==='compact');
  states.forEach(render);
}
for(const id of ['#background','#precision','#size']) $(id).onchange=applySettings;
// Browsers may restore form values on reload or back/forward navigation.
window.addEventListener('pageshow',applySettings);
applySettings();
if(reduced){$('#motion-note').textContent='已遵循系统的减少动态效果设置。可拖动进度条逐帧比较开场。';$('#auto-idle').disabled=true;}
setInterval(()=>{if($('#auto-idle').checked&&!document.hidden&&!reduced){const now=performance.now();states.filter(s=>!s.running).forEach(s=>start(s,'idle',now));}},8000);
document.addEventListener('visibilitychange',()=>{if(document.hidden){states.forEach(stop);cancelAnimationFrame(raf);raf=0;}});
