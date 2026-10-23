"""Build real tool outputs for the comparison page; no runtime dependencies."""
import json
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / 'agent_theme/themes/assets'

def run(*args):
    return subprocess.check_output(list(map(str, args)))

def grid(raw, height):
    return [[int(v >= 128) for v in raw[y * 18:(y + 1) * 18]] for y in range(height)]

with tempfile.TemporaryDirectory() as directory:
    temp = Path(directory)
    run('resvg', '--width', '1024', ASSETS / 'apple.svg', temp / 'source.png')
    # Physical canvas: nine cells wide, three cells high, cell H/W = 2.12.
    run('magick', temp / 'source.png', '-alpha', 'extract', '-resize', '1018x1018',
        '-background', 'black', '-gravity', 'center', '-extent', '1440x1018', temp / 'mask.png')
    asset = json.loads((ASSETS / 'apple.json').read_text())
    variants = [{'id': 'current', 'name': '当前手工小标', 'kind': '基准',
                 'note': '项目现有的光学校正稿，用来与自动转换比较。', 'grids': {
                     'octant': [[int(c == '1') for c in row] for row in asset['mini_grid']],
                     'quadrant': [[int(c == '1') for c in row] for row in asset['mini_grid_quadrant'][::2]]}}]
    for key, name, filt, threshold in (
            ('box42', '面积采样 · 42%', 'Box', 42),
            ('box50', '面积采样 · 50%', 'Box', 50),
            ('box60', '面积采样 · 60%', 'Box', 60),
            ('lanczos', 'Lanczos · 50%', 'Lanczos', 50),
            ('nearest', '最近邻 · 50%', 'Point', 50)):
        item = dict(id=key, name=name, kind='ImageMagick', note={
            'box42': '低阈值保留更多边缘，轮廓更饱满，也可能连起叶片。',
            'box50': '按像素覆盖面积取舍，作为中性自动转换基准。',
            'box60': '高阈值收紧轮廓，观察叶片与咬口能否保留。',
            'lanczos': '先滤波缩小，再二值化；最终没有灰边。',
            'nearest': '直接选取原图像素，观察细节遗漏与阶梯变化。'}[key], grids={})
        for mode, height in (('octant', 12), ('quadrant', 6)):
            raw = run('magick', temp / 'mask.png', '-filter', filt, '-resize', f'18x{height}!',
                      '-threshold', f'{threshold}%', '-depth', '8', 'gray:-')
            assert len(raw) == 18 * height
            item['grids'][mode] = grid(raw, height)
        variants.append(item)
    command = ['chafa', '-f', 'symbols', '--symbols', 'quad+space', '--fill', 'none',
               '--colors', 'none', '--fg', 'white', '--bg', 'black', '--preprocess', 'off',
               '--dither', 'none', '--size', '9x3', '--stretch', '--font-ratio', '50/106',
               '--work', '9', '--optimize', '0', '--probe', 'off', '--polite', 'on', temp / 'mask.png']
    output = run(*command).decode()
    (HERE / 'chafa.txt').write_text('\n'.join(line.rstrip() for line in output.splitlines()) + '\n')
    rows = output.splitlines()
    assert len(rows) == 3, repr(output)
    quad = ' ▘▝▀▖▌▞▛▗▚▐▜▄▙▟█'
    pixels = [[0] * 18 for _ in range(6)]
    for y, line in enumerate(rows):
        assert len(line) <= 9
        for x, char in enumerate(line):
            bits = quad.index(char)
            for bit in range(4):
                pixels[y * 2 + bit // 2][x * 2 + bit % 2] = (bits >> bit) & 1
    variants.append(dict(id='chafa', name='Chafa · 字形匹配', kind='Chafa',
                         note='真实四分块字符输出。切换八分块时仍保持 6 层精度，不虚构额外细节。',
                         grids=dict(quadrant=pixels, octant=[row for row in pixels for _ in range(2)])))
    (HERE / 'source.svg').write_bytes((ASSETS / 'apple.svg').read_bytes())
    data = dict(variants=variants, versions={
        name: run(*command).decode().splitlines()[0] for name, command in (
            ('Chafa', ['chafa', '--version']), ('ImageMagick', ['magick', '-version']),
            ('resvg', ['resvg', '--version']))})
    (HERE / 'data.js').write_text('const DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n')
    print('Generated', len(variants), 'variants:', data['versions'])
