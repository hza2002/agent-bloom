"""Apple entrances on the terminal's 2x4 sub-pixel lattice.

All motion is a pure function of time and geometry. Scene reconstruction after
resize cannot change the selected variant or introduce fresh random motion.
"""
import math
import random

from .. import art
from ..scene import Scene, ease_in_out


class AppleScene(Scene):
    duration = 3.2

    @property
    def pal(self):
        return self._pal

    @pal.setter
    def pal(self, value):
        self._pal = value
        if hasattr(self, 'mark'):
            self._refresh_draw()

    def _refresh_draw(self):
        self.logo = {(self.top + self.lock.logo_top + r, self.left + c): (ch, rgb)
                     for r, line in enumerate(self.mark.logo_cells(self.pal))
                     for c, (ch, rgb) in enumerate(line) if ch != ' '}
        self.word = {}
        if self.lock.show_word:
            left = self.lock.centre(self.mark.word_cols)
            self.word = {(self.top + self.lock.word_top + r, left + c): (ch, rgb)
                         for r, line in enumerate(self.mark.word_cells(self.pal))
                         for c, (ch, rgb) in enumerate(line) if ch != ' '}

    def __init__(self, cols, rows, pal, brand, lock=None, top=0):
        self.cols, self.rows, self.pal = cols, rows, pal
        self.lock, self.top = lock, top
        self.prev_cells = {}
        self.ok = lock is not None and lock.mark is not None and lock.show_mark
        if not self.ok:
            return
        mark = self.mark = lock.mark
        self.left = lock.centre(mark.logo_cols)
        self.y0 = top
        self.y1 = min(rows, top + (lock.word_top + lock.word_rows
                                  if lock.show_word else mark.logo_rows))
        self.x0, self.x1 = art.GUTTER, cols - art.GUTTER
        self.pixels = []
        self._refresh_draw()
        for r, line in enumerate(mark.logo_bits()):
            for c, bits in enumerate(line):
                if not bits:
                    continue
                row, col = top + lock.logo_top + r, self.left + c
                y = mark.logo_oy + (r * 4 + 2) / mark.ky_sub
                band = min(5, max(0, int((y - 5.7) / 18.3 * 6)))
                for bit in range(8):
                    if bits & (1 << bit):
                        self.pixels.append((col * 2 + bit % 2,
                                            row * 4 + bit // 2, (row, col), band))

    def settled(self):
        return self.logo | self.word

    def raster(self, points):
        """Merge moving sub-pixels into one-cell glyphs, clipped to owned rows."""
        bits, colours = {}, {}
        for x, y, rgb in points:
            x, y = round(x), round(y)
            row, col = y // 4, x // 2
            if self.y0 <= row < self.y1 and self.x0 <= col < self.x1:
                key = row, col
                bits[key] = bits.get(key, 0) | (1 << ((y % 4) * 2 + x % 2))
                colours[key] = rgb
        glyphs = art.glyphs()
        return {key: (glyphs[value], colours[key]) for key, value in bits.items()}

    def add_word(self, cells, t):
        if t <= 1.65:
            return cells
        for (row, col), (ch, rgb) in self.word.items():
            delay = (col - self.lock.centre(self.mark.word_cols)) / max(1, self.mark.word_cols) * .35
            alpha = ease_in_out((t - 1.65 - delay) / .55)
            if alpha:
                cells[row, col] = ch, art.mix(self.pal['bg'], rgb, alpha)
        return cells

    def shine(self, cells, progress, strength=.55):
        centre = self.left + (self.mark.logo_cols + 8) * progress - 4
        for (row, col), (ch, rgb) in list(cells.items()):
            if (row, col) not in self.logo:
                continue
            distance = abs(col - centre - (row - self.y0) * .3)
            amount = max(0, 1 - distance / 3) * strength
            if amount:
                cells[row, col] = ch, art.mix(rgb, self.pal['ink'], amount)
        return cells

    def ambient_frame(self, u):
        """Huawei-style light pass and brief left-to-right wordmark decode."""
        u = min(1, max(0, u))
        cells = self.settled()
        if u == 0 or u == 1:
            return cells
        span = max(1, self.x1 - self.x0)
        height = max(1, self.y1 - self.y0)
        centre = -.25 + 1.5 * ease_in_out(u)
        for key, (ch, colour) in list(cells.items()):
            position = ((key[1] - self.x0) / span +
                        (1 - (key[0] - self.y0) / height) * .45) / 1.45
            glow = max(0, 1 - abs(position - centre) / .12)
            if glow:
                target = self.pal['accent'] if key in self.word else self.pal['ink']
                cells[key] = ch, art.mix(colour, target, .85 * glow)
        if self.word and u < .42:
            left = min(col for _, col in self.word)
            right = max(col for _, col in self.word)
            settled = u / .42
            alphabet = '0123456789ABCDEF'
            step = int(u * 24)
            for (row, col), (ch, colour) in self.word.items():
                if (col - left) / max(1, right - left) <= settled:
                    continue
                # Stable per-cell glyphs avoid random flicker after a redraw.
                glyph = alphabet[(row * 7 + col * 11 + step) % len(alphabet)]
                cells[row, col] = glyph, art.mix(colour, self.pal['accent'], .55)
        return cells


class Spectrum(AppleScene):
    """Six staggered colour bands slide from alternating sides, then catch light."""
    def frame(self, t):
        t = max(0, t)
        if t >= self.duration:
            return self.settled()
        if t < 1.65:
            offsets = []
            for band in range(6):
                u = ease_in_out((t - .08 - band * .10) / 1.05)
                distance = (self.cols + self.mark.logo_cols) * (1 - u)
                offsets.append(distance * (-1 if band % 2 == 0 else 1))
            cells = self.raster((x + offsets[band], y, self.logo[key][1])
                                for x, y, key, band in self.pixels)
        else:
            cells = dict(self.logo)
        self.add_word(cells, t)
        if t > 2.1:
            self.shine(cells, (t - 2.1) / .8 * 1.3)
        return cells


class Constellation(AppleScene):
    """A dispersed field bends into the silhouette and settles without a rim flash."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.ok:
            return
        rng = random.Random(19)
        self.paths = []
        # One travelling light per selected cell, capped for large panes.
        # The solid silhouette fades in beneath them as they arrive.
        targets = list(self.logo.items())
        rng.shuffle(targets)
        for (row, col), _ in targets[:420]:
            x, y = col * 2, row * 4 + 1
            sx = rng.uniform(self.x0 * 2, self.x1 * 2 - 1)
            sy = rng.uniform(self.y0 * 4, self.y1 * 4 - 1)
            self.paths.append((x, y, (row, col), sx, sy, rng.uniform(-9, 9), rng.uniform(0, .45)))

    def frame(self, t):
        t = max(0, t)
        if t >= self.duration:
            return self.settled()
        if t < 2.1:
            points = []
            for x, y, key, sx, sy, bend, delay in self.paths:
                if t < delay:
                    continue
                u = ease_in_out((t - delay) / 1.65)
                arc = math.sin(math.pi * u)
                # Sparse light becomes solid only as particles reach their target.
                alpha = round((.35 + .65 * u) * 12) / 12
                points.append((sx + (x - sx) * u + bend * arc,
                               sy + (y - sy) * u - bend * arc,
                               art.mix(self.pal['bg'], self.logo[key][1], alpha)))
            cells = self.raster(points)
            fill = round(ease_in_out((t - 1.4) / .7) * 12) / 12
            if fill:
                solid = {key: (ch, art.mix(self.pal['bg'], rgb, fill))
                         for key, (ch, rgb) in self.logo.items()}
                # Arrived particles give way to the exact silhouette glyphs.
                cells = {key: value for key, value in cells.items() if key not in solid}
                cells.update(solid)
        else:
            cells = dict(self.logo)
        return self.add_word(cells, t)
