"""Shared frame encoding for built-in scenes; terminal ownership stays in Overlay."""
from . import art


def ease_in_out(t):
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


class Scene:
    """Scenes return one-cell glyph/RGB maps inside x0..x1, y0..y1.

    The scheduler owns time and the overlay owns row eligibility. Scenes never
    write to the terminal; this encoder is shared by all built-in animations.
    """
    def invalidate(self):
        """The overlay erased art rows; the next frame must resend them."""
        self.prev_cells.clear()

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
