"""Theme extension contracts: framing, independent resolution and shared copy."""
import ast
import base64
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
import zlib

from agent_theme import art
from agent_theme.themes import THEME_NAMES, get_theme
from agent_theme.themes.asset_spec import inspect_asset, validate_metadata
from agent_theme.themes.raster import RasterMark
from tools.build_theme_art import check_assets


def frame(width, height, box):
    pixels=[int(box[0] <= x < box[2] and box[1] <= y < box[3])
            for y in range(height) for x in range(width)]
    runs=[];last=pixels[0];count=0
    for value in pixels:
        if value != last:
            runs.extend((count,last));count=0;last=value
        count+=1
    runs.extend((count,last))
    return base64.b64encode(zlib.compress(struct.pack('<'+'H'*len(runs),*runs))).decode()


def sample_asset():
    still=frame(24,16,[8,4,16,12]);moving=frame(24,16,[10,4,18,12])
    return dict(format=1,id='example',name='Example',wordmark='X',header_icon='X',
                footer=['One','Two','Three'],accent='#ff0000',sources=['test drawing'],
                variants=[dict(id='enter',label='Enter')],palette=[None,[255,0,0]],
                width=24,height=16,word_width=8,word_height=8,fps=1,intro_seconds=1,
                raster=True,logo_bbox=[0,0,24,16],word_bbox=[0,0,8,8],min_word_rows=1,
                layout=dict(view_box=[6,2,20,14],logo_scale=1.04,min_word_rows=1),
                word=frame(8,8,[2,1,6,7]),
                headers={p:{m:frame(18,12,[4,2,12,10]) for m in ('octant','quadrant')}
                         for p in ('dark','light')},
                frames={p:dict(still=still,idle=[still,moving,still],
                               intro={'enter':[moving,still]}) for p in ('dark','light')})


