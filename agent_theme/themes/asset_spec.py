"""The small, internal contract for baked theme assets (no plugin discovery)."""
import base64
import math
import re
import struct
import zlib

CATALOG_FIELDS = ('name', 'wordmark', 'footer', 'accent', 'variants', 'header_icon')


def _size(value, name):
    if type(value) is not int or value <= 0:
        raise ValueError(name + ' must be a positive integer')


def _box(box, width, height, name):
    if (not isinstance(box, (list, tuple)) or len(box) != 4
            or any(type(v) is not int for v in box)
            or not 0 <= box[0] < box[2] <= width
            or not 0 <= box[1] < box[3] <= height):
        raise ValueError(name + ' must be a nonempty integer box inside the canvas')


def contains(outer, inner):
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[2] >= inner[2] and outer[3] >= inner[3])


def union(boxes):
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def validate_metadata(asset):
    """Cheap checks performed once when an internal raster theme is loaded."""
    if asset.get('format') != 1:
        raise ValueError('unsupported raster asset format')
    if not re.fullmatch(r'[a-z][a-z0-9-]*', asset.get('id', '')):
        raise ValueError('invalid theme id')
    for key in ('width', 'height', 'word_width', 'word_height', 'fps'):
        _size(asset.get(key), key)
    for key in ('name', 'wordmark', 'header_icon'):
        if not isinstance(asset.get(key), str) or not asset[key]:
            raise ValueError(key + ' must be nonempty text')
    if len(asset.get('footer', [])) != 3:
        raise ValueError('exactly three footer lines required')
    text = [asset['name'], asset['wordmark'], asset['header_icon'], *asset['footer']]
    if any(not isinstance(s, str) or not s or any(ord(c) < 32 or ord(c) == 127 for c in s) for s in text):
        raise ValueError('theme text must be nonempty and contain no terminal controls')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', asset.get('accent', '')):
        raise ValueError('accent must be a six-digit hex colour')
    keys = [v['id'] for v in asset['variants']]
    if (not keys or len(keys) != len(set(keys))
            or any(not re.fullmatch(r'[a-z][a-z0-9-]*', k) or k == 'random' for k in keys)):
        raise ValueError('invalid or duplicate animation ids')
    if not asset.get('sources'):
        raise ValueError('asset provenance is required')
    palette = asset.get('palette', [])
    if (not palette or palette[0] is not None or len(palette) > 65536
            or any(not isinstance(c, (list, tuple)) or len(c) != 3
                   or any(type(v) is not int or not 0 <= v <= 255 for v in c)
                   for c in palette[1:])):
        raise ValueError('invalid RGB palette')
    _box(asset.get('word_bbox', [0, 0, asset['word_width'], asset['word_height']]),
         asset['word_width'], asset['word_height'], 'word_bbox')
    layout = asset.get('layout', {})
    _box(layout.get('view_box', [0, 0, asset['width'], asset['height']]),
         asset['width'], asset['height'], 'view_box')
    scale = layout.get('logo_scale', 1.04)
    if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('logo_scale must be finite and positive')
    _size(layout.get('min_word_rows', asset.get('min_word_rows', 3)), 'min_word_rows')
    duration = asset.get('intro_seconds', 3.0)
    if not isinstance(duration, (int, float)) or not math.isfinite(duration) or duration <= 0:
        raise ValueError('intro_seconds must be finite and positive')


def frame_bounds(encoded, width, height, colours):
    """Validate compressed runs and find occupied bounds without expanding pixels."""
    raw = zlib.decompress(base64.b64decode(encoded, validate=True))
    boxes, offset = [], 0
    for count, colour in struct.iter_unpack('<HH', raw):
        end = offset + count
        if not count or end > width * height or colour >= colours:
            raise ValueError('invalid raster run or palette index')
        if colour:
            y0, x0 = divmod(offset, width)
            y1, x1 = divmod(end - 1, width)
            boxes.append([x0 if y0 == y1 else 0, y0,
                          x1 + 1 if y0 == y1 else width, y1 + 1])
        offset = end
    if offset != width * height:
        raise ValueError('invalid raster dimensions')
    return union(boxes)


def inspect_asset(asset):
    """Build/CI validation: every frame, endpoint, header and declared boundary."""
    validate_metadata(asset)
    width, height, colours = asset['width'], asset['height'], len(asset['palette'])
    keys = {v['id'] for v in asset['variants']}
    bounds, still_bounds, cache = [], [], {}
    def inspect(frame, w=width, h=height):
        key = (frame, w, h)
        if key not in cache:
            cache[key] = frame_bounds(frame, w, h, colours)
        return cache[key]
    for mode in ('dark', 'light'):
        frames = asset['frames'][mode]
        still = frames['still']
        still_bounds.append(inspect(still))
        if still_bounds[-1] is None:
            raise ValueError('empty static artwork')
        if set(frames['intro']) != keys:
            raise ValueError('animation metadata differs from frame sequences')
        expected_frames = round(asset.get('intro_seconds', 3.0) * asset['fps']) + 1
        if any(len(sequence) != expected_frames for sequence in frames['intro'].values()):
            raise ValueError('intro frame count differs from fps and duration')
        for sequence in [frames['idle'], *frames['intro'].values()]:
            if len(sequence) < 2 or sequence[-1] != still:
                raise ValueError('animation must end at the exact static frame')
            bounds.extend(inspect(frame) for frame in sequence)
        if frames['idle'][0] != still:
            raise ValueError('idle must start at the exact static frame')
        for glyph_mode in ('octant', 'quadrant'):
            if inspect(asset['headers'][mode][glyph_mode], 18, 12) is None:
                raise ValueError('empty header badge')
    if inspect(asset['word'], asset['word_width'], asset['word_height']) is None:
        raise ValueError('empty title')
    if asset.get('word_polys'):
        points = [point for contour in asset['word_polys'] for point in contour]
        if not points or any(len(point) != 2 or any(not math.isfinite(v) for v in point) for point in points):
            raise ValueError('invalid title outlines')
        title_bounds = [min(p[0] for p in points), min(p[1] for p in points),
                        max(p[0] for p in points), max(p[1] for p in points)]
    else:
        title_bounds = inspect(asset['word'], asset['word_width'], asset['word_height'])
    title_box = asset.get('word_bbox', [0, 0, asset['word_width'], asset['word_height']])
    if not contains(title_box, title_bounds):
        raise ValueError('word_bbox clips the title')
    visual, motion = union(still_bounds), union(bounds + still_bounds)
    view = asset.get('layout', {}).get('view_box', [0, 0, width, height])
    if not contains(view, motion):
        raise ValueError('view_box clips the animation motion bounds')
    for key, actual in (('visual_bbox', visual), ('motion_bbox', motion)):
        if key in asset and asset[key] != actual:
            raise ValueError(key + ' does not match encoded artwork')
    return visual, motion


def catalog_entry(asset):
    return {key: asset[key] for key in CATALOG_FIELDS}
