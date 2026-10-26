// Canvas playback is independent of theme selection, installation and page navigation.
type RGB = [number, number, number];
type Cell = [string, RGB | [RGB, RGB], boolean];
export type Clip = {tokens: Cell[]; frames: [number, number[]][]};

export function createTerminalPlayer(canvas: HTMLCanvasElement, geometry: {cols: number; rows: number; cellRatio: number; glyphs: string[]}) {
  const context = canvas.getContext('2d')!;
  const {cols, rows, cellRatio} = geometry;
  const glyphs = new Map(Array.from(geometry.glyphs).map((char, bits) => [char, bits]));
  const cellWidth = 8, cellHeight = cellWidth * cellRatio;
  canvas.width = cols * cellWidth;
  canvas.height = Math.ceil(rows * cellHeight);
  let clip: Clip | null = null;
  let background: number[] = [];
  let request = 0;

  function stop() {
    cancelAnimationFrame(request);
    clip = null;
  }

  function draw(position: number, token: number) {
    const x = position % cols * cellWidth;
    const y = Math.floor(position / cols) * cellHeight;
    context.fillStyle = `rgb(${background.join(',')})`;
    context.fillRect(x, Math.round(y), cellWidth, Math.round(y + cellHeight) - Math.round(y));
    if (token === -1) return;
    const [char, rgb, bold] = clip!.tokens[token];
    const paired = Array.isArray(rgb[0]);
    const foreground = paired ? (rgb as [RGB, RGB])[0] : rgb as RGB;
    if (paired) {
      context.fillStyle = `rgb(${(rgb as [RGB, RGB])[1].join(',')})`;
      context.fillRect(x, Math.round(y), cellWidth, Math.round(y + cellHeight) - Math.round(y));
    }
    context.fillStyle = `rgb(${foreground.join(',')})`;
    const bits = glyphs.get(char);
    if (bits === undefined) {
      context.font = `${bold ? 'bold ' : ''}13px monospace`;
      context.fillText(char, x, y + cellHeight * .78);
      return;
    }
    for (let bit = 0; bit < 8; bit++) {
      if (!(bits & (1 << bit))) continue;
      const top = Math.round(y + Math.floor(bit / 2) * cellHeight / 4);
      const bottom = Math.round(y + (Math.floor(bit / 2) + 1) * cellHeight / 4);
      context.fillRect(x + bit % 2 * 4, top, 4, bottom - top);
    }
  }

  function play(data: Clip, colour: number[], onFinish: () => void) {
    stop();
    clip = data;
    background = colour;
    context.fillStyle = `rgb(${background.join(',')})`;
    context.fillRect(0, 0, canvas.width, canvas.height);
    const start = performance.now();
    let frame = 0;
    const tick = (now: number) => {
      if (!clip) return;
      while (frame < clip.frames.length && clip.frames[frame][0] <= now - start) {
        const changes = clip.frames[frame++][1];
        for (let index = 0; index < changes.length; index += 2) draw(changes[index], changes[index + 1]);
      }
      if (frame === clip.frames.length) {
        stop();
        onFinish();
        return;
      }
      request = requestAnimationFrame(tick);
    };
    request = requestAnimationFrame(tick);
  }

  return {play, stop};
}
