// Shared preview of the terminal lockup's decode, staggered reveal and idle sheen.
// Theme modules own only the hero animation and palette, never copy timing.
const clamp=t=>Math.max(0,Math.min(1,t));
const ease=t=>{t=clamp(t);return t*t*(3-2*t);};
const CODE='01<>/{}';
function set(node,key,value){if(node.style[key]!==value)node.style[key]=value;}
function run(element,decode=false){
  const text=element.textContent;
  element.setAttribute('aria-label',text);
  const wrapper=document.createElement('span');wrapper.className='copy-run';wrapper.setAttribute('aria-hidden','true');
  const cells=[...text].map((char,i)=>{
    const node=document.createElement('span');node.className='copy-cell';
    const glyph=document.createElement('span');glyph.textContent=char;node.append(glyph);
    let code;
    if(decode&&char.trim()){
      code=document.createElement('span');code.className='copy-code';node.append(code);
    }
    wrapper.append(node);return {node,glyph,code,i,char};
  });
  element.replaceChildren(wrapper);return {element,cells};
}
export function createCopyMotion(root){
  const title=run(root.querySelector('.wordmark'),true);
  const lines=['strong','.tagline','.platform'].map(selector=>run(root.querySelector('.footer-copy '+selector)));
  return function renderCopy(state){
    const intro=state.phase==='intro',idle=state.phase==='idle'&&state.t>0&&state.t<1;
    const t=state.t;
    title.cells.forEach(({node,glyph,code,i,char})=>{
      const position=i/Math.max(1,title.cells.length-1);
      const lock=1.12+.62*position;
      const entering=intro?ease((t-lock)/.28):1;
      const band=idle?Math.abs(position-((t-.06)/.36)):2;
      const decoding=code&&(intro?t>=lock-.16&&t<lock:band<.12&&t>.06&&t<.45);
      set(node,'opacity',String(decoding?1:entering));
      set(glyph,'visibility',decoding?'hidden':'visible');
      if(code){
        code.textContent=decoding?CODE[(i*3+Math.floor(t*12))%CODE.length]:'';
        set(code,'visibility',decoding?'visible':'hidden');
      }
      set(node,'color',idle&&band<.2?'var(--theme-accent)':'');
    });
    lines.forEach(({element,cells},row)=>{
      const delay=[1.65,1.95,2.1][row];
      set(element,'opacity',String(intro?ease((t-delay)/.6):1));
      cells.forEach(({node,i})=>{
        const position=i/Math.max(1,cells.length-1);
        set(node,'opacity',String(intro&&row===0?ease((t-delay-position*.08)/.45):1));
        const band=idle?Math.abs(position-(-.2+1.4*t)):2;
        // Middle line stays readable; first and third share the ambient colour pass.
        set(node,'color',idle&&row!==1&&band<.13?
          (row===0?'var(--theme-accent)':'var(--fg)'):'');
      });
    });
  };
}
