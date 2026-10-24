"""Offline raster artwork on the existing terminal lattice. Standard library only."""
from array import array
import base64
from collections import Counter
from functools import lru_cache
import math
import struct
import zlib

from .. import art
from ..scene import Scene
from ..text_motion import title_cells, intro_title, ambient_title, light_pass


@lru_cache(maxsize=64)
def decode(encoded, width, height):
    raw = zlib.decompress(base64.b64decode(encoded))
    pixels = array('H')
    for count, colour in struct.iter_unpack('<HH', raw):
        if count == 0 or len(pixels) + count > width * height:
            raise ValueError('invalid raster run')
        pixels.extend(array('H', [colour]) * count)
    if len(pixels) != width * height:
        raise ValueError('invalid raster dimensions')
    return pixels


def light_palette(pal):
    return sum(a * b for a, b in zip(pal['bg'], (.2126, .7152, .0722))) > 140


def cells(pixels, sw, sh, width, height, palette, mode, preserve_colours=False, source_box=None):
    """Nearest-neighbour scale, then fit two solid colours into each 2×4 cell.

    Transparent cells reserve the terminal background. No edge antialiasing or
    baked terminal background is introduced. Quadrants share each pair of rows.
    preserve_colours drops unrepresentable edge pixels instead of recolouring them.
    """
    x0, y0, x1, y1 = source_box or (0, 0, sw, sh)
    grid = []
    for y in range(height):
        if mode == 'quadrant':
            y = y // 2 * 2
        sy = min(y1 - 1, y0 + int((y + .5) * (y1-y0) / height))
        grid.append([pixels[sy * sw + min(x1 - 1, x0 + int((x + .5) * (x1-x0) / width))]
                     for x in range(width)])
    rows = []
    for y in range(0, height, 4):
        line = []
        for x in range(0, width, 2):
            block = [grid[yy][xx] if yy < height and xx < width else 0
                     for yy in range(y, y + 4) for xx in range(x, x + 2)]
            colours = Counter(v for v in block if v)
            if not colours:
                line.append((0, None, None))
                continue
            limit=1 if 0 in block else 2
            # A cell cannot encode transparency plus two independent pane colours.
            # Leave a gap instead of painting one pane with its neighbour's ink.
            if preserve_colours and len(colours)>limit:limit=1
            chosen = [i for i, _ in colours.most_common(limit)]
            fg = tuple(palette[chosen[0]])
            bg = tuple(palette[chosen[1]]) if len(chosen) == 2 else None
            bits = 0
            for bit, value in enumerate(block):
                if not value:
                    continue
                if preserve_colours and value not in chosen:
                    continue
                rgb = palette[value]
                if bg is None or sum((a-b)**2 for a, b in zip(rgb, fg)) <= sum((a-b)**2 for a, b in zip(rgb, bg)):
                    bits |= 1 << bit
            line.append((bits, fg, bg))
        rows.append(line)
    return rows


def encoded_rows(rows):
    table = art.glyphs()
    return [[(table[bits], (fg, bg) if bg is not None else fg)
             for bits, fg, bg in line] for line in rows]


