"""Explicit project-owned raster themes; metadata loading never imports a renderer."""
import json
from functools import partial
from importlib.resources import files

from . import Animation, Theme

CATALOG = json.loads(files('agent_theme.themes').joinpath('assets/catalog.json').read_text(encoding='utf-8'))


def load_art(name):
    from .raster import cells, decode
    data = json.loads(files('agent_theme.themes').joinpath('assets/' + name + '.json').read_text(encoding='utf-8'))
    from .asset_spec import validate_metadata, frame_bounds, union
    validate_metadata(data)
    # Persistent content controls footer spacing; intro particles keep their full stage.
    data['rest_bbox'] = union(frame_bounds(frame, data['width'], data['height'],
                                           len(data['palette']))
                              for frames in data['frames'].values()
                              for frame in [frames['still'], *frames['idle']])
    headers = {}
    for palette, modes in data['headers'].items():
        headers[palette] = {}
        for mode, encoded in modes.items():
            rows = cells(decode(encoded, 18, 12), 18, 12, 18, 12, data['palette'], mode)
            # All mascot rows start at the same column. Only the right edge is shorter.
            headers[palette][mode] = [rows[0][:8]] + rows[1:]
    data['header_cells_by_palette'] = headers
    return data


def create_scene(*args, variant, **kwargs):
    from .raster import RasterScene
    return RasterScene(*args, variant=variant, **kwargs)


def make_theme(name):
    meta = CATALOG[name]
    accent = tuple(bytes.fromhex(meta['accent'].lstrip('#')))
    dark = dict(ink=(238, 238, 233), soft=(190, 196, 199), muted=(128, 138, 140),
                accent=accent, bg=(14, 15, 18))
    light = dict(ink=(30, 32, 33), soft=(70, 77, 80), muted=(98, 108, 112),
                 accent=tuple(round(v * .65) for v in accent), bg=(250, 250, 250))
    animations = tuple(Animation(v['id'], v['label'], partial(create_scene, variant=v['id']))
                       for v in meta['variants'])
    copy = {app: dict(header=meta['name'], title=meta['name']+' · '+app.capitalize(),
                      slogan=meta['footer'][0], tagline=meta['footer'][1], platform=meta['footer'][2])
            for app in ('claude', 'codex')}
    return Theme(key=name, label=meta['name'], load_art=partial(load_art, name),
                 create_scene=animations[0].create_scene, dark=dark, light=light,
                 copy=copy, header_icon=meta['header_icon'], header_colour=accent,
                 mini_shrink=1.0, animations=animations,
                 default_animation=animations[0].key)