class ThemeArchitectureTests(unittest.TestCase):
    def tearDown(self):art.reset_glyphs()

    def test_approved_huawei_and_apple_motion_is_unchanged(self):
        fixture=Path(__file__).parent/'fixtures/approved_theme_motion.json'
        with patch.dict(os.environ,AGENT_THEME_GLYPHS='quadrant'):
            art.reset_glyphs()
            for key,expected in json.loads(fixture.read_text()).items():
                name,variant,app,cols,rows,light=ast.literal_eval(key)
                _,theme=get_theme(name).select_animation(variant)
                pal=theme.light if light else theme.dark
                brand=theme.brands[app];lock=art.choose(brand,cols,rows-2)
                scene=theme.create_scene(cols,rows,pal,brand,lock=lock,top=1)
                if hasattr(scene,'rng'):scene.rng.seed(12345)
                frames=[scene.frame(t) for t in (0,.5,1.2,1.7,2.3,3.3)]
                frames += [scene.ambient_frame(u) for u in (0,.15,.5,1)]
                payload=json.dumps([sorted(f.items()) for f in frames],sort_keys=True)
                self.assertEqual(hashlib.sha256(payload.encode()).hexdigest(),expected,key)

    def test_titles_reveal_without_scrambling_and_idle_returns_to_the_same_art(self):
        for name in THEME_NAMES[2:]:
            theme=get_theme(name)
            for cols,rows in ((80,30),(120,50),(160,65)):
                for pal in (theme.dark,theme.light):
                    brand=theme.brands['claude'];lock=art.choose(brand,cols,rows-2)
                    scene=theme.create_scene(cols,rows,pal,brand,lock=lock,top=1)
                    word=scene._word()
                    if not lock.show_word:
                        self.assertEqual(word, {})
                        continue
                    previous=set()
                    for t in (1.3,1.8,2.2,2.9):
                        revealed=scene._word(t=t)
                        self.assertTrue(previous <= set(revealed) <= set(word))
                        for key,(ch,rgb) in revealed.items():
                            self.assertEqual(ch,word[key][0], 'title entrance should fade its own glyph')
                            self.assertTrue(all(min(bg,ink) <= v <= max(bg,ink)
                                for bg,ink,v in zip(pal['bg'],pal['ink'],rgb)))
                        previous=set(revealed)
                    self.assertEqual(revealed,word)
                    self.assertEqual(scene._word(idle=0),word)
                    self.assertEqual(scene._word(idle=1),word)
                    self.assertTrue(any(ch != word[key][0]
                        for key,(ch,_) in scene._word(idle=.15).items()))
                    self.assertTrue(all(ch == word[key][0]
                        for key,(ch,_) in scene._word(idle=.5).items()))

    def test_nonstandard_canvas_and_safe_framing_render_without_theme_branches(self):
        asset=sample_asset()
        self.assertEqual(inspect_asset(asset),([8,4,16,12],[8,4,18,12]))
        cropped=RasterMark(28,3,asset)
        full=deepcopy(asset);full['layout']['view_box']=[0,0,24,16]
        uncropped=RasterMark(28,3,full)
        self.assertEqual(cropped.logo_rows,math.ceil(12*(56/14)/art.SUB_ASPECT/4))
        self.assertEqual(cropped.word_cols,math.ceil(12*art.SUB_ASPECT/2))
        self.assertGreater(sum(bin(b).count('1') for row in cropped.logo_bits() for b in row),
                           sum(bin(b).count('1') for row in uncropped.logo_bits() for b in row))
        self.assertEqual(len(cropped.logo_cells(get_theme('huawei').dark)),cropped.logo_rows)
        tight=deepcopy(asset);tight['word_bbox']=[2,1,6,7]
        inspect_asset(tight)
        title=RasterMark(28,3,tight)
        self.assertLess(title.word_cols,cropped.word_cols)
        self.assertGreater(sum(bin(b).count('1') for row in title.word_bits() for b in row),
                           sum(bin(b).count('1') for row in cropped.word_bits() for b in row))

    def test_invalid_framing_corrupt_frames_and_bad_endpoints_are_rejected(self):
        for change,error in (
            (lambda a:a['layout'].update(view_box=[8,4,16,12]),'clips'),
            (lambda a:a.update(motion_bbox=[0,0,24,16]),'motion_bbox'),
            (lambda a:a.update(word_bbox=[3,2,5,6]),'clips the title'),
            (lambda a:a['frames']['dark']['intro']['enter'].reverse(),'static'),
            (lambda a:a['frames']['dark'].update(still=frame(12,8,[2,2,4,4])),'dimensions'),
        ):
            a=sample_asset();change(a)
            with self.assertRaisesRegex(ValueError,error):inspect_asset(a)
        a=sample_asset();a['palette']=[None]
        with self.assertRaisesRegex(ValueError,'palette'):inspect_asset(a)
        for value in (0,-1,float('nan')):
            a=sample_asset();a['layout']['logo_scale']=value
            with self.assertRaisesRegex(ValueError,'logo_scale'):validate_metadata(a)

    def test_layout_configuration_changes_scale_without_renderer_changes(self):
        theme=get_theme('microsoft');brand=theme.brands['claude']
        with patch.dict(theme.art,layout=dict(logo_scale=1.3,min_word_rows=3)):
            lock=art.Lockup(brand,4,0,160)
            expected=int(lock.mark.word_cols*1.3+1)//2*2
            self.assertEqual(lock.mark.logo_cols,expected)
        small=art.choose(brand,80,25);large=art.choose(brand,160,65)
        self.assertGreater(large.word_rows,small.word_rows)
        self.assertGreater(large.mark.logo_cols,small.mark.logo_cols)

    def test_title_visibility_is_shared_layout_configuration(self):
        theme = get_theme('microsoft')
        brand = theme.brands['claude']
        for cols, rows in ((60, 20), (80, 30), (120, 50), (160, 65)):
            baseline = art.choose(brand, cols, rows)
            self.assertTrue(baseline.show_word)
            with patch.dict(theme.art, layout=dict(theme.art['layout'], show_title=False)):
                lock = art.choose(brand, cols, rows)
                self.assertFalse(lock.show_word)
                self.assertEqual(lock.word_rows, 0)
                self.assertTrue(lock.show_mark and lock.show_small)
                self.assertGreaterEqual(lock.mark.logo_cols, baseline.mark.logo_cols)
                self.assertLessEqual(lock.height, rows)
                self.assertLessEqual(lock.width, cols - 2 * art.GUTTER)
                self.assertEqual(lock.slogan_top, lock.mark.content_rows + lock.gap_word)
                scene = theme.create_scene(cols, rows, theme.dark, brand, lock=lock, top=0)
                self.assertEqual(scene._word(), {})
                for stamp in (0, 1.5, 3):
                    self.assertIsInstance(scene.frame(stamp), dict)
                self.assertIsInstance(scene.ambient_frame(.5), dict)

    def test_wordmark_heroes_disable_their_duplicate_titles(self):
        for name in ('google', 'intel', 'amd', 'nintendo'):
            theme = get_theme(name)
            lock = art.choose(theme.brands['claude'], 100, 40)
            self.assertFalse(lock.show_word, name)
            self.assertTrue(lock.show_mark and lock.show_small, name)
        for value in (0, 1, 'false', None):
            asset = sample_asset()
            asset['layout']['show_title'] = value
            with self.assertRaisesRegex(ValueError, 'show_title'):
                validate_metadata(asset)

    def test_hidden_title_footer_follows_persistent_art_not_intro_canvas(self):
        for name in ('google', 'intel', 'amd', 'nintendo'):
            theme = get_theme(name)
            for cols, rows in ((80, 30), (120, 50)):
                lock = art.choose(theme.brands['claude'], cols, rows)
                mark = lock.mark
                self.assertLess(mark.content_rows, mark.logo_rows, name)
                self.assertEqual(lock.slogan_top, mark.content_rows + lock.gap_word)
                self.assertGreaterEqual(lock.height, mark.logo_rows)
                scene = theme.create_scene(cols, rows, theme.dark, theme.brands['claude'],
                                           lock=lock, top=0)
                for phase in ('still', 'idle'):
                    for progress in (0, .25, .5, .75, 1):
                        cells = scene._hero(phase, progress)
                        self.assertTrue(cells)
                        self.assertLess(max(row for row, col in cells), lock.slogan_top)

    def test_checked_catalog_is_generated_from_validated_assets(self):
        directory=Path(__file__).parents[1]/'agent_theme/themes/assets'
        self.assertEqual(check_assets(directory),10)



