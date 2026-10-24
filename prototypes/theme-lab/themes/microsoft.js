import { ease, settled } from './drawing.js';
const C=['#f25022','#7fba00','#00a4ef','#ffb900'];
const XY=[[52,20],[98,20],[52,66],[98,66]];
const SIZE=42;

// All panes share one continuous deformation field, so gaps survive the morph.
// At bend=0 the exact same points form the standard square Microsoft mark.
function point(x,y,bend,phase){
  const u=(x-96)/44,v=(y-64)/44;
  return [x-12*v*bend,y+9*bend*Math.sin(u*Math.PI*.85+phase)];
}
function tiles(ctx,bend=0,phase=0,offsets=null){
  XY.forEach(([x,y],i)=>{
    const [dx,dy]=offsets?.[i]||[0,0];
    ctx.fillStyle=C[i];
    if(bend===0){ctx.fillRect(x+dx,y+dy,SIZE,SIZE);return;}
    ctx.beginPath();
    const edge=(ax,ay,bx,by,first=false)=>{
      for(let j=0;j<=24;j++){
        const t=j/24,[px,py]=point(ax+(bx-ax)*t,ay+(by-ay)*t,bend,phase);
        if(first&&j===0)ctx.moveTo(px+dx,py+dy);else ctx.lineTo(px+dx,py+dy);
      }
    };
    edge(x,y,x+SIZE,y,true);edge(x+SIZE,y,x+SIZE,y+SIZE);
    edge(x+SIZE,y+SIZE,x,y+SIZE);edge(x,y+SIZE,x,y);
    ctx.closePath();ctx.fill();
  });
}
// Canvas overlap edges may blend neighbouring paints. Resolve every occupied
// pixel back to exactly one brand colour before terminal-cell allocation.
function solidColours(ctx){
  const frame=ctx.getImageData(0,0,192,128),d=frame.data;
  const rgb=C.map(hex=>[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)));
  for(let i=0;i<d.length;i+=4){
    if(d[i+3]<128){d[i+3]=0;continue;}
    let best=rgb[0],distance=Infinity;
    for(const colour of rgb){
      const delta=colour.reduce((n,v,c)=>n+(v-d[i+c])**2,0);
      if(delta<distance){best=colour;distance=delta;}
    }
    d[i]=best[0];d[i+1]=best[1];d[i+2]=best[2];d[i+3]=255;
  }
  ctx.putImageData(frame,0,0);
}
export default {
  preserveColours:true,
  id:'microsoft',name:'Microsoft',subtitle:'四色传承 · 从 Windows 飘旗到现代方阵',accent:'#00a4ef',wordmark:'Microsoft',
  footer:['Your potential Our passion','Achieve more','We empower the world'],
  headerIcon:"",
  variants:[{id:'converge',label:"Four-colour heritage",description:'四色从四向汇成飘旗，风势渐息后收平成现代方阵；待机一阵风掠过，再平稳归位'}],
  sources:[
    {label:'官方历史宣传语：Your Potential Our Passion',url:'https://news.microsoft.com/speeches/steve-ballmer-michigan-state-university/'},
    {label:'官方使命与标题：Achieve more / We empower the world',url:'https://www.microsoft.com/en-us/about'},
    {label:'Microsoft 四色几何参考',url:'https://github.com/simple-icons/simple-icons/blob/9.0.0/icons/microsoft.svg'},
    {label:'Windows XP 飘旗轮廓研究来源',url:'https://commons.wikimedia.org/wiki/File:Windows_logo_-_2002.svg'},
  ],
  note:'合并原 Windows 与 Microsoft 原型。静态大图与小图为标准四色方阵；飘旗是参考经典 Windows 的原创连续变形，不是官方动画或 XP 原始轮廓。标题用普通字体排版。三行文案均取自微软官方：历史品牌活动用语、使命中的短句、About 页标题；去除标点并调整大小写，不把它们当作一组官方联合宣传语。',
  render(ctx,s){
    ctx.save();ctx.beginPath();ctx.rect(8,8,176,112);ctx.clip();
    if(settled(s))tiles(ctx);
    else if(s.phase==='idle'){
      const bend=Math.sin(Math.PI*s.t)**2;
      tiles(ctx,bend,s.t*Math.PI*2);
    }else{
      const t=Math.max(0,s.t);
      const from=[[-100,0],[0,-110],[0,110],[100,0]];
      const offsets=from.map(([x,y],i)=>{
        const remaining=1-ease((t-i*.09)/1.05);
        return [Math.round(x*remaining),Math.round(y*remaining)];
      });
      const bend=1-ease((t-1.5)/1.2);
      tiles(ctx,bend,t*2.6,offsets);
    }
    ctx.restore();solidColours(ctx);
  },
  mini(ctx){
    // Four 4×4 squares; the gutter keeps each colour in independent terminal cells.
    [[4,0],[10,0],[4,6],[10,6]].forEach(([x,y],i)=>{ctx.fillStyle=C[i];ctx.fillRect(x,y,4,4);});
  }
};
