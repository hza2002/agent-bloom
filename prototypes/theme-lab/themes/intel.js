import { paths } from './intel/paths.js';
import { path, ease, grid, settled } from './drawing.js';
// Keep the oval unchanged, enlarge only letter height, and omit the tiny ®.
const [LETTER_PATH,oval]=paths[0].split('m4.347-6.038');
const OVAL_PATH='M23.894 8.584'+oval.split('M20.984')[0];
let displayPath;
function artwork(){
  if(!displayPath){
    displayPath=new Path2D(OVAL_PATH);
    displayPath.addPath(path(LETTER_PATH),new DOMMatrix([1,0,0,1.16,0,-11.4*.16]));
  }
  return displayPath;
}
function logo(ctx,light=false){ctx.save();ctx.translate(18,-14);ctx.scale(6.5,6.5);ctx.fillStyle=light?'#0068b5':'#32baff';ctx.fill(artwork());ctx.restore();}
function idle(ctx,s){
  const t=s.t,energy=Math.sin(Math.PI*t)**2;
  logo(ctx,s.light);
  // Smooth orbital packets accelerate together, with continuous short trails.
  const angle=-Math.PI/2+Math.PI*2*(.3*t+.7*t*t);
  const position=a=>{
    const x=78*Math.cos(a),y=43*Math.sin(a),r=-.15;
    return [96+x*Math.cos(r)-y*Math.sin(r),64+x*Math.sin(r)+y*Math.cos(r)];
  };
  for(let packet=0;packet<2;packet++){
    const head=angle+packet*Math.PI;
    for(let layer=0;layer<2;layer++){
      const tail=(layer?.2:.8)*energy;
      if(tail<.005)continue;
      ctx.beginPath();
      for(let j=0;j<=24;j++){
        const [x,y]=position(head-tail+tail*j/24);
        j?ctx.lineTo(x,y):ctx.moveTo(x,y);
      }
      ctx.lineWidth=(layer?3:2)*energy;
      ctx.strokeStyle=layer?(s.light?'#003d73':'#e1f8ff'):(s.light?'#0089c9':'#32baff');
      ctx.stroke();
    }
  }
  // Only the actual letter ink lights up; the orbit remains a separate data track.
  ctx.save();ctx.translate(18,-14);ctx.scale(6.5,6.5);ctx.clip(artwork());
  ctx.scale(1/6.5,1/6.5);ctx.translate(-18,14);
  const letters=[[40,12],[56,28],[86,20],[108,26],[136,12]];
  letters.forEach(([x,width],i)=>{
    const p=(t-.12-i*.105)/.27;
    if(p>0&&p<1){
      ctx.fillStyle=s.light?'#003d73':'#c6f1ff';
      const h=Math.round(34*Math.sin(Math.PI*p)**2);
      ctx.fillRect(x,82-h,width,h);
    }
  });ctx.restore();
}
export default {
  id:'intel',name:'Intel',subtitle:'经典椭圆字标 · 芯片与电路',accent:'#32baff',wordmark:'intel',
  footer:['Intel Inside','Leap ahead','Core · Xeon · Intel Arc'],
  headerIcon:"",
  variants:[{id:'orbit',label:"Silicon startup",description:'芯片引脚回收，方形晶粒扩展为轨道，数据通道交错写出字标；待机双路轨道加速，字母依次通电'}],
  sources:[{label:'Intel 官方 2006 品牌发布：Leap ahead',url:'https://www.intel.com/pressroom/archive/releases/2006/20060103corp.htm'},{label:'Intel 官方产品名称',url:'https://www.intel.com/content/www/us/en/products/overview.html'},{label:'Intel 官方品牌历史',url:'https://timeline.intel.com/1991/inside-intel-inside'},{label:'经典矢量来源',url:'https://github.com/simple-icons/simple-icons/blob/1.20.0/icons/intel.svg'}],
  note:'选用经典椭圆 Intel 轮廓，保留 Simple Icons 1.20.0 SVG，不是当前字标。小图为独立芯片像素图。Intel Inside 为历史品牌用语，Leap ahead 为 2006 年官方品牌用语，第三行为官方产品名称组合；动作不复刻官方启动动画。',
  render(ctx,s){if(settled(s)){logo(ctx,s.light);return;}
    if(s.phase==='idle'){idle(ctx,s);return;}
    const t=s.t, expand=ease((t-.35)/1.5), vanish=1-ease((t-1.45)/.95);
    // A processor die opens into an orbital circuit; pins retract continuously.
    ctx.strokeStyle=s.light?'#0068b5':'#32baff';ctx.lineWidth=2*vanish;
    if(vanish>0){
      ctx.beginPath();
      for(let i=0;i<=64;i++){
        const a=i*Math.PI/32,co=Math.cos(a),si=Math.sin(a),square=18/Math.max(Math.abs(co),Math.abs(si));
        const x=96+co*(square*(1-expand)+81*expand),y=64+si*(square*(1-expand)+45*expand);
        i?ctx.lineTo(x,y):ctx.moveTo(x,y);
      }ctx.stroke();
      ctx.fillStyle=s.light?'#0068b5':'#32baff';
      for(let side=0;side<4;side++)for(let pin=0;pin<5;pin++){
        ctx.save();ctx.translate(96,64);ctx.rotate(side*Math.PI/2);
        ctx.fillRect(-14+pin*7,20+expand*20,2*vanish,18*(1-expand));ctx.restore();
      }
    }
    // Opposing data lanes reveal the actual mark rather than replacing it.
    ctx.save();ctx.beginPath();
    for(let row=0;row<16;row++){
      const p=ease((t-.55-(row%4)*.1)/1.65),w=192*p;
      ctx.rect(row%2?192-w:0,row*8,w,8);
    }
    ctx.clip();logo(ctx,s.light);ctx.restore();
  },
  mini(ctx){grid(ctx,[
    '.....b.b.b.b......','...bbbbbbbbbbbb...','...bccccccccccb...',
    '..bbccbbbbbbccbb..','...bccbccccbccb...','..bbccbccccbccbb..',
    '...bccbccccbccb...','..bbccbbbbbbccbb..','...bccccccccccb...',
    '...bbbbbbbbbbbb...','.....b.b.b.b......','..................'
  ],{b:'#32baff',c:'#0c4674'});}
};
