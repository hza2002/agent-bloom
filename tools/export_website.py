#!/usr/bin/env python3
"""Build website facts and sampled production frames. No website runtime dependency."""
import argparse
import gzip
import hashlib
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Preview geometry and language are explicit, independent of the build machine.
os.environ['AGENT_THEME_GLYPHS'] = 'octant'
os.environ['AGENT_THEME_CELL_RATIO'] = '2.12'
os.environ['AGENT_THEME_LANG'] = 'zh-Hans'

from agent_theme import __version__, art
from agent_theme.animation import (FRAME_HZ, AMBIENT_PERIOD, AMBIENT_SWEEP,
                                   AMBIENT_INTERVAL, make_animated_overlay)
from agent_theme.cli import HELP
from agent_theme.overlay import REVEAL_SECONDS
from agent_theme.themes import DEFAULT_THEME, THEME_NAMES, get_theme

COLS, ROWS = 81, 40
CELL_WIDTH, CELL_HEIGHT = 8, 8 * art.CELL_RATIO


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def flatten(rows):
    cells = {}
    for row, entries in rows.items():
        for col, run in entries:
            for char, rgb, bold in run:
                if char != ' ' and rgb is not None:
                    cells[row * COLS + col] = (char, tuple(rgb), bool(bold))
                col += art.text_width(char)
    return cells


