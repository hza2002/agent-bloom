"""Generate pixel studies using actual terminal cells: <= 2 colours per cell."""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from agent_theme import art

# Preserve the accepted proportions; only trim the lower bite edge.
shape = [
    '..........111.....',
    '.........111......',
    '..................',
    '.....111..111.....',
    '....1111111111....',
    '...1111111111.....',
    '...111111111......',
    '...111111111......',
    '....111111111.....',
    '....1111111111....',
    '.....11111111.....',
    '......111.11......',
]
fallback = [
    '..........11......',
    '..................',
    '.....111.1111.....',
    '....11111111......',
    '....111111111.....',
    '.....1111111......',
]
bands = ['#61b748', '#f5cf48', '#ef963d', '#de544d', '#a65c9b', '#488fca']

def encode(pixels, mode, style, light):
    """Preserve transparent boundary cells; split solid cells with half blocks."""
    height = 4 if mode == 'octant' else 2
    ink = '#333a40' if light else '#eef1f2'
    silver = '#7d8b99' if light else '#a8b8c7'
    colors = [bands[min(5, y // 2)] if style == 'rainbow' else ink for y in range(12)]
    if mode == 'quadrant': colors = colors[::2]
    output = [[None] * 18 for _ in pixels]
    lines = []
    for r in range(3):
        line = ''
        for c in range(9):
            occupied = [(yy, xx) for yy in range(height) for xx in range(2)
                        if pixels[r * height + yy][c * 2 + xx] == '1']
            fg, bg = ink, None
            bits = 0
            if occupied:
                if style == 'rainbow':
                    # A full cell can use two real stripe colours. At the edge,
                    # the second colour must remain transparent terminal bg.
                    if len(occupied) == height * 2:
                        fg, bg = colors[r * height], colors[(r + 1) * height - 1]
                    else:
                        y = round(sum(p[0] for p in occupied) / len(occupied))
                        fg = bands[0] if r == 0 and any(yy < height / 2 for yy, _ in occupied) else colors[r * height + y]
                elif style == 'silver':
                    fg = silver if r > 0 and c >= 5 else ink
                    if len(occupied) == height * 2 and c == 4:
                        bg = silver
                for yy, xx in occupied:
                    foreground = bg is None or (yy < height / 2 if style == 'rainbow' else xx == 0)
                    color = fg if foreground else bg
                    output[r * height + yy][c * 2 + xx] = color
                    if foreground:
                        if mode == 'octant': bits |= 1 << (yy * 2 + xx)
                        else: bits |= 1 << (yy * 4 + xx) | 1 << (yy * 4 + 2 + xx)
            def sgr(color, channel):
                if color is None: return '\x1b[49m'
                return '\x1b[%s;2;%s;%s;%sm' % (channel, *(int(color[i:i+2],16) for i in (1,3,5)))
            line += sgr(bg, 48) + sgr(fg, 38) + art.OCTANT_TABLE[bits]
        lines.append(line + '\x1b[0m')
    return output, '\n'.join(lines) + '\n'

variants = []
for key, name, note in (
    ('rainbow', '经典六色', '保留六色顺序。内部用前景色＋背景色分出半高色带，边缘留空。'),
    ('silver', '银白双色', '亮银主体与冷银侧面，以明确色块表达层次，不做灰色抗锯齿边。'),
    ('mono', '新轮廓 · 单色', '与彩色版共用轮廓，直接判断改进来自造型还是颜色。'),
    ('current', '原比例六色 · 对照', '保留加宽前的六色稿；与新版对比右侧咬口，主体没有横向拉伸。')):
    v = dict(id=key, name=name, note=note, kind='像素设计' if key != 'current' else '基准', grids={}, colorGrids={})
    for mode in ('octant','quadrant'):
        pixels = shape if mode == 'octant' else fallback
        if key == 'current':
            previous = json.loads((HERE / 'previous-shape.json').read_text())
            pixels = previous['shape'] if mode == 'octant' else previous['fallback']
        v['grids'][mode] = [[int(x == '1') for x in row] for row in pixels]
        v['colorGrids'][mode] = {}
        for palette in ('dark','light'):
            result, ansi = encode(pixels, mode, 'rainbow' if key == 'current' else key, palette == 'light')
            v['colorGrids'][mode][palette] = result
            (HERE / f'{key}-{mode}-{palette}.ansi').write_text(ansi)
    variants.append(v)
(HERE / 'design-data.js').write_text('const DATA = ' + json.dumps(dict(variants=variants, versions={
    'method':'真实字符编码：每个字符最多两个颜色；边界保留终端背景。',
    'size':'9 列 × 3 行；半高、四分块与八分块；不混合灰色边缘。'}),ensure_ascii=False) + ';\n')
print('Generated 4 designs and 16 ANSI samples.')
