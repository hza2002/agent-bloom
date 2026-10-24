// Each terminal cell holds at most a foreground and a background colour.
// Transparent edge cells keep transparency plus a single foreground colour.
export function terminalPixels(ctx, mode, preserveColours = false) {
  const {width:w,height:h}=ctx.canvas;
  const frame=ctx.getImageData(0,0,w,h), d=frame.data;
  for(let i=0;i<d.length;i+=4){d[i+3]=d[i+3]>=128?255:0;}
  if(mode==='quadrant'){
    for(let y=0;y<h;y+=2)for(let x=0;x<w;x++){
      const a=(y*w+x)*4,b=((y+1)*w+x)*4;
      const source=d[a+3]>=128?a:b;
      for(let k=0;k<4;k++){const v=d[source+k];d[a+k]=v;d[b+k]=v;}
    }
  }
  for(let y=0;y<h;y+=4)for(let x=0;x<w;x+=2){
    const pixels=[],counts=new Map();let transparent=false;
    for(let dy=0;dy<4;dy++)for(let dx=0;dx<2;dx++){
      if(y+dy>=h||x+dx>=w)continue;
      const i=((y+dy)*w+x+dx)*4;pixels.push(i);
      if(!d[i+3]){transparent=true;continue;}
      const color=(d[i]<<16)|(d[i+1]<<8)|d[i+2];counts.set(color,(counts.get(color)||0)+1);
    }
    const limit=preserveColours&&counts.size>(transparent?1:2)?1:(transparent?1:2);
    const palette=[...counts].sort((a,b)=>b[1]-a[1]).slice(0,limit).map(([v])=>[v>>16,(v>>8)&255,v&255]);
    for(const i of pixels){if(!d[i+3])continue;let best=palette[0],dist=Infinity;
      for(const c of palette){const n=(d[i]-c[0])**2+(d[i+1]-c[1])**2+(d[i+2]-c[2])**2;if(n<dist){best=c;dist=n;}}
      if(preserveColours&&!palette.some(c=>c[0]===d[i]&&c[1]===d[i+1]&&c[2]===d[i+2])){d[i+3]=0;continue;}
      d[i]=best[0];d[i+1]=best[1];d[i+2]=best[2];
    }
  }
  ctx.putImageData(frame,0,0);
}
