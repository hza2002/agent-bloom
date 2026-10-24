import { intelMark } from './intel/official-paths.js';
import { path, ease, grid, settled, pixelOutline } from './drawing.js';
// Official 2008 cover paths, uniformly normalized; omit the tiny registration mark.
const LETTER_PATH = intelMark.letters;
const OVAL_PATH = intelMark.oval;
const E_BOX = intelMark.eBox;
const ink = light => light ? '#0068b5' : '#32baff';
function mark(ctx, part, colour) {
  ctx.save();ctx.translate(18,-14);ctx.scale(6.5,6.5);
  ctx.fillStyle=colour;
  if(part===LETTER_PATH) {
    ctx.save();ctx.beginPath();ctx.rect(0,0,24,24);ctx.rect(...E_BOX);ctx.clip('evenodd');
    ctx.fill(path(part));ctx.restore();
    ctx.fill(pixelOutline(part,E_BOX,...intelMark.eGrid,intelMark.eOmit));
  } else ctx.fill(path(part));
  ctx.restore();
}
function logo(ctx, light=false) {
  mark(ctx, OVAL_PATH, ink(light));mark(ctx, LETTER_PATH, ink(light));
}
function colour(a,b,t) {
  return `rgb(${a.map((v,i)=>Math.round(v+(b[i]-v)*t)).join(',')})`;
}
function trace(ctx, points, progress, colour) {
  const lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));
  let remaining=lengths.reduce((a,b)=>a+b,0)*progress;
  let head=points[0];ctx.beginPath();ctx.moveTo(...head);
  for(let i=0;i<lengths.length;i++) {
    const q=Math.min(1,remaining/lengths[i]);
    head=points[i].map((v,k)=>v+(points[i+1][k]-v)*q);
    ctx.lineTo(...head);remaining-=lengths[i];if(remaining<=0)break;
  }
  ctx.strokeStyle=colour;ctx.lineWidth=2;ctx.stroke();
  ctx.fillStyle=colour;ctx.fillRect(Math.round(head[0])-1,Math.round(head[1])-1,3,3);
}
function intro(ctx,s) {
  const t=s.t, current=ease((t-.12)/.8), release=ease((t-.92)/.42);
  const blue=ink(s.light);
  // Four orthogonal circuit traces deliver a single clock pulse to a square die.
  if(t<1.34) {
    const signal=colour(s.light?[0,104,181]:[50,186,255],s.light?[0,61,115]:[207,244,255],1-release);
    for(const points of [ [[12,44],[42,44],[62,64],[78,64]],
                         [[180,84],[150,84],[130,64],[114,64]],
                         [[76,8],[76,30],[96,48]], [[116,120],[116,98],[96,80]] ]) {
      if(current>0 && release<.98)trace(ctx,points,current,signal);
    }
    const size=Math.round(32*(1-release));
    if(size>0) {
      ctx.strokeStyle=blue;ctx.lineWidth=2;ctx.strokeRect(96-size/2,64-size/2,size,size);
      ctx.fillStyle=signal;
      const core=Math.max(2,Math.round(size*.42));ctx.fillRect(96-core/2,64-core/2,core,core);
      for(let side=0;side<4;side++)for(let pin=0;pin<4;pin++) {
        ctx.save();ctx.translate(96,64);ctx.rotate(side*Math.PI/2);
        ctx.fillRect(Math.round((-10+pin*7)*(1-release)),Math.round(size/2+2),2,Math.round(6*(1-release)));ctx.restore();
      }
    }
  }
  // Stamp the source letters into place; then close the actual Intel oval.
  const word=ease((t-.86)/1.02);
  if(word>0) {
    ctx.save();ctx.beginPath();ctx.rect(96-82*word,8,164*word,112);ctx.clip();
    mark(ctx,LETTER_PATH,blue);ctx.restore();
  }
  const orbit=ease((t-1.02)/1.2);
  if(orbit>0) {
    ctx.save();ctx.beginPath();ctx.moveTo(96,64);
    ctx.arc(96,64,118,-Math.PI/2,-Math.PI/2+Math.PI*2*orbit);ctx.closePath();ctx.clip();
    mark(ctx,OVAL_PATH,blue);ctx.restore();
  }
}
function idle(ctx,s) {
  logo(ctx,s.light);
  const t=s.t, energy=Math.sin(Math.PI*t)**2;
  if(energy<1e-8)return;
  const angle=-Math.PI/2+2*Math.PI*(.25*t+.75*t*t);
  // Data stays on the actual brand ink, so no detached satellites or extra pixels.
  ctx.save();ctx.globalCompositeOperation='source-atop';
  ctx.save();ctx.translate(18,-14);ctx.scale(6.5,6.5);ctx.clip(path(OVAL_PATH));
  ctx.scale(1/6.5,1/6.5);ctx.translate(-18,14);
  const base=s.light?[0,104,181]:[50,186,255], peak=s.light?[0,36,81]:[225,249,255];
  for(let i=0;i<2;i++) {
    const a=angle+i*Math.PI;
    ctx.fillStyle=colour(base,peak,energy);
    ctx.beginPath();ctx.ellipse(96+76*Math.cos(a),64+43*Math.sin(a),18,15,0,0,Math.PI*2);ctx.fill();
  }
  ctx.restore();
  ctx.translate(18,-14);ctx.scale(6.5,6.5);ctx.clip(path(LETTER_PATH));
  ctx.scale(1/6.5,1/6.5);ctx.translate(-18,14);
  const x=25+145*ease(t);
  const light=ctx.createLinearGradient(x-20,0,x+20,0);
  light.addColorStop(0,colour(base,peak,0));light.addColorStop(.5,colour(base,peak,energy*.8));light.addColorStop(1,colour(base,peak,0));
  ctx.fillStyle=light;ctx.fillRect(x-20,20,40,80);ctx.restore();
}
// Independent processor badge studies, not official Intel die layouts.
const MINI_CHIPS = {
  cpu: [
    '....bbbbbbbbbb....',
    '....bbbbbbbbbb....',
    '...bbssssssssbb...',
    '...bbssssssssbb...',
    '...bbssbbbbssbb...',
    '...bbssssssssbb...',
    '...bbssbbbsssbb...',
    '...bbssssssssbb...',
    '...bbssssssssbb...',
    '...bbssssssssbb...',
    '....bbbbbbbbbb....',
    '....bbbbbbbbbb....',
  ],
  die: [
    '...dddggddggddd...',
    '...dddggddggddd...',
    '...ddbbbbbbbbdd...',
    '...ddbbbbbbbbdd...',
    '...ggbbccccbbgg...',
    '...ggbbccccbbgg...',
    '...ggbbccccbbgg...',
    '...ggbbccccbbgg...',
    '...ddbbbbbbbbdd...',
    '...ddbbbbbbbbdd...',
    '...dddggddggddd...',
    '...dddggddggddd...',
  ],
  circuit: [
    '........bb........',
    '........bb........',
    '.bb..bbbbbbbb.....',
    '.bb..bbbbbbbb.....',
    '.bbbbbbccccbb.....',
    '.bbbbbbccccbb.....',
    '.....bbccccbbbbbb.',
    '.....bbccccbbbbbb.',
    '.....bbbbbbbb..bb.',
    '.....bbbbbbbb..bb.',
    '........bb........',
    '........bb........',
  ],
};
const MINI_COLOURS = {"dark":{"b":"#32baff","d":"#123854","c":"#beecff","g":"#e2b454","s":"#becad2"},"light":{"b":"#0068b6","d":"#20445e","c":"#62b6e0","g":"#987020","s":"#b2bcc8"}};
export default {
  layout: { show_title: false },
  id:'intel',name:'Intel',subtitle:'经典椭圆字标 · 芯片与电路',accent:'#32baff',wordmark:'intel',
  footer:['Intel Inside','Leap ahead','Core · Xeon · Intel Arc'],
  badges:[{id:'die',label:'蓝色核心 · 金色触点'},{id:'cpu',label:'银色 CPU 顶盖'},{id:'circuit',label:'核心电路'}],
  headerIcon:"",
  variants:[{id:'orbit',label:"Silicon startup",description:'四路电路汇聚为芯片时钟，字标压印落定、经典椭圆闭合；待机信号沿真实椭圆与字形流动'}],
  sources:[{label:'Intel 官方处理器封装说明',url:'https://www.intel.com/content/www/us/en/support/articles/000005670/processors.html'},{label:'Intel 官方 2006 品牌发布：Leap ahead',url:'https://www.intel.com/pressroom/archive/releases/2006/20060103corp.htm'},{label:'Intel 官方产品名称',url:'https://www.intel.com/content/www/us/en/products/overview.html'},{label:'Intel 官方品牌历史',url:'https://timeline.intel.com/1991/inside-intel-inside'},{label:'经典矢量：Intel 官方文档 317804-010 封面',url:'https://cdrdv2-public.intel.com/841119/317804.pdf'}],
  note:'经典椭圆字标直接提取自 Intel 官方 2008 年文档 317804-010 封面的矢量路径，不是当前字标。仅做统一缩放归一化；原始路径与文档校验值随素材记录。小图默认采用深蓝封装、蓝色核心与金色触点的原创处理器意象，不是实际 Intel 裸片布局；大图 e 的细节采用单色网格适配，保持开口和横杆清晰。Intel Inside 为历史品牌用语，Leap ahead 为 2006 年官方品牌用语，第三行为官方产品名称组合；动作不复刻官方启动动画。',
  render(ctx,s){
    if(settled(s)){logo(ctx,s.light);return;}
    if(s.phase==='idle')idle(ctx,s);else intro(ctx,s);
  },
  mini(ctx,s){
    const pixels=MINI_CHIPS[s.badge]||MINI_CHIPS.die;
    grid(ctx,pixels,MINI_COLOURS[s.light?'light':'dark']);
  }
};
