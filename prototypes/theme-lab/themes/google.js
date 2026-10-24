import { letters } from './google/letters.js';
import { path, ease, grid, settled } from './drawing.js';
const COLORS = ['#4285f4','#ea4335','#fbbc05','#34a853'];
function word(ctx, displace = () => [0,0]) {
  // Use more of the canvas and compensate for paired terminal pixel rows.
  // Preserve source letter widths, spacing and colours, including the g descender.
  const scale=174/272;
  ctx.save(); ctx.translate(9,64-46*scale*1.14); ctx.scale(scale,scale*1.14);
  letters.forEach((letter,i) => { const [x,y]=displace(i); ctx.save(); ctx.translate(x,y);ctx.fillStyle=letter.color;ctx.fill(path(letter.d));ctx.restore(); });
  ctx.restore();
}
export default {
  layout: { show_title: false },
  id:'google',name:'Google',subtitle:'2015 四色字标 · 四色轨道 · 字母弹入',accent:'#4285f4',wordmark:'Google',
  footer:['Search Discover Create','A little curiosity','Search · Chrome · Pixel'],
  headerIcon:"",
  variants:[{id:'letters',label:"Colour convergence",description:'四色粒子沿轨道旋入，六个字母从环绕位置落定'}],
  sources:[{label:'Google 官方 G 素材',url:'https://fonts.gstatic.com/s/i/productlogos/googleg/v6/24px.svg'},{label:'Google 官方 2015 视觉体系',url:'https://design.google/library/evolving-google-identity'},{label:'字标矢量来源',url:'https://commons.wikimedia.org/wiki/File:Google_2015_logo.svg'}],
  note:'使用明确的 2015 实色字标版本，不声称是最新标志。大图来自 Wikimedia 收录矢量；G 小图依据 Google 官方产品 SVG 做独立像素适配。三行文案为品牌相关编辑提案，不是官方 slogan；动作原创。',
  render(ctx,s){
    if(settled(s)){word(ctx);return;}
    if(s.phase==='idle'){const wave=Math.sin(Math.PI*s.t);word(ctx,i=>[0,-8*wave*Math.sin(Math.PI*s.t*2+i*.6)]);return;}
    const t=s.t, energy=1-ease((t-1.2)/1.3);
    // Four coloured comet trails tighten into the word, then shrink to zero.
    for(let c=0;c<4;c++)for(let k=0;k<12;k++){
      const a=t*4+c*Math.PI/2-k*.07,r=(52+k*2)*energy;
      const size=Math.round((4-k*.23)*energy);
      ctx.fillStyle=COLORS[c];ctx.fillRect(Math.round(96+Math.cos(a)*r),Math.round(64+Math.sin(a)*r*.68),size,size);
    }
    word(ctx,i=>{const q=1-ease((t-.35-i*.1)/1.65),a=i*Math.PI/3+t*2;
      return [Math.cos(a)*90*q,Math.sin(a)*65*q];});
  },
  mini(ctx){
    // Optical adaptation of g.svg: paired rows preserve the counter in quadrant mode.
    const rows=[
      '......rrrrrrr.....','......rrrrrrr.....',
      '....rrrr....rrr...','....rrrr....rrr...',
      '...yyy............','...yyy............',
      '...yyy..bbbbbbb...','...yyy..bbbbbbb...',
      '....ggg.....bbb...','....ggg.....bbb...',
      '......gggggbb.....','......gggggbb.....'
    ];
    grid(ctx,rows,{r:'#ea4335',y:'#fbbc05',g:'#34a853',b:'#4285f4'});
  }
};
