#!/usr/bin/env python3
"""Pack a build-time theme-lab export into offline, standard-library assets.

In the local theme-lab page call exportTheme(id) from export.js, save its JSON,
then run (FontTools and a font covering the title are build-time dependencies):
uv run --with fonttools python tools/build_theme_art.py export.json output.json InterVariable.ttf
The maintained JS drawings are the source; there is no browser at runtime.
"""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import sys
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from agent_theme.themes import RASTER_THEME_NAMES
from agent_theme.themes.asset_spec import catalog_entry, inspect_asset, validate_metadata


def pack(value):
    if isinstance(value, dict):
        return {key: pack(item) for key, item in value.items()}
    if isinstance(value, list):
        return [pack(item) for item in value]
    if isinstance(value, str):
        return base64.b64encode(zlib.compress(base64.b64decode(value), 9)).decode('ascii')
    raise ValueError('invalid raster payload')


def title_outlines(font_path, text, target_width=192, target_height=36):
    from fontTools.ttLib import TTFont
    from tools.build_apple_word import OutlinePen
    font=TTFont(font_path)
    axes={a.axisTag for a in font['fvar'].axes} if 'fvar' in font else set()
    glyphs=font.getGlyphSet(location={k:v for k,v in {'wght':500,'opsz':32}.items() if k in axes})
    cmap=font.getBestCmap()
    if any(ord(ch) not in cmap for ch in text):
        return None
    contours=[];left=0
    for ch in text:
        glyph=glyphs[cmap[ord(ch)]];pen=OutlinePen(glyphs);glyph.draw(pen)
        contours.extend([[(x+left,-y) for x,y in line] for line in pen.contours])
        left+=glyph.width+font['head'].unitsPerEm*.015
    xs=[x for line in contours for x,_ in line];ys=[y for line in contours for _,y in line]
    width,height=max(xs)-min(xs),max(ys)-min(ys)
    scale=min(174/width,(24 if text.isascii() else 30)/height)
    ox,oy=(192-width*scale)/2,(36-height*scale)/2
    return [[(round((ox+(x-min(xs))*scale)*target_width/192,5),
              round((oy+(y-min(ys))*scale)*target_height/36,5))
             for x,y in line] for line in contours]


def title_bounds(outlines):
    """Frame the actual title ink so terminal rows are not spent on canvas padding."""
    points = [point for contour in outlines for point in contour]
    return [math.floor(min(p[0] for p in points)), math.floor(min(p[1] for p in points)),
            math.ceil(max(p[0] for p in points)), math.ceil(max(p[1] for p in points))]


def build(source, destination, font_path=None):
    data = json.loads(Path(source).read_text())
    if data['format'] != 1:
        raise ValueError('unsupported theme export')
    validate_metadata(data)
    if font_path is None:
        raise ValueError('title regeneration requires a font covering every title character')
    for field in ('frames', 'headers', 'word'):
        data[field] = pack(data[field])
    outlines=title_outlines(font_path,data['wordmark'],data['word_width'],data['word_height'])
    if not outlines:
        raise ValueError('selected font does not cover every title character')
    from fontTools.ttLib import TTFont
    with TTFont(font_path) as font:
        family = font['name'].getDebugName(1) or 'Unnamed font'
        version = font['name'].getDebugName(5) or ''
        axes = {axis.axisTag for axis in font['fvar'].axes} if 'fvar' in font else set()
    settings = ', '.join('%s %s' % (key, value) for key, value in
                         (('wght', 500), ('opsz', 32)) if key in axes)
    data['word_polys']=outlines
    data['title_source']='; '.join(filter(None, (family, version, settings, 'terminal grid fitted')))
    data['title_font_sha256']=hashlib.sha256(Path(font_path).read_bytes()).hexdigest()
    layout = dict(view_box=[0, 0, data['width'], data['height']],
                  logo_scale=1.2, min_word_rows=3)
    layout.update(data.get('layout', {}))
    data['layout'] = layout
    data.update(raster=True, logo_bbox=[0, 0, data['width'], data['height']],
                word_bbox=data.get('word_bbox') or title_bounds(outlines),
                min_word_rows=3)
    data['visual_bbox'], data['motion_bbox'] = inspect_asset(data)
    Path(destination).write_text(json.dumps(data, separators=(',', ':'), ensure_ascii=False)+'\n')


def check_assets(directory, write_catalog=False):
    expected = {}
    for name in RASTER_THEME_NAMES:
        path = directory / (name + '.json')
        asset = json.loads(path.read_text())
        if asset['id'] != name:
            raise ValueError(str(path) + ': theme id differs from filename')
        inspect_asset(asset)
        expected[name] = catalog_entry(asset)
    path = directory / 'catalog.json'
    if write_catalog:
        path.write_text(json.dumps(expected, indent=2, ensure_ascii=False)+'\n')
    elif json.loads(path.read_text()) != expected:
        raise ValueError('catalog differs from assets; run --catalog after building themes')
    return len(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?', type=Path)
    parser.add_argument('destination', nargs='?', type=Path)
    parser.add_argument('font', nargs='?', type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true', help='validate all baked assets and catalog')
    action.add_argument('--catalog', action='store_true', help='validate assets and regenerate the catalog')
    args = parser.parse_args()
    if args.check or args.catalog:
        if args.source or args.destination or args.font:
            parser.error('catalog/check modes take no positional arguments')
        count = check_assets(Path(__file__).resolve().parents[1]/'agent_theme/themes/assets', args.catalog)
        print('Validated %d raster themes and catalog' % count)
    else:
        if not args.source or not args.font:
            parser.error('building requires source, destination and font paths')
        build(args.source, args.destination, args.font)


if __name__ == '__main__':
    main()
