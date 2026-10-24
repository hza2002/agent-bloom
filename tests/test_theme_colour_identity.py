"""Keep the Microsoft panes distinct and the Chinese title independent of bitmaps."""
import os
import unittest
from unittest.mock import patch

from agent_theme import art
from agent_theme.themes import get_theme
from agent_theme.themes.raster import decode

COLOURS=((242,80,34),(127,186,0),(0,164,239),(255,185,0))


def pane(rgb):
    return min(range(4),key=lambda i:sum((a-b)**2 for a,b in zip(rgb,COLOURS[i])))


class ThemeColourIdentityTests(unittest.TestCase):
    def tearDown(self):art.reset_glyphs()

    def test_microsoft_boundary_pixels_never_change_to_a_neighbouring_pane(self):
        asset=get_theme('microsoft').art
        for mode in ('octant','quadrant'):
            with patch.dict(os.environ,AGENT_THEME_GLYPHS=mode):
                art.reset_glyphs();inverse={char:bits for bits,char in enumerate(art.glyphs())}
                mark=art.Mark(60,5,asset);w,h=mark.logo_cols*2,mark.logo_rows*4
                for palette in ('dark','light'):
                    sequences=asset['frames'][palette]
                    samples=[sequences['intro']['converge'][i] for i in (36,48,60)]
                    samples += [sequences['idle'][i] for i in (15,30,45)]
                    for frame in samples:
                        raw=decode(frame,192,128)
                        picture=mark.picture(frame,palette,mode)
                        for cy,line in enumerate(picture):
                            for cx,(char,colour) in enumerate(line):
                                if colour is None:continue
                                fg,bg=colour if len(colour)==2 else (colour,None)
                                bits=inverse[char]
                                for bit in range(8):
                                    rgb=fg if bits>>bit&1 else bg
                                    if rgb is None:continue
                                    x,y=cx*2+bit%2,cy*4+bit//2
                                    if mode=='quadrant':y=y//2*2
                                    source=raw[min(127,int((y+.5)*128/h))*192+min(191,int((x+.5)*192/w))]
                                    if source:
                                        self.assertEqual(pane(rgb),pane(asset['palette'][source]),
                                            f'{palette}/{mode}: neighbouring pane recoloured pixel {x},{y}')

    def test_nintendo_chinese_title_is_a_dedicated_vector_font(self):
        asset=get_theme('nintendo').art
        self.assertTrue(asset.get('word_polys'))
        self.assertIn('Noto Sans SC',asset.get('title_source',''))
        self.assertEqual(asset['wordmark'],'任天堂')


if __name__=='__main__':unittest.main()
