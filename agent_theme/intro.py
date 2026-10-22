"""Opening animation: the Huawei flower blooms out of code.

Timeline of the bloom (seconds):
  0.00  a red cursor blinks where the petals meet
  0.30  the bud grows out of the cursor and fans open, inner pair first; the leading
        edge of every petal is drawn in code glyphs that settle into solid colour
  1.15  HUAWEI decodes from random code glyphs, left to right
  2.05  a light sweep crosses the mark
  end   hand-off: the mark stays exactly where the home page draws it
"""
import math
import random

from . import art

BLOOM_SECONDS = 2.95
CODE = '0101010110{}<>/=;+*#'
# During each ambient sweep the wordmark re-settles from code; this fraction of
# the sweep is the decode, the rest is the normal light pass.
AMBIENT_DECODE_FRACTION = 0.45
HOT = (255, 104, 88)
FLASH = (255, 255, 255)
SHINE = (255, 236, 226)


def ease_out_cubic(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return 1 - (1 - t) ** 3


def ease_out_back(t, s=1.25):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


def ease_in_out(t):
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    return t * t * (3 - 2 * t)


class Bloom:
    def __init__(self, cols, rows, pal, brand, bloom_length=BLOOM_SECONDS,
                 lock=None, top=0):
        self.cols, self.rows, self.pal = cols, rows, pal
        self.duration = bloom_length
        if lock is None:
            self.lock = None
            self.mark = None
            self.ok = False
            return
        self.top = top
        self.lock = lock
        self.mark = mark = self.lock.mark
        # The Bloom is the mark's entrance; word-only and text-only fallbacks
        # go straight to the static home.
        self.ok = mark is not None and lock.show_mark
        if not self.ok:
            return
        self.lx = self.lock.centre(mark.logo_cols)
        self.ly = self.top + self.lock.logo_top
        self.wx = self.lock.centre(mark.word_cols)
        self.wy = self.top + self.lock.word_top
        ox, oy = mark.svg_to_cell(*art.ART['origin'])
        # Origin in screen sub-pixels; physical units scale y by the sub-pixel aspect.
        self.ox = self.lx * 2 + ox
        self.oy = (self.ly * 4 + oy) * art.SUB_ASPECT
        self.petals = []
        lb = art.ART['logo_bbox']
        cx_axis = (lb[0] + lb[2]) / 2
        for poly in art.ART['petals']:
            pts = self._outline(poly)
            if not pts:
                continue
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            angle = math.atan2(mx, -my)  # from straight up, clockwise positive
            centroid_x = sum(p[0] for p in poly) / len(poly)
            self.petals.append({'poly': pts, 'angle': angle, 'side': centroid_x > cx_axis})
        # Inner pair opens first, the low outer pair last.
        order = sorted({round(abs(p['angle']), 1) for p in self.petals})
        for p in self.petals:
            p['rank'] = order.index(round(abs(p['angle']), 1))
        # Every petal is exactly at its final angle once the last one finishes easing.
        self.posed = 0.36 + 0.075 * max((p['rank'] for p in self.petals), default=0) + 0.82
        self.final = mark.logo_bits()
        octants = art.glyphs()
        self.pose_cells = {(self.ly + r, self.lx + c): bits
                           for r, line in enumerate(self.final)
                           for c, bits in enumerate(line) if bits}
        # The settled mark never changes; resolve its glyphs and gradient once.
        self.final_draw = {(self.ly + r, self.lx + c): (octants[bits], mark.logo_color(r, c))
                           for r, line in enumerate(self.final)
                           for c, bits in enumerate(line) if bits}
        # Cell-level output cache. A few hundred KB is cheap next to resending
        # the settled logo and the cells outside the sweep every frame.
        self.prev_cells = {}
        self.word = mark.word_bits() if lock.show_word else []
        rng = random.Random(7)
        self.word_lock = {}
        for r, line_bits in enumerate(self.word):
            for c, bits in enumerate(line_bits):
                if bits:
                    self.word_lock[(r, c)] = 1.15 + 0.62 * c / max(1, len(line_bits)) + rng.uniform(0, 0.1)
        # The word stops changing after its last cell finishes fading.
        self.word_settled = max(self.word_lock.values(), default=0) + 0.22
        self.word_span = (min(self.word_lock.values(), default=0.0),
                          max(self.word_lock.values(), default=0.0))
        self.word_ink = pal['ink']
        self.word_draw = {(self.wy + r, self.wx + c): (octants[self.word[r][c]], pal['ink'])
                          for r, c in self.word_lock}
        self.born = {}
        self.base_colors = {}  # Moving cells reuse the same clamped logo gradient.
        self.spin = {}
        self.word_spin = {}
        self.rng = random.Random()
        # Region we repaint every frame (the bud overshoots the logo box a little).
        self.x0 = max(0, min(self.lx, self.wx) - 2)
        self.x1 = min(cols, max(self.lx + mark.logo_cols, self.wx + mark.word_cols) + 2)
        self.y0 = max(0, self.ly - 1)
        bottom = self.ly + mark.logo_rows
        if lock.show_word:
            bottom = max(bottom, self.wy + mark.word_rows)
        self.y1 = min(rows, bottom + 1)

    def _outline(self, poly):
        """Petal outline in bloom-local units (sub-pixel x, physical y)."""
        mark = self.mark
        kx, ky = mark.kx, mark.ky_sub * art.SUB_ASPECT
        ox, oy = mark.logo_ox, mark.logo_oy
        base_x = self.lx * 2 - self.ox
        base_y = self.ly * 4 * art.SUB_ASPECT - self.oy
        return [((x - ox) * kx + base_x, (y - oy) * ky + base_y) for x, y in poly]

    def _petal_cells(self, t):
        """Octant bits per screen cell for the blooming petals at time t.

        Each petal outline is transformed and filled with sub-pixel coverage.
        Sampling the polygon (rather than sprinkling pre-sampled points) keeps
        the leading edges solid and steady while the flower opens.
        """
        grow = ease_out_cubic((t - 0.30) / 0.75)
        if grow <= 0:
            return {}
        if t >= self.posed:
            return self.pose_cells
        scale = 0.22 + 0.78 * grow
        aspect = art.SUB_ASPECT
        ox, oy = self.ox, self.oy
        cells = {}
        for petal in self.petals:
            open_ = ease_out_back((t - 0.36 - 0.075 * petal['rank']) / 0.82)
            delta = -petal['angle'] * 0.94 * (1 - open_)
            c, s = math.cos(delta) * scale, math.sin(delta) * scale
            poly = [(ox + px * c - py * s, (oy + px * s + py * c) / aspect)
                    for px, py in petal['poly']]
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            x0, x1 = max(0, math.floor(min(xs))), min(self.cols * 2, math.ceil(max(xs)) + 1)
            y0, y1 = max(0, math.floor(min(ys))), min(self.rows * 4, math.ceil(max(ys)) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            # One sample per sub-pixel row matches the three-sample edge on all
            # but a handful of cells and cuts the growth phase's cost by ~25%.
            part = art.coverage([poly], x1 - x0, y1 - y0, x0, y0, 1.0, 1.0, samples=1)
            for j, row in enumerate(part):
                sy = y0 + j
                cell_row, dy = sy >> 2, (sy & 3) * 2
                for i, v in enumerate(row):
                    if v >= 0.5:
                        sx = x0 + i
                        key = (cell_row, sx >> 1)
                        cells[key] = cells.get(key, 0) | (1 << (dy + (sx & 1)))
        return cells

    def _glyph(self, spin, key, t, hz=20.0):
        """A code glyph that changes at a fixed, readable rate (not every frame)."""
        step = int(t * hz)
        rec = spin.get(key)
        if rec is None or rec[0] != step:
            rec = (step, self.rng.choice(CODE))
            spin[key] = rec
        return rec[1]

    def invalidate(self):
        """The overlay erased art rows; the next frame must resend them."""
        self.prev_cells.clear()

    def frame(self, t):
        """Cells {(row, col): (char, rgb)} at time t."""
        return self._bloom(t)

    def _bloom(self, t):
        out = {}
        pal = self.pal
        mix = art.mix
        octants = art.glyphs()
        settled = t >= 1.62
        if t < 0.30:
            on = t < 0.11 or 0.19 <= t
            if on:
                out[(int(self.oy / art.SUB_ASPECT) >> 2, int(self.ox) >> 1)] = ('█', art.ART['gradient']['stops'][1][1])
        elif settled:
            out.update(self.final_draw)
        else:
            mark = self.mark
            cells = self._petal_cells(t)
            heat = ease_out_cubic((t - 0.3) / 1.1)
            deep = tuple(art.ART['gradient']['stops'][2][1])
            logo_color = mark.logo_color
            born = self.born
            for key in list(born):
                if key not in cells:
                    del born[key]
                    self.spin.pop(key, None)
            for key, bits in cells.items():
                row, col = key
                first = born.setdefault(key, t)
                base = self.base_colors.get(key)
                if base is None:
                    base = self.base_colors[key] = logo_color(
                        min(max(row - self.ly, 0), mark.logo_rows - 1),
                        min(max(col - self.lx, 0), mark.logo_cols - 1))
                colour = base if heat >= 1 else mix(deep, base, heat)
                age = t - first
                # The bud condenses out of code; afterwards only moving edges sparkle.
                if age < 0.12 and (bits != 255 or t < 0.52):
                    out[key] = (self._glyph(self.spin, key, t), mix(HOT, colour, age / 0.12))
                else:
                    out[key] = (octants[bits], colour if age >= 0.22 else mix(HOT, colour, age / 0.22))
        bg = pal['bg']
        if t >= self.word_settled:
            if self.word_ink != pal['ink']:
                self.word_ink = pal['ink']
                self.word_draw = {key: (ch, self.word_ink)
                                  for key, (ch, _) in self.word_draw.items()}
            out.update(self.word_draw)
        else:
            for (r, c), lock in self.word_lock.items():
                if t < lock - 0.34:
                    continue
                key = (self.wy + r, self.wx + c)
                if t < lock:
                    out[key] = (self._glyph(self.word_spin, key, t),
                                mix(bg, (190, 70, 74), (t - lock + 0.34) / 0.2))
                else:
                    out[key] = (octants[self.word[r][c]], mix(FLASH, pal['ink'], (t - lock) / 0.22))
        self._sweep(out, t)
        return out

    def _sweep(self, out, t):
        """Apply the light pass at timeline time t, in place."""
        sweep = (t - 2.02) / 0.7
        if not 0 < sweep < 1:
            return
        centre = -0.25 + 1.5 * ease_in_out(sweep)
        span = max(1, self.x1 - self.x0)
        height = max(1, self.y1 - self.y0)
        pal = self.pal
        for key, (ch, colour) in out.items():
            u = ((key[1] - self.x0) / span + (1 - (key[0] - self.y0) / height) * 0.45) / 1.45
            glow = 1 - abs(u - centre) / 0.085
            if glow > 0:
                # A white shine reads on the red mark but disappears on the
                # near-white wordmark; lift that copy to the brand red.
                target = pal['red'] if key in self.word_draw else SHINE
                out[key] = (ch, art.mix(colour, target, 0.7 * glow * glow))

    def ambient_frame(self, u):
        """Settled home plus the ambient light pass and a short word decode."""
        u = 0.0 if u < 0 else 1.0 if u > 1 else u
        cells = self._bloom(self.duration)
        self._sweep(cells, 2.02 + u * 0.7)
        if not self.word_lock:
            return cells
        lo, hi = self.word_span
        span = max(1e-6, hi - lo)
        settle = min(1.0, u / AMBIENT_DECODE_FRACTION)
        step = u * 2.0
        for (r, c), lock in self.word_lock.items():
            if (lock - lo) / span <= settle:
                continue
            key = (self.wy + r, self.wx + c)
            rec = cells.get(key)
            if rec is None:
                continue
            ch, colour = rec
            # Code glyphs flash in the brand colour, then resolve to the ink
            # wordmark; this is the intro's decode, replayed briefly.
            colour = art.mix(colour, self.pal['red'], 0.35)
            cells[key] = (self._glyph(self.word_spin, key, step), colour)
        return cells

    def ansi(self, cells, rows=None):
        """ANSI for the frame, writing only the cells that changed.

        Every character in this scene is one cell wide (octants, spaces and the
        ASCII code glyphs), so a run is a simple column range.
        """
        get = cells.get
        prev = self.prev_cells
        parts = []
        for row in (range(self.y0, self.y1) if rows is None else rows):
            # The default tuple is shared, so unchanged empty cells compare equal.
            new = [get((row, col), (' ', None)) for col in range(self.x0, self.x1)]
            old = prev.get(row)
            prev[row] = new
            if old == new:
                continue
            if old is None or len(old) != len(new):
                first, last = 0, len(new) - 1
            else:
                first = 0
                while new[first] == old[first]:
                    first += 1
                last = len(new) - 1
                while new[last] == old[last]:
                    last -= 1
            parts.append('\x1b[%d;%dH' % (row + 1, self.x0 + first + 1))
            parts.append(art.render_run([(ch, colour, False)
                                         for ch, colour in new[first:last + 1]]))
        if not parts:
            return ''
        return '\x1b[?2026h' + ''.join(parts) + '\x1b[0m\x1b[?2026l'
