// Full-body adaptation of the classic Android robot; see android/SOURCE.md.
import { ease, settled } from './drawing.js';
function round(ctx,x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fill();}
function robot(ctx,{x=0,step=0,wave=0,spread=0,blink=1,y=0,tilt=0,look=0,squash=0}={}){
  ctx.save();ctx.translate(96+x,114+y);ctx.scale(.3*(1+squash),.3*(1-squash));ctx.translate(0,-270);ctx.fillStyle='#3ddc84';
  // The classic source proportions are retained; limbs have independent pivots.
  for(const side of [-1,1]){
    ctx.save();ctx.translate(side*48,186+spread*25);ctx.rotate(side*step*.25);round(ctx,-24,0,48,85,23);ctx.restore();
  }
  round(ctx,-91,52+spread*8,182,150,22);
  ctx.fillStyle='#3ddc84';
  for(const side of [-1,1]){
    ctx.save();ctx.translate(side*(120+spread*55),62);ctx.rotate(side===1?-wave*2.45:step*.25);round(ctx,-24,-14,48,133,24);ctx.restore();
  }
  ctx.save();ctx.translate(look,30-spread*45);ctx.rotate(tilt);ctx.translate(0,-30);
  ctx.beginPath();ctx.ellipse(0,41,91,84,0,Math.PI,Math.PI*2);ctx.closePath();ctx.fill();
  for(const side of [-1,1]){ctx.save();ctx.translate(side*48,-27);ctx.rotate(side*.48);round(ctx,-5,-40,10,44,5);ctx.restore();}
  ctx.fillStyle='#f5fff8';for(const side of [-1,1])round(ctx,side*42-8,-8,16,Math.max(3,16*blink),8);
  ctx.restore();ctx.restore();
}
// Finite envelopes settle to the identical static pose at both ends.
function pulse(t,start,end){
  if(t<=start||t>=end)return 0;
  return Math.sin(Math.PI*(t-start)/(end-start))**2;
}
function greeting(t,start,end){
  const p=(t-start)/(end-start);
  if(p<=0||p>=1)return 0;
  const lift=ease(p/.2)*ease((1-p)/.2);
  return lift*(.82+.16*Math.sin(4*Math.PI*p));
}
function render(ctx,s){
  if(settled(s)){robot(ctx);return;}
  if(s.phase==='idle'){
    const t=s.t,left=pulse(t,.02,.34),right=pulse(t,.28,.57);
    robot(ctx,{
      look:9*(right-left),tilt:.13*(right-left),
      wave:greeting(t,.4,.88),
      blink:1-.85*pulse(t,.87,.98),
    });return;
  }
  const t=s.t,drop=Math.min(1,Math.max(0,t/.72));
  const rebound=pulse(t,.72,1.28);
  const landing=.1*pulse(t,.68,.91);
  const wave=greeting(t,1.3,2.65);
  robot(ctx,{
    y:-135*(1-drop*drop)-10*rebound,
    squash:landing,step:.4*rebound,
    wave,tilt:-.1*pulse(t,1.3,2.65),
    blink:1-.85*pulse(t,2.48,2.68),
  });
}
function mini(ctx, state) {
  ctx.save();
  const silhouette = [
    [3, 5, 13, 15], [4, 6, 12, 14], [5, 13], [4, 14],
    [3, 15], [2, 16], [1, 17], [1, 17],
    [0, 18], [0, 18], [0, 18], [0, 18]
  ];
  ctx.fillStyle = '#3ddc84';
  silhouette.forEach((runs, y) => {
    for (let i = 0; i < runs.length; i += 2) ctx.fillRect(runs[i], y, runs[i + 1] - runs[i], 1);
  });
  // Each eye stays in fully opaque head cells so terminal quantization needs
  // at most green plus dark, never green plus dark plus transparency.
  ctx.fillStyle = '#202124';
  ctx.fillRect(4, 7, 2, 2);
  ctx.fillRect(12, 7, 2, 2);
  ctx.restore();
}

export default {
  id:'android',name:'Android',subtitle:'全身机器人 · 大图挥手，小图探头',accent:'#3ddc84',wordmark:'Android',
  footer:['More choice More you','Way more fun','Android · Google Play · Material'],
  headerIcon:"",
  variants:[{id:'walk',label:"Robot landing",description:'机器人加速落下、着陆回弹、站稳后举手招呼；待机左右探头、连挥两下并眨眼归位'}],
  sources:[{label:'Android 官方素材与署名要求',url:'https://developer.android.com/distribute/marketing-tools/brand-guidelines'},{label:'经典全身机器人参考',url:'https://commons.wikimedia.org/wiki/File:Android_robot.svg'},{label:'Android 文案参考',url:'https://www.android.com/intl/en_au/'}],
  note:'大图参考经典全身机器人比例，重绘为透明关节、现代绿色、白色圆眼和独立肢体动作；不是原始官方全身 SVG 的直接展示。小图继续使用独立头部像素图。Android 机器人由 Google 创建并分享，按 CC BY 3.0 署名和改编。',
  render,mini
};