def scene_for(theme, app, palette):
    brand = theme.brands[app]
    # Leave the same kind of blank margin that application chrome reserves.
    lock = art.choose(brand, COLS, ROWS - 6)
    if lock is None:
        raise ValueError('Preview layout unavailable: ' + theme.key)
    top = max(0, (ROWS - lock.height) // 2)
    scene = theme.create_scene(COLS, ROWS, palette, brand, lock=lock, top=top)
    if not scene.ok:
        raise ValueError('Preview scene unavailable: ' + theme.key)
    if hasattr(scene, 'rng'):
        scene.rng.seed(7)
    return scene, lock, top


def sample_frames(theme, app, palette):
    scene, lock, top = scene_for(theme, app, palette)
    duration = scene.duration + REVEAL_SECONDS
    count = math.ceil(duration * FRAME_HZ)
    for index in range(count + 1):
        stamp = min(duration, index / FRAME_HZ)
        source = scene.frame(min(stamp, scene.duration))
        reveal = min(1, max(0, (stamp - scene.duration) / REVEAL_SECONDS))
        text = art.small_text_rows(lock, top, reveal, palette)
        cells = {row * COLS + col: (char, tuple(rgb), False)
                 for (row, col), (char, rgb) in source.items()
                 if char != ' ' and rgb is not None}
        cells.update(flatten(text))
        yield round(stamp * 1000), cells


def sample_ambient(theme, app, palette):
    scene, lock, top = scene_for(theme, app, palette)
    # Reuse the production text sheen without constructing a PTY overlay.
    overlay = make_animated_overlay(object, theme.create_scene)
    state = SimpleNamespace(anchor=(lock, top, None), pal=palette)
    count = math.ceil(AMBIENT_SWEEP / AMBIENT_INTERVAL)
    for index in range(count + 1):
        u = min(1, index * AMBIENT_INTERVAL / AMBIENT_SWEEP)
        source = scene.ambient_frame(u) if u < 1 else scene.frame(scene.duration)
        cells = {row * COLS + col: (char, tuple(rgb), False)
                 for (row, col), (char, rgb) in source.items()
                 if char != ' ' and rgb is not None}
        cells.update(flatten(art.small_text_rows(
            lock, top, 1, palette, tint=overlay._text_tint(state, u))))
        yield round(u * AMBIENT_SWEEP * 1000), cells


def encode_frames(frames):
    """Dictionary-coded cells and changes; token -1 erases an old cell."""
    tokens, indices, encoded, previous = [], {}, [], {}
    for stamp, cells in frames:
        changes = []
        for position in sorted(previous.keys() | cells.keys()):
            value = cells.get(position)
            if value == previous.get(position):
                continue
            token = -1
            if value is not None:
                if value not in indices:
                    indices[value] = len(tokens)
                    tokens.append(value)
                token = indices[value]
            changes.extend((position, token))
        encoded.append([stamp, changes])
        previous = cells
    return {'tokens': tokens, 'frames': encoded}


def poster(cells, background):
    """SVG is generated terminal output, using the exact production octant map."""
    bits_by_char = {char: bits for bits, char in enumerate(art.OCTANT_TABLE)}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges" width="648" height="{ROWS * CELL_HEIGHT}" viewBox="0 0 648 {ROWS * CELL_HEIGHT}">',
             f'<path fill="rgb{tuple(background)}" d="M0 0H648V{ROWS * CELL_HEIGHT}H0Z"/>']
    paths = {}
    for position, (char, rgb, bold) in sorted(cells.items()):
        x, y = position % COLS * CELL_WIDTH, position // COLS * CELL_HEIGHT
        if len(rgb) == 2:
            rgb, cell_background = rgb
            colour_bg = '#%02x%02x%02x' % cell_background
            parts.append(f'<rect x="{x:g}" y="{y:g}" width="8" height="{CELL_HEIGHT:g}" fill="{colour_bg}"/>')
        colour = '#%02x%02x%02x' % rgb
        if char in bits_by_char:
            path = paths.setdefault(colour, [])
            for bit in range(8):
                if bits_by_char[char] & (1 << bit):
                    px, py = x + (bit % 2) * 4, y + (bit // 2) * CELL_HEIGHT / 4
                    path.append(f'M{px:g} {py:g}h4v{CELL_HEIGHT / 4:g}h-4Z')
        else:
            parts.append(f'<text x="{x:g}" y="{y + CELL_HEIGHT * .78:g}" fill="{colour}" font-family="monospace" font-size="13" font-weight="{700 if bold else 400}">{html.escape(char)}</text>')
    parts.extend(f'<path fill="{colour}" d="{"".join(path)}"/>' for colour, path in paths.items())
    parts.append('</svg>')
    return ''.join(parts)


def header_poster(theme, mode):
    """Render the same baked or procedural cells used by the Claude header."""
    previous = os.environ.get('AGENT_THEME_PALETTE')
    os.environ['AGENT_THEME_PALETTE'] = mode
    try:
        baked = ((theme.art.get('header_cells_by_palette') or {}).get(mode) or
                 theme.art.get('header_cells') or {}).get('octant')
        if baked:
            rows = baked
        else:
            bits_by_char = {char: bits for bits, char in enumerate(art.OCTANT_TABLE)}
            rows = [[(bits_by_char[char], rgb, None) for char, rgb in row]
                    for row in art.mini_logo(theme, shrink=theme.mini_shrink)]
    finally:
        if previous is None:
            os.environ.pop('AGENT_THEME_PALETTE', None)
        else:
            os.environ['AGENT_THEME_PALETTE'] = previous
    height = CELL_HEIGHT * 3
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges" viewBox="0 0 72 {height}">']
    for row, (cells, width) in enumerate(zip(rows, (8, 9, 9))):
        for col, (bits, foreground, background) in enumerate(cells[:width]):
            x, y = col * CELL_WIDTH, row * CELL_HEIGHT
            if background is not None:
                parts.append(f'<rect x="{x}" y="{y}" width="8" height="{CELL_HEIGHT}" fill="rgb{tuple(background)}"/>')
            if foreground is None:
                continue
            for bit in range(8):
                if bits & (1 << bit):
                    px, py = x + bit % 2 * 4, y + bit // 2 * CELL_HEIGHT / 4
                    parts.append(f'<rect x="{px}" y="{py}" width="4" height="{CELL_HEIGHT / 4}" fill="rgb{tuple(foreground)}"/>')
    return ''.join(parts) + '</svg>'


def export(output):
    # Only this generated directory is owned by the exporter.
    output.mkdir(parents=True, exist_ok=True)
    media = output / 'media'
    if media.exists():
        shutil.rmtree(media)
    media.mkdir()
    themes, metrics = [], []
    for name in THEME_NAMES:
        theme = get_theme(name)
        item = {'id': name, 'name': name, 'defaultAnimation': theme.default_animation,
                'apps': list(theme.brands),
                'animations': [{'id': a.key, 'name': a.label} for a in theme.animations],
                'previews': {}}
        for app in item['apps']:
            for animation in theme.animations:
                _, selected = theme.select_animation(animation.key)
                for mode in ('light', 'dark'):
                    palette = getattr(selected, mode)
                    scene, lock, top = scene_for(selected, app, palette)
                    static = flatten(art.home_rows(lock, top, 1, palette))
                    stem = f'{name}-{animation.key}-{app}-{mode}'
                    svg = poster(static, palette['bg']).encode()
                    poster_name = hashlib.sha256(svg).hexdigest()[:16] + '.svg'
                    (media / poster_name).write_bytes(svg)
                    badge = header_poster(selected, mode).encode()
                    badge_name = hashlib.sha256(badge).hexdigest()[:16] + '.svg'
                    (media / badge_name).write_bytes(badge)
                    data = encode_frames(sample_frames(selected, app, palette))
                    # Check playback state, including removals, against production static art.
                    decoded = {}
                    for _, changes in data['frames']:
                        for offset in range(0, len(changes), 2):
                            pos, token = changes[offset:offset + 2]
                            if token == -1:
                                decoded.pop(pos, None)
                            else:
                                decoded[pos] = data['tokens'][token]
                    if decoded != static:
                        raise ValueError(f'{stem} does not settle to static art')
                    payload = dumps(data)
                    filename = hashlib.sha256(payload).hexdigest()[:16] + '.json'
                    (media / filename).write_bytes(payload)
                    ambient = encode_frames(sample_ambient(selected, app, palette))
                    ambient_payload = dumps(ambient)
                    ambient_name = hashlib.sha256(ambient_payload).hexdigest()[:16] + '.json'
                    (media / ambient_name).write_bytes(ambient_payload)
                    metrics.append({'preview': stem, 'phase': 'ambient', 'bytes': len(ambient_payload),
                                    'gzipBytes': len(gzip.compress(ambient_payload)), 'frames': len(ambient['frames'])})
                    item['previews'][f'{animation.key}/{app}/{mode}'] = {
                        'poster': poster_name, 'background': palette['bg'], 'intro': filename, 'ambient': ambient_name,
                        'header': selected.brands[app].header, 'badge': badge_name,
                        'icon': selected.header_icon, 'iconColour': selected.header_colour,
                        'foreground': palette['ink'], 'muted': palette['muted']}
                    metrics.append({'preview': stem, 'phase': 'intro', 'bytes': len(payload),
                                    'gzipBytes': len(gzip.compress(payload)), 'frames': len(data['frames'])})
        themes.append(item)
    revision = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    catalogue = {'version': __version__, 'revision': revision, 'defaultTheme': DEFAULT_THEME,
                 'ambientPeriod': round(AMBIENT_PERIOD * 1000), 'ambientSweep': round(AMBIENT_SWEEP * 1000),
                 'cols': COLS, 'rows': ROWS, 'cellRatio': art.CELL_RATIO,
                 'glyphs': art.OCTANT_TABLE,
                 'themes': themes, 'help': HELP % __version__}
    (output / 'catalogue.json').write_bytes(dumps(catalogue))
    (output / 'metrics.json').write_bytes(dumps(metrics))
    print(f'Exported {len(themes)} themes; {len(list(media.glob("*.json")))} unique clips; '
          f'largest clip {max(x["bytes"] for x in metrics):,} bytes '
          f'({max(x["gzipBytes"] for x in metrics):,} bytes gzip estimate).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'website/public/generated')
    export(parser.parse_args().output)
