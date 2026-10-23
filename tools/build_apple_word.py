"""Bake Inter Medium's APPLE outlines; no font dependency at runtime.

Regenerate with: uv run --with fonttools tools/build_apple_word.py InterVariable.ttf
Source: https://github.com/rsms/inter/blob/v4.1/docs/font-files/InterVariable.ttf
"""
import hashlib
import json
from pathlib import Path
import sys

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont


class OutlinePen(BasePen):
    def __init__(self, glyphs):
        super().__init__(glyphs)
        self.contours = []

    def _moveTo(self, point):
        self.contours.append([point])

    def _lineTo(self, point):
        self.contours[-1].append(point)

    def _curveToOne(self, a, b, c):
        start = self._getCurrentPoint()
        for step in range(1, 33):
            t, u = step / 32, 1 - step / 32
            self._lineTo(tuple(u**3 * start[i] + 3*u*u*t*a[i] +
                               3*u*t*t*b[i] + t**3*c[i] for i in range(2)))

    def _qCurveToOne(self, a, b):
        start = self._getCurrentPoint()
        for step in range(1, 33):
            t, u = step / 32, 1 - step / 32
            self._lineTo(tuple(u*u*start[i] + 2*u*t*a[i] + t*t*b[i] for i in range(2)))

    def _closePath(self):
        pass

    def _endPath(self):
        pass


def build(font_path):
    font = TTFont(font_path)
    glyphs = font.getGlyphSet(location={'wght': 500, 'opsz': 32})
    cmap = font.getBestCmap()
    contours, left = [], 0
    for letter in 'APPLE':
        glyph = glyphs[cmap[ord(letter)]]
        pen = OutlinePen(glyphs)
        glyph.draw(pen)
        contours.extend([[(x + left, -y) for x, y in line] for line in pen.contours])
        left += glyph.width + font['head'].unitsPerEm * .015
    xs = [x for line in contours for x, _ in line]
    ys = [y for line in contours for _, y in line]
    scale = 9 / (max(ys) - min(ys))
    polys = [[(round((x - min(xs)) * scale, 5), round((y - min(ys)) * scale, 5))
              for x, y in line] for line in contours]
    data = {'source': 'APPLE set in Inter 4.1 Medium, optical size 32; SIL OFL 1.1',
            'font_sha256': hashlib.sha256(Path(font_path).read_bytes()).hexdigest(),
            'word': polys, 'word_bbox': [0, 0, round((max(xs) - min(xs)) * scale, 5), 9]}
    path = Path(__file__).resolve().parents[1] / 'agent_theme/themes/assets/apple-word.json'
    path.write_text(json.dumps(data, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    build(sys.argv[1])
