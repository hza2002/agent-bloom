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

    def test_checked_catalog_is_generated_from_validated_assets(self):
        directory=Path(__file__).parents[1]/'agent_theme/themes/assets'
        self.assertEqual(check_assets(directory),10)


if __name__=='__main__':unittest.main()