class RasterMark:
    def __init__(self, logo_cols, word_rows, asset):
        self.asset = asset
        self.logo_cols = logo_cols
        self.width, self.height = asset['width'], asset['height']
        self.view_box = asset.get('layout', {}).get('view_box', [0, 0, self.width, self.height])
        x0, y0, x1, y1 = self.view_box
        self.logo_rows = math.ceil((y1-y0) * (2*logo_cols/(x1-x0)) / art.SUB_ASPECT / 4)
        self.word_rows = word_rows
        self.word_box = asset.get('word_bbox', [0, 0, asset['word_width'], asset['word_height']])
        wx0, wy0, wx1, wy1 = self.word_box
        self.word_cols = math.ceil(word_rows * 4 / (wy1-wy0) * (wx1-wx0) * art.SUB_ASPECT / 2)

    @lru_cache(maxsize=24)
    def picture(self, encoded, light, mode):
        pixels = decode(encoded, self.width, self.height)
        return encoded_rows(cells(pixels, self.width, self.height, self.logo_cols * 2,
                                  self.logo_rows * 4, self.asset['palette'], mode, self.asset.get('preserve_colours',False), self.view_box))

    def logo_cells(self, pal):
        key = 'light' if light_palette(pal) else 'dark'
        return self.picture(self.asset['frames'][key]['still'], key, art.glyph_mode())

    def logo_bits(self):
        pixels = decode(self.asset['frames']['dark']['still'], self.width, self.height)
        return [[bits for bits, _, _ in line] for line in cells(
            pixels, self.width, self.height, self.logo_cols * 2, self.logo_rows * 4,
            self.asset['palette'], art.glyph_mode(), self.asset.get('preserve_colours', False), self.view_box)]

    @lru_cache(maxsize=16)
    def word_bits(self):
        if not self.word_rows:
            return []
        if self.asset.get('word_polys'):
            x0, y0, x1, y1 = self.word_box
            ky = self.word_rows * 4 / (y1-y0)
            polys = art.snap_polys(self.asset['word_polys'], x0, y0, ky*art.SUB_ASPECT, ky)
            return art.octant_cells(art.cell_fill(polys,self.word_cols*2,self.word_rows*4,fill_rule='nonzero'))
        pixels = decode(self.asset['word'], self.asset['word_width'], self.asset['word_height'])
        return [[bits for bits, _, _ in line] for line in cells(
            pixels, self.asset['word_width'], self.asset['word_height'], self.word_cols * 2, self.word_rows * 4,
            self.asset['palette'], art.glyph_mode(), self.asset.get('preserve_colours', False), self.word_box)]

    def word_cells(self, pal):
        return [[(art.glyphs()[bits], pal['ink'] if bits else None)
                 for bits in line] for line in self.word_bits()]


class RasterScene(Scene):
    duration = 3.0

    def __init__(self, cols, rows, pal, brand, lock=None, top=0, variant=None):
        self.cols, self.rows, self.pal, self.brand = cols, rows, pal, brand
        self.lock, self.top, self.prev_cells = lock, top, {}
        self.ok = lock is not None and lock.mark is not None
        if not self.ok:
            return
        self.mark = lock.mark
        self.duration = self.mark.asset.get('intro_seconds', 3.0)
        self.variant = variant or brand.theme.animations[0].key
        self.x0, self.x1 = art.GUTTER, cols - art.GUTTER
        self.y0 = top
        bottom = lock.word_top + lock.word_rows if lock.show_word else self.mark.logo_rows
        self.y1 = min(rows, top + bottom)

    def _hero(self, phase, value):
        if not self.lock.show_mark:
            return {}
        key = 'light' if light_palette(self.pal) else 'dark'
        frames = self.mark.asset['frames'][key]
        if phase == 'still':
            encoded = frames['still']
        else:
            sequence = frames['intro'][self.variant] if phase == 'intro' else frames['idle']
            index = min(len(sequence)-1, max(0, int(value*(len(sequence)-1)+1e-9)))
            encoded = sequence[index]
        picture = self.mark.picture(encoded, key, art.glyph_mode())
        left = self.lock.centre(self.mark.logo_cols)
        return {(self.top + self.lock.logo_top + r, left + c): (ch, rgb)
                for r, line in enumerate(picture) for c, (ch, rgb) in enumerate(line)
                if ch != ' ' and self.y0 <= self.top + self.lock.logo_top + r < self.y1
                and self.x0 <= left+c < self.x1}

    def _word(self, t=None, idle=None):
        if not self.lock.show_word:
            return {}
        word = title_cells(self.mark, self.lock, self.top, self.pal)
        if t is not None:
            return intro_title(word, self.pal, t,
                               self.lock.centre(self.mark.word_cols), self.mark.word_cols)
        if idle is not None and 0 < idle < 1:
            light_pass(word, self.pal, (self.x0, self.y0, self.x1, self.y1), idle, word)
            ambient_title(word, dict(word), self.pal, idle)
        return word

    def settled(self):
        return self._hero('still', 1) | self._word()

    def frame(self, t):
        if t >= self.duration:
            return self.settled()
        return self._hero('intro', max(0, t)/self.duration) | self._word(t=max(0, t))

    def ambient_frame(self, progress):
        if progress <= 0 or progress >= 1:
            return self.settled()
        return self._hero('idle', progress) | self._word(idle=progress)
