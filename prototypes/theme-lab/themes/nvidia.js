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
// The logo changes material: solid eye -> binary glyph eye -> solid eye.
// There is no solid green backing beneath the data field at full decode.
function idle(ctx,s){
  const t=s.t;
  eye(ctx,s.light);
  const solid=ctx.getImageData(0,0,192,128);
  ctx.clearRect(0,0,192,128);
  ctx.save();mask(ctx);
  const colours=s.light?['#284c00','#4b7800','#739343']:['#c5f26b','#76b900','#356414'];
  const tick=Math.floor(t*28);
  for(let c=0;c<36;c++)for(let row=0;row<32;row++){
    const x=24+c*4,y=row*4;
    const head=(c*7+tick)%32,tail=(head-row+32)%32;
    ctx.fillStyle=colours[tail===0?0:tail<6?1:2];
    const identity=((c*23+(row-tick)*37)%11+11)%11;
    if(identity<5)ctx.fillRect(x+1,y,1,3);
    else {
      ctx.fillRect(x,y,3,1);ctx.fillRect(x,y+2,3,1);
      ctx.fillRect(x,y+1,1,1);ctx.fillRect(x+2,y+1,1,1);
    }
  }
  ctx.restore();
  const frame=ctx.getImageData(0,0,192,128);
  const decode=ease(t/.22)*(1-ease((t-.70)/.30));
  for(let y=0;y<128;y++)for(let x=0;x<192;x++){
    const i=(y*192+x)*4,c=Math.floor((x-24)/4),row=Math.floor(y/4);
    const rank=(((c*13+row*7)%29+29)%29+.5)/29;
    if(decode<rank){
      for(let k=0;k<4;k++)frame.data[i+k]=solid.data[i+k];
    }else{
      // Preserve the original outer boundary and pupil. Inside the eye,
      // transparent spaces between digits are real gaps in the artwork.
      frame.data[i+3]=Math.min(frame.data[i+3],solid.data[i+3]);
    }
  }
  ctx.putImageData(frame,0,0);
}

function foundersCard(ctx,variant='gpu'){
  // Original 18x12 optical adaptations of the Founders Edition coolers.
  // Two colours keep the fan cells exact in both terminal glyph modes.
  const silver='#b8c0c2',dark='#1a2225';
  ctx.fillStyle=silver;
  ctx.fillRect(0,3,1,8); // I/O bracket
  ctx.fillRect(2,3,14,1);ctx.fillRect(1,4,16,4);
  ctx.fillRect(2,8,14,1);ctx.fillRect(5,9,7,1);
  const fan=cx=>{
    ctx.fillStyle=dark;
    ctx.fillRect(cx-1,4,3,1);ctx.fillRect(cx-2,5,5,2);ctx.fillRect(cx-1,7,3,1);
    ctx.fillStyle=silver;ctx.fillRect(cx,5,1,2);
  };
  if(variant==='gpu4090'){
    ctx.fillStyle=dark;ctx.fillRect(3,4,6,4);
    // X-shaped rail and one visible fan evoke the 4090 flow-through face.
    ctx.fillStyle=silver;
    for(let y=0;y<4;y++){
      ctx.fillRect(3+y,4+y,1,1);ctx.fillRect(6-y,4+y,1,1);
    }
    fan(12);
  }else{fan(5);fan(12);}
}
export default {
  id:'nvidia',name:'NVIDIA',subtitle:'绿色眼形 · 绿色数字雨',accent:'#76b900',wordmark:'NVIDIA',
  footer:['The way it’s meant to be played','Accelerated imagination','GeForce · RTX · CUDA'],
  headerIcon:"󰢮",
  variants:[{id:'scan',label:"Matrix construction",description:'细密数字雨逐列写入眼形，亮色写入头沿轮廓收束；待机眼形解码为 0/1 数据结构，数字流构成眼眶与瞳孔边界，随后逐格聚回实心眼形'}],
  badges:[{id:'gpu',label:'2080 Ti FE · 双风扇'},{id:'gpu4090',label:'4090 FE · X 框架'},{id:'eye',label:'原始眼形'}],
  sources:[{label:'2080 Ti FE 官方外观参考',url:'https://www.nvidia.com/content/nvidiaGDC/zz/en_ZZ/geforce/graphics-cards/rtx-2080-ti.html'},{label:'4090 FE 官方外观参考',url:'https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4090/'},{label:'NVIDIA 品牌参考',url:'https://www.nvidia.com/en-gb/about-nvidia/legal-info/logo-brand-usage/'},{label:'眼形矢量来源',url:'https://github.com/simple-icons/simple-icons/blob/9.0.0/icons/nvidia.svg'},{label:'历史品牌用语',url:'https://http.download.nvidia.com/downloads/nZone/theway/TheWay_Issue_5.pdf'}],
  note:'眼形来自 Simple Icons 保存的品牌轮廓，小图可选参考 2080 Ti FE 银色双风扇、4090 FE X 框架与单面可见风扇的原创像素适配，或原始眼形；不是官方 sprite 或精确硬件图纸。首句是 NVIDIA 历史宣传语；次句为编辑文案，平台行是产品名称组合。动画为原创设计，非官方品牌动画。',
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
    foundersCard(ctx,s.badge);
  }
};
