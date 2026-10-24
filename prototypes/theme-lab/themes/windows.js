import { panes } from './windows/xp-paths.js';
import { path, ease, clip, settled } from './drawing.js';
const COLORS=['#f35325','#81bc06','#05a6f0','#ffba08'];
function paint(ctx){panes.forEach((d,i)=>{ctx.fillStyle=COLORS[i];ctx.fill(path(d));});}
function flag(ctx){ctx.save();ctx.translate(30,-2);ctx.scale(5.5,5.5);paint(ctx);ctx.restore();}
function wave(ctx,light,p){
  const amplitude=5*Math.sin(Math.PI*p)**2;
  if(amplitude<.01){flag(ctx,light);return;}
  // Integer slice boundaries prevent half-pixel seams at the static handoff.
  for(let i=0;i<22;i++){ctx.save();ctx.translate(0,Math.round(Math.sin(i*.43+p*6)*amplitude));clip(ctx,30+i*6,0,6,128);flag(ctx,light);ctx.restore();}
}
export default {
  id:'windows',name:'Windows',subtitle:'Windows XP 四色旗 · 清晰曲面',accent:'#05a6f0',wordmark:'Windows',
  footer:['Welcome to Windows','A world of possibilities','Windows XP · Desktop · Start'],
  variants:[{id:'flag',label:'Flag · 旗面展开',description:'四色旗面展开，四块色面随波浪归位'}],
  badges:[{id:'window',label:'蓝色窗格'},{id:'colour',label:'四色方窗'}],
  sources:[{label:'经典旗帜矢量来源',url:'https://github.com/simple-icons/simple-icons/blob/9.0.0/icons/windowsxp.svg'},{label:'Windows XP 图形参考',url:'https://commons.wikimedia.org/wiki/File:Windows_logo_-_2002.svg'}],
  note:'采用 Windows XP 四色旗轮廓，按原始矢量四个子路径分别填色，去除旧版灰框与像素尾迹。小图使用现代蓝色方窗或四色方窗，与 XP 大图独立搭配；保留旗面展开节奏。文案为编辑提案。',
  render(ctx,s){if(settled(s)){flag(ctx,s.light);return;}
    if(s.phase==='idle'){wave(ctx,s.light,s.t);return;}
    const p=ease(s.t/2.2);ctx.save();clip(ctx,0,0,192*p,128);wave(ctx,s.light,p);ctx.restore();
  },
  mini(ctx,s){
    // A badge need not reproduce the waving hero: four aligned square panes read first.
    const colors=s.badge==='colour'?COLORS:Array(4).fill(s.light?'#0078d4':'#00a4ef');
    [[4,0],[10,0],[4,6],[10,6]].forEach(([x,y],i)=>{
      ctx.fillStyle=colors[i];ctx.fillRect(x,y,4,4);
    });
  }
};
