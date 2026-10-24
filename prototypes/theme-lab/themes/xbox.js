// Pixel sphere with the saved Xbox outline mapped onto its front hemisphere.
const OUTLINE = 'M4.102 21.033C6.211 22.881 8.977 24 12 24c3.026 0 5.789-1.119 7.902-2.967 1.877-1.912-4.316-8.709-7.902-11.417-3.582 2.708-9.779 9.505-7.898 11.417zm11.16-14.406c2.5 2.961 7.484 10.313 6.076 12.912C23.002 17.48 24 14.861 24 12.004c0-3.34-1.365-6.362-3.57-8.536 0 0-.027-.022-.082-.042-.063-.022-.152-.045-.281-.045-.592 0-1.985.434-4.805 3.246zM3.654 3.426c-.057.02-.082.041-.086.042C1.365 5.642 0 8.664 0 12.004c0 2.854.998 5.473 2.661 7.533-1.401-2.605 3.579-9.951 6.08-12.91-2.82-2.813-4.216-3.245-4.806-3.245-.131 0-.223.021-.281.046v-.002zM12 3.551S9.055 1.828 6.755 1.746c-.903-.033-1.454.295-1.521.339C7.379.646 9.659 0 11.984 0H12c2.334 0 4.605.646 6.766 2.085-.068-.046-.615-.372-1.52-.339C14.946 1.828 12 3.545 12 3.545v.006z';
const clamp=t=>Math.max(0,Math.min(1,t));
const ease=t=>{t=clamp(t);return t*t*(3-2*t);};
let mask, raster, rasterContext, image, lastFrame;
function sourceMask(){
  if(!mask){
    const c=document.createElement('canvas');c.width=c.height=192;
    const g=c.getContext('2d');g.scale(8,8);g.fill(new Path2D(OUTLINE));
    mask=g.getImageData(0,0,192,192).data;
  }return mask;
}
// Interior shading uses finer solid steps; silhouette pixels remain fully opaque or transparent.
const SHADE_STOPS=[
  [17,53,25],[20,68,27],[24,84,29],[28,100,32],
  [34,119,33],[41,138,35],[49,157,36],[63,173,40],
  [77,188,44],[91,203,49],[113,214,60],[136,224,71],[159,234,83]
];
// Keep the interior palette restrained: dense colours compete inside two-colour terminal cells.
const PALETTE=SHADE_STOPS.flatMap((color,i)=>i===SHADE_STOPS.length-1?[color]:[
  color,color.map((value,c)=>Math.round((value+SHADE_STOPS[i+1][c])/2))
]);
function sphere(ctx,{radius=48,yaw=0,open=1,light=1}={}){
  const key=[radius,yaw,open,light].join('/');
  if(!raster){raster=document.createElement('canvas');raster.width=192;raster.height=128;rasterContext=raster.getContext('2d');image=rasterContext.createImageData(192,128);}
  if(key===lastFrame){ctx.drawImage(raster,0,0);return;}
  const src=sourceMask(),d=image.data;d.fill(0);
  const co=Math.cos(yaw),si=Math.sin(yaw);
  for(let y=0;y<128;y++)for(let x=0;x<192;x++){
    const nx=(x+.5-96)/radius,ny=(y+.5-64)/radius,q=nx*nx+ny*ny;
    if(q>=1)continue;
    const nz=Math.sqrt(1-q),sx=nx*co-nz*si,sz=nx*si+nz*co;
    const u=Math.min(191,Math.max(0,Math.floor((sx+1)*96)));
    const v=Math.min(191,Math.max(0,Math.floor((ny+1)*96)));
    // The last sliver at the horizon is solid shell; avoid sampling outside the source circle.
    const carved=sz>.14&&!src[(v*192+u)*4+3];
    // The gap opens radially from the centre; it remains a cutout, never a light bar.
    if(carved&&Math.sqrt(sx*sx+ny*ny)<open*1.5)continue;
    const illumination=clamp((.32-.28*nx-.42*ny+.45*nz)*light);
    const color=PALETTE[Math.min(PALETTE.length-1,Math.floor(illumination*PALETTE.length))],i=(y*192+x)*4;
    d[i]=color[0];d[i+1]=color[1];d[i+2]=color[2];d[i+3]=255;
  }
  // putImageData ignores transforms; draw the cached-size raster through Canvas instead.
  rasterContext.putImageData(image,0,0);lastFrame=key;ctx.drawImage(raster,0,0);
}
function awaken(ctx,t){
  const settle=ease((t-1.45)/1.15);
  sphere(ctx,{radius:56-8*settle,yaw:.38*(1-settle),open:ease((t-.25)/1.35),light:.2+.8*ease(t/1.5)});
}
function fold(ctx,t){
  const p=ease(t/2.35);
  if(p===1){sphere(ctx);return;}
  for(let part=0;part<4;part++){
    const a=part*Math.PI/2,q=ease((t-part*.12)/1.9),rest=1-q;
    ctx.save();ctx.translate(96+Math.cos(a)*42*rest,64+Math.sin(a)*42*rest);
    ctx.rotate((part%2?1:-1)*.6*rest);ctx.scale(.18+.82*q,1);ctx.translate(-96,-64);
    ctx.beginPath();ctx.moveTo(96,64);
    ctx.lineTo(96+140*Math.cos(a-Math.PI/4),64+140*Math.sin(a-Math.PI/4));
    ctx.lineTo(96+140*Math.cos(a+Math.PI/4),64+140*Math.sin(a+Math.PI/4));
    ctx.closePath();ctx.clip();sphere(ctx);ctx.restore();
  }
}
function controller(ctx,light){
  const rows=[
    '..................','..................',
    '....wwwwwwwwww....','....wwwwwwwwww....',
    '..wwwwwwwwwwwwww..','..wwwwwwwwwwwwww..',
    '..wwwwwwwwwwwwww..','..wwwwwwwwwwwwww..',
    '..wwwww....wwwww..','..wwwww....wwwww..',
    '..wwww......wwww..','..wwww......wwww..'
  ];
  ctx.fillStyle=light?'#65717a':'#dce5e9';
  rows.forEach((row,y)=>[...row].forEach((v,x)=>{if(v==='w')ctx.fillRect(x,y,1,1);}));
  // Two readable groups, without tiny sticks and diamond dots competing for pixels.
  ctx.fillStyle='#172126';ctx.fillRect(5,4,1,3);ctx.fillRect(4,5,3,1);
  ctx.fillStyle=light?'#153d09':'#277716';ctx.fillRect(12,4,2,2);
}
function consoleBadge(ctx,light){
  ctx.fillStyle=light?'#303c39':'#87958d';ctx.fillRect(5,0,9,12);
  ctx.fillStyle='#15231c';ctx.fillRect(6,2,7,10);
  ctx.fillStyle='#70c52c';ctx.fillRect(5,0,9,2);
  ctx.fillStyle='#dcebdc';ctx.fillRect(11,4,1,1);
  ctx.fillStyle='#62796a';ctx.fillRect(7,8,1,3);
}
export default {
  id:'xbox',name:'Xbox',subtitle:'像素曲面 · 球体苏醒',accent:'#72c642',wordmark:'XBOX',
  footer:['Jump in','Power Your Dreams','Xbox · Game Pass · Cloud'],
  headerIcon:"X",
  productionVariants:["awaken"],
  variants:[
    {id:'awaken',label:"Sphere awakening",description:'暗绿球体的 X 从中心张开，曲面亮起并收回正常大小；待机短暂左右转身'},
    {id:'fold',label:'B · 曲面翻合 / 回弹',description:'四块曲面从侧面翻入并组成球体；待机蓄力收缩后回弹'}
  ],
  badges:[{id:'controller',label:'像素手柄'},{id:'console',label:'竖直主机'}],
  sources:[{label:'轮廓 · Simple Icons v9',url:'https://github.com/simple-icons/simple-icons/blob/9.0.0/icons/xbox.svg'},{label:'Power Your Dreams',url:'https://news.xbox.com/en-us/2023/10/19/power-your-dreams/'},{label:'Jump in',url:'https://news.xbox.com/en-us/2018/10/22/jump-in-xbox-2018/'}],
  note:'大图采用 Simple Icons 的经典 Xbox 轮廓；手柄、主机小图与球体动画是原创像素适配。Jump in 与 Power Your Dreams 是 Xbox 官方历史品牌活动用语，出处分别为 2018、2023 年 Xbox Wire；第三行为产品名称编排，不是官方宣传语。',
  render(ctx,{phase,t,variant}){
    if(phase==='still'||phase==='intro'&&t>=3||phase==='idle'&&(t<=0||t>=1)){sphere(ctx);return;}
    if(phase==='intro'){(variant==='fold'?fold:awaken)(ctx,t);return;}
    const envelope=Math.sin(Math.PI*t)**2;
    if(variant==='fold')sphere(ctx,{radius:48*(1-.13*envelope*Math.cos(Math.PI*t*2))});
    else sphere(ctx,{yaw:.72*Math.sin(Math.PI*t*2)*envelope});
  },
  mini(ctx,s){(s.badge==='console'?consoleBadge:controller)(ctx,s.light);}
};
