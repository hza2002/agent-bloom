import { paths } from './amd/paths.js';
import { path, ease, clip, settled } from './drawing.js';
// Separate source components avoid painting translucent red edges over white.
const arrow='M18.324 9.137l1.559 1.56h2.556v2.557L24 14.814V9.137z M19.881 11.01l-1.604 1.603v2.25h2.246l1.604-1.607h-2.246z';
const letters=paths[0];
function mark(ctx,light=false,offset=0,reveal=1,dy=-offset,scale=1,split=0){
  ctx.save();ctx.translate(16,-16);ctx.scale(160/24,160/24);
  ctx.save();clip(ctx,0,0,18*reveal,24);ctx.fillStyle=light?'#272729':'#f1eee8';
  // Terminal row compensation: taller letter counters without widening the mark.
  ctx.translate(0,12);ctx.scale(1,1.22);ctx.translate(0,-12);
  ctx.fill(path(letters));ctx.restore();
  ctx.translate(offset,dy);ctx.translate(21.14,12);ctx.scale(scale,scale);ctx.translate(-21.14,-12);ctx.fillStyle='#ed3434';
  arrow.split(' M').forEach((d,i)=>{ctx.save();ctx.translate(i?-split:split,i?split:-split);ctx.fill(path(i?'M'+d:d));ctx.restore();});ctx.restore();
}
function idle(ctx,s){
  const t=s.t,charge=Math.sin(Math.PI*t)**2;
  const split=.3*charge,scale=1+.18*charge;
  mark(ctx,s.light,0,1,0,scale,split);
  // Energy follows each sharp L-shaped corner; the white AMD letters stay white.
  const routes=[[[18.6,9.55],[23.6,9.55],[23.6,14.3]],[[18.6,12.8],[18.6,14.45],[20.4,14.45]]];
  arrow.split(' M').forEach((d,i)=>{
    ctx.save();ctx.translate(16,-16);ctx.scale(160/24,160/24);
    ctx.translate(21.14,12);ctx.scale(scale,scale);ctx.translate(-21.14,-12);
    ctx.translate(i?-split:split,i?split:-split);ctx.clip(path(i?'M'+d:d));
    const p=ease((t-.12-i*.1)/.7),route=routes[i];
    ctx.beginPath();route.forEach(([x,y],j)=>j?ctx.lineTo(x,y):ctx.moveTo(x,y));
    ctx.setLineDash([2.6,40]);ctx.lineDashOffset=2.6-p*16;
    ctx.strokeStyle=s.light?'#8b1420':'#ffd0bd';ctx.lineWidth=.65*charge;
    if(charge>.001)ctx.stroke();ctx.restore();
  });
}
export default {
  id:'amd',name:'AMD',subtitle:'锐利折角 · 红色计算脉冲',accent:'#ed3434',wordmark:'AMD',
  footer:['together we advance','High-performance and adaptive computing','Ryzen · Radeon · EPYC'],
  headerIcon:"A",
  variants:[{id:'corners',label:"Red compute core",description:'红色折角展开为核心，四路数据汇入后扣合字标；待机箭头蓄力舒展，能量沿两个折角依次传递'}],
  sources:[{label:'AMD 官方战略与品牌发布',url:'https://www.amd.com/en/newsroom/press-releases/2022-6-9-amd-details-strategy-to-drive-next-phase-of-growth.html'},{label:'AMD 品牌故事与文案',url:'https://www.amd.com/en/corporate/amd-story.html'},{label:'字标矢量来源',url:'https://github.com/simple-icons/simple-icons/blob/9.0.0/icons/amd.svg'}],
  note:'采用 Simple Icons 收录的 AMD 字标与箭头。箭头强调红色是本主题配色改编；小图为独立像素适配。首句来自 AMD 品牌表达，第二行摘自官方计算战略表述，第三行为官方产品名称组合。',
  render(ctx,s){if(settled(s)){mark(ctx,s.light);return;}
    if(s.phase==='idle'){idle(ctx,s);return;}
    const t=s.t/2.65;
    const split=3.8*(1-ease(s.t/1.85));
    const dock=1-ease((s.t-.55)/1.75);
    // Separated arrow corners form a large central core, then dock with the wordmark.
    // Four diagonal data buses converge on the core. Packets travel, rather than blink.
    const energy=Math.sin(Math.PI*ease(s.t/2.55))**2;
    ctx.strokeStyle=s.light?'#a51d26':'#792129';ctx.lineWidth=2*energy;
    for(let lane=0;lane<4;lane++){
      const y=[18,30,98,110][lane],reach=(128-(lane%2)*12)*energy;
      if(energy>0){ctx.beginPath();ctx.moveTo(14,y);ctx.lineTo(14+reach,y);ctx.lineTo(14+reach+12*energy,y+(lane<2?1:-1)*12*energy);ctx.stroke();}
      for(let k=0;k<5;k++){
        const travel=(t*1.8+k*.19+lane*.13)%1;
        const size=Math.round(4*energy*Math.sin(Math.PI*travel));
        ctx.fillStyle=k===0?'#ffb2a6':'#ed3434';
        ctx.fillRect(Math.round(14+travel*reach),y-1,size*2,size);
      }
    }
    mark(ctx,s.light,-8*dock,ease((s.t-.95)/1.4),0,1+dock*.65,split);

  },
  mini(ctx){ctx.save();ctx.translate(4-18.277*1.75,-9.137*1.75);ctx.scale(1.75,1.75);ctx.fillStyle='#ed3434';ctx.fill(path(arrow));ctx.restore();}
};
