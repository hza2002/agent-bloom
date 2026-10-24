// Build-time only. Invoke exportTheme(id) in this local page, then pass its JSON
// to tools/build_theme_art.py. Installed themes never execute JavaScript.
import { terminalPixels } from './pixels.js';
export async function exportTheme(id) {
  const theme=(await import(`./themes/${id}.js?export=${Date.now()}`)).default;
  const palette=[null],indices=new Map();
  function encode(ctx){
    const {width,height}=ctx.canvas,d=ctx.getImageData(0,0,width,height).data;
    const runs=[];let last=-1,count=0;
    for(let i=0;i<d.length;i+=4){
      let index=0;
      if(d[i+3]>=128){
        const rgb=theme.preserveColours?[d[i],d[i+1],d[i+2]]:
          [d[i],d[i+1],d[i+2]].map(v=>Math.min(255,Math.round(v/2)*2));
        const key=rgb.join(',');
        if(!indices.has(key)){indices.set(key,palette.length);palette.push(rgb);}
        index=indices.get(key);
      }
      if(index===last&&count<65535)count++;
      else {if(count)runs.push(count,last);last=index;count=1;}
    }
    if(count)runs.push(count,last);
    if(palette.length>65535)throw Error('palette overflow');
    const data=new Uint8Array(runs.length*2),view=new DataView(data.buffer);
    runs.forEach((v,i)=>view.setUint16(i*2,v,true));
    let binary='';for(let i=0;i<data.length;i+=8192)binary+=String.fromCharCode(...data.subarray(i,i+8192));
    return btoa(binary);
  }
  const canvas=document.createElement('canvas');canvas.width=192;canvas.height=128;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});
  const selected=theme.productionVariants ?? theme.variants.map(v=>v.id);
  const variants=selected.map(id=>{
    const variant=theme.variants.find(v=>v.id===id);
    if(!variant)throw Error(`unknown production animation: ${id}`);
    return variant;
  });
  const frames={},headers={};
  for(const light of [false,true]){
    const key=light?'light':'dark';frames[key]={intro:{},idle:[]};
    const frame=state=>{ctx.clearRect(0,0,192,128);ctx.save();theme.render(ctx,{...state,light,badge:theme.badges?.[0].id});ctx.restore();return encode(ctx);};
    frames[key].still=frame({phase:'still',t:3});
    for(const variant of variants){
      const list=[];
      for(let i=0;i<=90;i++)list.push(frame({phase:'intro',t:i/30,variant:variant.id}));
      frames[key].intro[variant.id]=list;
    }
    for(let i=0;i<=60;i++)frames[key].idle.push(frame({phase:'idle',t:i/60,variant:variants[0].id}));
    headers[key]={};
    for(const mode of ['octant','quadrant']){
      const c=document.createElement('canvas');c.width=18;c.height=12;const x=c.getContext('2d');
      theme.mini(x,{light,badge:theme.badges?.[0].id});x.clearRect(16,0,2,4);terminalPixels(x,mode);
      headers[key][mode]=encode(x);
    }
  }
  const title=document.createElement('canvas');title.width=192;title.height=36;
  const tx=title.getContext('2d');tx.font='bold 28px monospace';tx.textAlign='center';tx.textBaseline='middle';
  const size=Math.min(28,28*184/tx.measureText(theme.wordmark).width);
  tx.font=`bold ${size}px monospace`;tx.fillStyle='#ffffff';tx.fillText(theme.wordmark,96,18);
  return {format:1,word_bbox:theme.wordBox??[0,0,192,36],header_icon:theme.headerIcon,layout:theme.layout??{},intro_seconds:3,
    preserve_colours:theme.preserveColours===true,id,name:theme.name,wordmark:theme.wordmark,footer:theme.footer,
    accent:theme.accent,sources:theme.sources,note:theme.note,
    variants:variants.map(({id,label})=>({id,label})),fps:30,width:192,height:128,
    palette,frames,headers,word:encode(tx),word_width:192,word_height:36};
}
