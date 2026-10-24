// Small drawing primitives shared by the internal prototypes, not an animation engine.
export const clamp = t => Math.max(0, Math.min(1, t));
export const ease = t => { t = clamp(t); return t * t * (3 - 2 * t); };
const cache = new Map();
export function path(d) { if (!cache.has(d)) cache.set(d, new Path2D(d)); return cache.get(d); }
export function clip(ctx, x, y, w, h) { ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip(); }
export function grid(ctx, rows, colors) {
  rows.forEach((row, y) => [...row].forEach((key, x) => {
    if (colors[key]) { ctx.fillStyle = colors[key]; ctx.fillRect(x, y, 1, 1); }
  }));
}
export function line(ctx, points, color, width = 2) {
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'butt';
  ctx.beginPath(); points.forEach(([x,y],i) => i ? ctx.lineTo(x,y) : ctx.moveTo(x,y)); ctx.stroke();
}
export function settled(state) {
  return state.phase === 'still' || (state.phase === 'intro' && state.t >= 3)
    || (state.phase === 'idle' && (state.t <= 0 || state.t >= 1));
}

const pixelOutlines = new Map();
// Build-time grid fitting for small details in a vector mark. Output stays binary.
export function pixelOutline(outline, box, columns, rows, omit = []) {
  const key = JSON.stringify([outline, box, columns, rows, omit]);
  if (!pixelOutlines.has(key)) {
    const canvas = document.createElement('canvas');canvas.width=columns;canvas.height=rows;
    const ctx=canvas.getContext('2d',{willReadFrequently:true}), [x,y,width,height]=box;
    ctx.scale(columns/width,rows/height);ctx.translate(-x,-y);ctx.fill(path(outline));
    const pixels=ctx.getImageData(0,0,columns,rows).data, fitted=new Path2D();
    const omitted=new Set(omit.map(([col,row])=>row*columns+col));
    const filled=(col,row)=>!omitted.has(row*columns+col)&&col>=0&&row>=0&&col<columns&&row<rows&&pixels[(row*columns+col)*4+3]>=128;
    // Trace the union boundary; adjacent rectangles otherwise leave antialias seams.
    const edges=new Map();
    const edge=(a,b)=>{const key=a.join(',');if(!edges.has(key))edges.set(key,[]);edges.get(key).push(b);};
    for(let row=0;row<rows;row++)for(let col=0;col<columns;col++) {
      if(!filled(col,row))continue;
      if(!filled(col,row-1))edge([col,row],[col+1,row]);
      if(!filled(col+1,row))edge([col+1,row],[col+1,row+1]);
      if(!filled(col,row+1))edge([col+1,row+1],[col,row+1]);
      if(!filled(col-1,row))edge([col,row+1],[col,row]);
    }
    const point=([col,row])=>[x+col*width/columns,y+row*height/rows];
    while(edges.size) {
      const first=edges.keys().next().value;
      fitted.moveTo(...point(first.split(',').map(Number)));
      let current=first;
      do {
        const next=edges.get(current).pop();
        if(!edges.get(current).length)edges.delete(current);
        fitted.lineTo(...point(next));current=next.join(',');
      } while(current!==first);
      fitted.closePath();
    }
    pixelOutlines.set(key,fitted);
  }
  return pixelOutlines.get(key);
}