class ThemePolishTests(unittest.TestCase):
    @staticmethod
    def assert_badge_colours(test, asset):
        from agent_theme.themes.raster import cells, decode
        # Each pair of symbols occupies different 2x4 cells, in both glyph modes.
        for palette in ('dark', 'light'):
            for mode in ('octant', 'quadrant'):
                pixels = decode(asset['headers'][palette][mode], 18, 12)
                rows = cells(pixels, 18, 12, 18, 12, asset['palette'], mode)
                expected = ((66,198,180), (240,116,128), (112,156,244), (220,138,192))
                for index, colour in enumerate(expected):
                    selected_rows = rows[:1] if index < 2 else rows[1:]
                    left = 1 if index % 2 == 0 else 5
                    ink = {fg for line in selected_rows
                           for bits, fg, bg in line[left:left+3] if bits}
                    test.assertEqual(ink, {colour}, (palette, mode, index))

    def test_playstation_button_colours_stay_in_their_own_symbols(self):
        asset = get_theme('playstation').art
        self.assert_badge_colours(self, asset)

    def test_playstation_symbols_share_a_balanced_visual_size(self):
        from agent_theme.themes.raster import decode
        asset = get_theme('playstation').art
        colours = ((66,198,180), (240,116,128), (112,156,244), (220,138,192))
        for palette in ('dark', 'light'):
            pixels = decode(asset['headers'][palette]['octant'], 18, 12)
            for index, colour in enumerate(colours):
                points = [(x, y) for y in range(12) for x in range(18)
                          if pixels[y*18+x] and tuple(asset['palette'][pixels[y*18+x]]) == colour]
                self.assertTrue(points)
                width = max(x for x,y in points)-min(x for x,y in points)+1
                height = max(y for x,y in points)-min(y for x,y in points)+1
                self.assertEqual((width,height), (5,4) if index == 0 else (4,4))

    def test_playstation_symbols_form_a_compact_group(self):
        from agent_theme.themes.raster import decode
        asset = get_theme('playstation').art
        pixels = decode(asset['headers']['dark']['octant'], 18, 12)
        groups = []
        for colour in ((66,198,180), (240,116,128), (112,156,244), (220,138,192)):
            points = [(x,y) for y in range(12) for x in range(18)
                      if pixels[y*18+x] and tuple(asset['palette'][pixels[y*18+x]]) == colour]
            groups.append((min(x for x,y in points), min(y for x,y in points),
                           max(x for x,y in points), max(y for x,y in points)))
        self.assertEqual(groups[1][0] - groups[0][2] - 1, 2)
        self.assertEqual(groups[3][0] - groups[2][2] - 1, 2)
        self.assertEqual(groups[2][1] - groups[0][3] - 1, 2)
        self.assertEqual(groups[3][1] - groups[1][3] - 1, 2)

    def test_intel_reference_is_traceable_to_an_official_vector_publication(self):
        import xml.etree.ElementTree as ET
        root = Path(__file__).parents[1]
        prototype = root / 'prototypes/theme-lab/themes/intel'
        shipped = root / 'agent_theme/themes/assets'
        provenance = json.loads((prototype/'provenance.json').read_text())
        self.assertEqual(provenance['url'], 'https://cdrdv2-public.intel.com/841119/317804.pdf')
        self.assertEqual(provenance['page'], 1)
        self.assertEqual(provenance['sha256'],
            'c554f4c7a26dacf291051125c59b0761c978af4cace9fb15863d119fcbf8de22')
        self.assertEqual((prototype/'source.svg').read_bytes(), (shipped/'intel-source.svg').read_bytes())
        self.assertEqual((prototype/'provenance.json').read_bytes(), (shipped/'intel-provenance.json').read_bytes())
        self.assertEqual(hashlib.sha256((prototype/'source.svg').read_bytes()).hexdigest(),
                         provenance['svg_sha256'])
        paths = json.loads((prototype/'official-paths.js').read_text().split(' = ',1)[1].rstrip(';\n'))
        svg = ET.parse(prototype/'source.svg')
        for part in ('letters','oval','registration'):
            self.assertEqual(svg.find(".//*[@id='%s']" % part).attrib['d'], paths[part])
        self.assertEqual(paths['eBox'], provenance['e_box'])
        self.assertEqual(paths['eGrid'], provenance['terminal_e_grid'])
        self.assertEqual(paths['eOmit'], provenance['terminal_e_omit'])
        # Uniform normalization cannot distort letters relative to the oval.
        transform = provenance['normalization']
        self.assertEqual(transform[0], transform[3])
        self.assertEqual((transform[1],transform[2]), (0,0))

    def test_intel_header_chip_has_a_square_footprint(self):
        from agent_theme.themes.raster import decode
        asset = get_theme('intel').art
        for palette in ('dark', 'light'):
            pixels = decode(asset['headers'][palette]['octant'], 18, 12)
            points = [(x,y) for y in range(12) for x in range(18) if pixels[y*18+x]]
            width = max(x for x,y in points)-min(x for x,y in points)+1
            height = max(y for x,y in points)-min(y for x,y in points)+1
            self.assertEqual((width,height), (12,12))
            self.assertLess(abs(height*art.SUB_ASPECT/width-1), .1)

    @staticmethod
    def assert_intel_e_has_no_single_pixel_spurs(test, asset):
        from agent_theme.themes.raster import cells, decode, RasterMark
        for cols in (49, 77, 107):
            mark = RasterMark(cols, 0, asset)
            width, height = cols*2, mark.logo_rows*4
            for palette in ('dark', 'light'):
                pixels = decode(asset['frames'][palette]['still'], 192, 128)
                lattice = cells(pixels, 192, 128, width, height, asset['palette'], 'octant')
                points = set()
                for row, line in enumerate(lattice):
                    for col, (bits, fg, bg) in enumerate(line):
                        for bit in range(8):
                            x,y = col*2+bit%2, row*4+bit//2
                            if (103*width/192 <= x < 135*width/192
                                    and 47*height/128 <= y < 86*height/128
                                    and (bg is not None or bits >> bit & 1)):
                                points.add((x,y))
                test.assertTrue(points)
                spurs = [(x,y) for x,y in points if sum((x+dx,y+dy) in points
                         for dx,dy in ((1,0),(-1,0),(0,1),(0,-1))) < 2]
                test.assertEqual(spurs, [], (cols, palette))

    def test_intel_e_has_no_single_pixel_spurs_at_terminal_sizes(self):
        self.assert_intel_e_has_no_single_pixel_spurs(self, get_theme('intel').art)

    @staticmethod
    def assert_intel_terminal_tip_is_flat(test, asset):
        from agent_theme.themes.raster import decode
        for palette in ('dark', 'light'):
            pixels = decode(asset['frames'][palette]['still'], 192, 128)
            # The raised cap disappears; the adjacent diagonal stroke stays intact.
            for x in (125, 126):
                test.assertEqual(pixels[72*192+x], 0, (palette, x))
                test.assertNotEqual(pixels[73*192+x], 0, (palette, x))

    def test_intel_terminal_tip_does_not_have_a_raised_two_pixel_cap(self):
        self.assert_intel_terminal_tip_is_flat(self, get_theme('intel').art)

    def test_intel_idle_colours_never_change_the_wordmark_silhouette(self):
        from agent_theme.themes.raster import decode
        asset = get_theme('intel').art
        for palette in ('dark', 'light'):
            frames = asset['frames'][palette]
            expected = bytes(bool(v) for v in decode(frames['still'], 192, 128))
            for index, frame in enumerate(frames['idle']):
                actual = bytes(bool(v) for v in decode(frame, 192, 128))
                self.assertEqual(actual, expected, (palette, index))
            self.assertTrue(any(frame != frames['still'] for frame in frames['idle']))

    def test_raster_titles_use_their_ink_bounds(self):
        from tools.build_theme_art import title_bounds
        for name in THEME_NAMES[2:]:
            asset = get_theme(name).art
            self.assertEqual(asset['word_bbox'], title_bounds(asset['word_polys']), name)

    def test_amd_copy_fits_a_short_brand_line(self):
        copy = get_theme('amd').brands['claude']
        self.assertEqual(copy.slogan, 'Together We Advance')
        self.assertEqual(copy.tagline, 'High-Performance Computing')


if __name__=='__main__':unittest.main()
