"""Shared title effects. Themes supply artwork; the scheduler supplies time.

The default is the approved Apple timing. Huawei keeps its established timings
and glyph source through the same effects, without moving policy into themes.
The three small-copy lines already share art.small_text_rows and animation.py.
"""
from dataclasses import dataclass

from . import art
from .scene import ease_in_out


@dataclass(frozen=True)
class TitleTiming:
    start: float = 1.65
    stagger: float = .35
    fade: float = .55
    lead: float = 0
    lead_colour: tuple = None
    lead_fade: float = 0
    flash: tuple = None
    smooth: bool = True


DEFAULT_TIMING = TitleTiming()


def title_cells(mark, lock, top, pal):
    """Place a title independently of the large graphic or its renderer."""
    if not lock.show_word:
        return {}
    left = lock.centre(mark.word_cols)
    return {(top + lock.word_top + r, left + c): (ch, rgb)
            for r, line in enumerate(mark.word_cells(pal))
            for c, (ch, rgb) in enumerate(line) if ch != ' '}


def intro_title(word, pal, t, left, width, timing=DEFAULT_TIMING,
                locks=None, glyph=None):
    """Reveal complete title cells left to right, with optional code prelude.

    Explicit cell lock times and a glyph callback preserve Huawei's seeded
    cadence. New themes use the default fade; they need no title-motion code.
    """
    out = {}
    for key, (ch, rgb) in word.items():
        lock = (locks[key] if locks is not None else
                timing.start + (key[1] - left) / max(1, width) * timing.stagger)
        if t < lock - timing.lead:
            continue
        if t < lock:
            colour = timing.lead_colour or pal['accent']
            if timing.lead_fade:
                colour = art.mix(pal['bg'], colour,
                                 (t - lock + timing.lead) / timing.lead_fade)
            out[key] = glyph(key, t), colour
        else:
            alpha = (t - lock) / timing.fade
            if timing.smooth:
                alpha = ease_in_out(alpha)
            # Omit zero-alpha cells, as the original Apple fade does.
            if alpha or timing.lead:
                out[key] = ch, art.mix(timing.flash or pal['bg'], rgb, alpha)
    return out


def ambient_title(cells, word, pal, u, fraction=.42, strength=.55,
                  locks=None, glyph=None):
    """Brief deterministic decode, applied after the scene's light pass."""
    if not word or u >= fraction:
        return
    values = list(locks.values()) if locks is not None else [col for _, col in word]
    lo, hi = min(values), max(values)
    span = max(1e-6 if locks is not None else 1, hi - lo)
    settled = u / fraction
    alphabet = '0123456789ABCDEF'
    step = int(u * 24)
    for key in word:
        position = locks[key] if locks is not None else key[1]
        if (position - lo) / span <= settled or key not in cells:
            continue
        ch, colour = cells[key]
        ch = (glyph(key, u) if glyph else
              alphabet[(key[0] * 7 + key[1] * 11 + step) % len(alphabet)])
        cells[key] = ch, art.mix(colour, pal['accent'], strength)


def light_pass(cells, pal, bounds, u, word=(), band=.12, strength=.85,
               mark_colour=None, squared=False):
    """A shared diagonal light pass; title cells use the brand accent."""
    x0, y0, x1, y1 = bounds
    span, height = max(1, x1-x0), max(1, y1-y0)
    centre = -.25 + 1.5 * ease_in_out(u)
    for key, (ch, colour) in cells.items():
        position = ((key[1]-x0)/span + (1-(key[0]-y0)/height)*.45)/1.45
        glow = 1 - abs(position-centre)/band
        if glow > 0:
            target = pal['accent'] if key in word else (mark_colour or pal['ink'])
            cells[key] = ch, art.mix(colour, target,
                                     strength * (glow * glow if squared else glow))
