import { paths } from './nvidia/paths.js';
import { path, ease, settled } from './drawing.js';
function eye(ctx,light=false,color=null){ctx.save();ctx.translate(26,-6);ctx.scale(140/24,140/24);ctx.fillStyle=color||(light?'#598d00':'#76b900');ctx.fill(path(paths[0]));ctx.restore();}
function mask(ctx){
  ctx.translate(26,-6);ctx.scale(140/24,140/24);ctx.clip(path(paths[0]));
  ctx.scale(24/140,24/140);ctx.translate(-26,6);
}
function opening(ctx,s){
  const t=s.t;
  const heads=[];
  // A 4×4 grid gives every tiny digit its own terminal cell pair.
  // Fixed stagger and glyphs keep the rain coherent between adjacent frames.
  for(let c=0;c<36;c++){
    const delay=((c*11)%19)*.026;
    const p=ease((t-delay)/1.9),head=4*Math.round((-40+208*p)/4);
    heads.push(head);
    const length=Math.round(11*(1-ease((t-1.65-delay)/.5)));
    for(let row=0;row<length;row++){
      const y=head-row*4,x=24+c*4;
      if(y<8||y>116)continue;
      ctx.fillStyle=row===0?(s.light?'#365e00':'#c5f26b'):
        row<4?(s.light?'#598d00':'#76b900'):(s.light?'#8caa61':'#28550d');
      if((c*3+row)%5<2)ctx.fillRect(x+1,y,1,3);
      else {ctx.fillRect(x,y,3,3);ctx.clearRect(x+1,y+1,1,1);}
    }
  }
  if(heads.every(head=>head-4>=128))eye(ctx,s.light);
  else {
    ctx.save();ctx.beginPath();
    heads.forEach((head,c)=>ctx.rect(24+c*4,0,4,Math.max(0,head-4)));
    ctx.clip();eye(ctx,s.light);ctx.restore();
  }
  // The thin write head lives inside the logo, never a rectangle over its holes.
  if(t<2.55){
    ctx.save();mask(ctx);ctx.fillStyle=s.light?'#365e00':'#c5f26b';
    heads.forEach((head,c)=>{if(head>8&&head<120)ctx.fillRect(24+c*4,head-8,4,4);});
    ctx.restore();
  }
}
// Original RTX-inspired light paths, expressed in the logo's source coordinates.
const RAYS=[
  [[23.5,5.5],[19,8],[21,10.5],[14,10.5],[10,11.6]],
  [[23.5,11.5],[20,11.5],[18.5,9],[14,10.5],[10,11.6]],
  [[23.5,18.8],[19,16.5],[21,14],[14,10.5],[10,11.6]],
];
function screen([x,y]){return [26+x*140/24,-6+y*140/24];}
function track(points){
  const pts=points.map(screen),lengths=[0];
  for(let i=1;i<pts.length;i++)lengths.push(lengths[i-1]+Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]));
  return {pts,lengths,total:lengths.at(-1)};
}
const LIGHT_PATHS=RAYS.map(track);
function orbit(){
  const points=[[1.2,10.7]],curves=[
    [[3,8.7],[6,6.9],[9,6.8]],
    [[12.6,6.6],[15.3,8.2],[17,10.7]],
    [[14.5,13.6],[12.2,16.8],[9,16.7]],
    [[4.2,16],[2.2,13.4],[1.2,10.7]],
  ];
  for(const [b,c,d] of curves){
    const a=points.at(-1);
    for(let i=1;i<=20;i++){
      const t=i/20,u=1-t;
      points.push([0,1].map(k=>u*u*u*a[k]+3*u*u*t*b[k]+3*u*t*t*c[k]+t*t*t*d[k]));
    }
  }
  return track(points);
}
const ORBIT=orbit();
function segment(ctx,route,start,end,color,width){
  start=Math.max(0,start);end=Math.min(route.total,end);
  if(end<=start)return;
  ctx.beginPath();let began=false;
  for(let i=1;i<route.pts.length;i++){
    const lo=route.lengths[i-1],hi=route.lengths[i];
    if(hi<=start||lo>=end)continue;
    const a=route.pts[i-1],b=route.pts[i];
    const pointAt=d=>a.map((v,k)=>v+(b[k]-v)*(d-lo)/(hi-lo));
    const from=pointAt(Math.max(start,lo)),to=pointAt(Math.min(end,hi));
    if(!began){ctx.moveTo(...from);began=true;}ctx.lineTo(...to);
  }
  ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineCap='butt';ctx.lineJoin='bevel';ctx.stroke();
}
function idle(ctx,s){
  const t=s.t,energy=Math.sin(Math.PI*t)**2;
  const base=s.light?[89,141,0]:[118,185,0];
  const dim=base.map(v=>Math.round(v*(1-.42*energy)));
  eye(ctx,s.light,`rgb(${dim.join(',')})`);
  const bright=s.light?'#d7f2a2':'#edffc2',trail=s.light?'#91b950':'#b4e86a';
  ctx.save();mask(ctx);
  // Parallel rays retain short trails as they change direction and reach the core.
  LIGHT_PATHS.forEach((route,i)=>{
    const p=ease((t-.03-i*.025)/.4),head=p*(route.total+60);
    segment(ctx,route,head-60,head,trail,6);
    segment(ctx,route,head-22,head,bright,3);
  });
  const hit=Math.sin(Math.PI*Math.max(0,Math.min(1,(t-.36)/.2)));
  if(hit>0){
    const [x,y]=screen([10,11.6]),r=Math.round(6*hit);
    ctx.fillStyle=bright;ctx.fillRect(Math.round(x)-r,Math.round(y)-1,r*2,2);
    ctx.fillRect(Math.round(x)-1,Math.round(y)-r,2,r*2);
  }
  // A single energy packet follows the eye's curved band and exits smoothly.
  const p=ease((t-.43)/.54),head=p*(ORBIT.total+76);
  segment(ctx,ORBIT,head-76,head,trail,8);
  segment(ctx,ORBIT,head-28,head,bright,4);
  ctx.restore();
}
export default {
  id:'nvidia',name:'NVIDIA',subtitle:'绿色眼形 · 绿色数字雨',accent:'#76b900',wordmark:'NVIDIA',
  footer:['The way it’s meant to be played','Accelerated imagination','GeForce · RTX · CUDA'],
  headerIcon:"N",
  variants:[{id:'scan',label:"Matrix construction",description:'细密数字雨逐列写入眼形，亮色写入头沿轮廓收束；待机三束 RTX 光路折转汇聚，亮色脉冲沿眼形曲线推进'}],
  badges:[{id:'gpu',label:'双风扇显卡'},{id:'eye',label:'原始眼形'}],
  sources:[{label:'NVIDIA 品牌参考',url:'https://www.nvidia.com/en-gb/about-nvidia/legal-info/logo-brand-usage/'},{label:'眼形矢量来源',url:'https://github.com/simple-icons/simple-icons/blob/9.0.0/icons/nvidia.svg'},{label:'历史品牌用语',url:'https://http.download.nvidia.com/downloads/nZone/theway/TheWay_Issue_5.pdf'}],
  note:'眼形来自 Simple Icons 保存的品牌轮廓，小图可选原创双风扇显卡或原始眼形的等比像素适配；显卡是硬件意象，并非 NVIDIA 官方标志。首句是 NVIDIA 历史宣传语；次句为编辑文案，平台行是产品名称组合。动画为原创设计，非官方品牌动画。',
  render(ctx,s){
    ctx.save();ctx.beginPath();ctx.rect(8,8,176,112);ctx.clip();
    if(settled(s))eye(ctx,s.light);
    else if(s.phase==='idle')idle(ctx,s);
    else opening(ctx,s);
    ctx.restore();
  },
  mini(ctx,s){
    const green=s.light?'#598d00':'#76b900';
    if(s.badge==='eye'){
      ctx.save();ctx.translate(1,-2);ctx.scale(16/24,16/24);
      ctx.fillStyle=green;ctx.fill(path(paths[0]));ctx.restore();return;
    }
    // A graphics card, rather than a cramped imitation of the nested brand eye.
    // Use just two colours, with the fan detail inside fully occupied terminal cells.
    ctx.fillStyle=green;ctx.fillRect(2,2,14,8);ctx.fillRect(0,4,1,8);
    ctx.fillRect(5,10,7,1);
    // Keep the dark shroud inside the fully opaque middle cell row.
    // Otherwise quadrant row duplication makes the lower-right edge dark.
    ctx.fillStyle='#142609';ctx.fillRect(3,4,12,4);
    for(const x of [5,12]){
      ctx.fillStyle=green;
      ctx.fillRect(x-1,4,3,1);ctx.fillRect(x-2,5,5,2);ctx.fillRect(x-1,7,3,1);
      ctx.fillStyle='#142609';ctx.fillRect(x,5,1,2);
    }
  }
};
