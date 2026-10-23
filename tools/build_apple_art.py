"""Regenerate Apple polygons from the vendored Simple Icons SVG (stdlib only).

This small converter deliberately supports only the M/c/z commands in this
source. Unexpected commands fail rather than silently changing the silhouette.
"""
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


ASSETS = Path(__file__).resolve().parents[1] / 'agent_theme/themes/assets'


def build():
    root = ET.parse(ASSETS / 'apple.svg').getroot()
    path = root.find('{http://www.w3.org/2000/svg}path').attrib['d']
    tokens = re.findall(r'[A-Za-z]|[-+]?(?:\d*\.\d+|\d+)', path)
    polygons, polygon = [], []
    i, command = 0, None
    x = y = 0.0
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            i += 1
        if command == 'z':
            polygons.append(polygon)
            x, y = polygon[0]
            polygon = []
            command = None
        elif command == 'M':
            if polygon:
                polygons.append(polygon)
            x, y = map(float, tokens[i:i + 2])
            polygon = [(x, y)]
            i += 2
        elif command == 'c':
            a, b, c, d, e, f = map(float, tokens[i:i + 6])
            for step in range(1, 25):
                t = step / 24
                u = 1 - t
                polygon.append((round(x + 3*u*u*t*a + 3*u*t*t*c + t*t*t*e, 5),
                                round(y + 3*u*u*t*b + 3*u*t*t*d + t*t*t*f, 5)))
            x, y = x + e, y + f
            i += 6
        else:
            raise ValueError('Unsupported SVG command: %r' % command)
    if polygon:
        polygons.append(polygon)
    lettering = json.loads((ASSETS / 'apple-word.json').read_text())
    # Round outward, never guess a box tighter than the actual outline.
    points = [point for polygon in polygons for point in polygon]
    bounds = [math.floor(min(p[0] for p in points) * 1000) / 1000,
              math.floor(min(p[1] for p in points) * 1000) / 1000,
              math.ceil(max(p[0] for p in points) * 1000) / 1000,
              math.ceil(max(p[1] for p in points) * 1000) / 1000]
    header = json.loads((ASSETS / 'apple-header.json').read_text())
    asset = {
        'source': 'Apple silhouette: Simple Icons apple.svg (CC0); Apple trademark. '
                  'Source preserved in apple.svg; ' + lettering['source'],
        'source_url': 'https://github.com/simple-icons/simple-icons/blob/develop/icons/apple.svg',
        'mini_monochrome': True, 'word_fill': 'nonzero',
        'mini_grid': header['mini_grid'], 'mini_grid_quadrant': header['mini_grid_quadrant'],
        'header_cells': header['header_cells'],
        'min_word_rows': 3,
        'mark': polygons, 'word': lettering['word'], 'logo_bbox': bounds,
        'logo_notch_fill_box': [18, 11, 20, 14],
        'word_bbox': lettering['word_bbox'],
        'gradient': {'type': 'bands', 'y0': 5.7, 'height': 18.3,
                     'colours': [[97, 187, 72], [247, 207, 64], [245, 143, 44],
                                 [229, 65, 67], [158, 79, 159], [55, 164, 214]]},
    }
    (ASSETS / 'apple.json').write_text(json.dumps(asset, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    build()
