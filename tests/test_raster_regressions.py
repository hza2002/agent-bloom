"""Production regressions that a final-frame dictionary comparison cannot detect."""
import os
import re
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace

from agent_theme import art
from agent_theme.scene import Scene
from agent_theme.themes import THEME_NAMES, get_theme
from agent_theme.themes.raster import cells, decode


class ColourTerminal:
    """Observe persisted cell colours, independently of the frame dictionary."""
    def __init__(self):
        self.fg=self.bg=None;self.row=self.col=0;self.screen={}

    def feed(self,output):
        for token in re.findall(r'\x1b\[[0-9;?]*[A-Za-z]|[^\x1b]',output):
            if token.startswith('\x1b['):
                if token.endswith('H'):
                    y,x=map(int,token[2:-1].split(';'));self.row,self.col=y-1,x-1
                elif token.endswith('m'):
                    args=list(map(int,token[2:-1].split(';')));i=0
                    while i<len(args):
                        if args[i]==0:self.fg=self.bg=None
                        elif args[i]==39:self.fg=None
                        elif args[i]==49:self.bg=None
                        elif args[i] in (38,48) and args[i+1]==2:
                            if args[i]==48:self.bg=tuple(args[i+2:i+5])
                            else:self.fg=tuple(args[i+2:i+5])
                            i+=4
                        i+=1
            elif token:
                self.screen[self.row,self.col]=(token,self.fg,self.bg);self.col+=1


class RasterRegressionTests(unittest.TestCase):
    def tearDown(self):
        art.reset_glyphs()
        art._MINI_CACHE.clear()

    def test_header_rows_preserve_a_single_origin_and_fit_the_actual_slot(self):
        for name in THEME_NAMES[2:]:
            asset=get_theme(name).art
            for palette in ('dark','light'):
                for mode in ('octant','quadrant'):
                    raw=decode(asset['headers'][palette][mode],18,12)
                    expected=cells(raw,18,12,18,12,asset['palette'],mode)
                    actual=asset['header_cells_by_palette'][palette][mode]
                    with self.subTest(name=name,palette=palette,mode=mode):
                        self.assertEqual(expected[0][8][0],0,'badge extends beyond first-row slot')
                        self.assertEqual(actual[0],expected[0][:8],'first row shifted relative to lower rows')
                        self.assertEqual(actual[1:],expected[1:])

    def test_colour_pair_run_resets_background_before_the_next_row(self):
        pair=((255,0,0),(0,255,0))
        run=art.render_run([('▀',pair,False)])
        self.assertIn('\x1b[48;2;0;255;0m',run)  # Exercise a real nondefault background.
        self.assertTrue(run.endswith('\x1b[49m'),repr(run))
        scene=Scene();scene.x0=0;scene.x1=8;scene.y0=0;scene.y1=3;scene.prev_cells={}
        scene.ansi({})
        output=scene.ansi({(0,7):('▀',pair),(1,1):('T',(238,238,233))})
        background=None;seen={};row=col=0
        # Independent SGR/CUP observer, including state carried between row writes.
        for token in re.findall(r'\x1b\[[0-9;?]*[A-Za-z]|[^\x1b]',output):
            if token.startswith('\x1b['):
                if token.endswith('H'):
                    y,x=map(int,token[2:-1].split(';'));row,col=y-1,x-1
                elif token.endswith('m'):
                    args=list(map(int,token[2:-1].split(';')))
                    i=0
                    while i<len(args):
                        if args[i] in (0,49):background=None
                        elif args[i] in (38,48) and args[i+1]==2:
                            if args[i]==48:background=tuple(args[i+2:i+5])
                            i+=4
                        i+=1
            elif token:
                seen[row,col]=(token,background);col+=1
        self.assertEqual(seen[0,7],('▀',(0,255,0)))
        self.assertEqual(seen[1,1],('T',None),'colour from hero leaked into the next row')

    def test_persisted_terminal_pixels_match_every_intro_idle_and_handoff_frame(self):
        for name in THEME_NAMES[2:]:
            theme=get_theme(name)
            for mode in ('octant','quadrant'):
                with patch.dict(os.environ,AGENT_THEME_GLYPHS=mode):
                    art.reset_glyphs()
                    for pal in (theme.dark,theme.light):
                        brand=theme.brands['claude'];lock=art.choose(brand,81,36)
                        scene=theme.create_scene(81,40,pal,brand,lock=lock,top=2)
                        terminal=ColourTerminal()
                        frames=[scene.frame(t) for t in (0,.4,1.1,1.7,2.4,2.9,3)]
                        frames += [scene.ambient_frame(t) for t in (.1,.3,.6,.9,1)]
                        for index,frame in enumerate(frames):
                            terminal.feed(scene.ansi(frame))
                            with self.subTest(name=name,mode=mode,light=pal is theme.light,frame=index):
                                for row in range(scene.y0,scene.y1):
                                    for col in range(scene.x0,scene.x1):
                                        ch,colour=frame.get((row,col),(' ',None))
                                        actual=terminal.screen.get((row,col),(' ',None,None))
                                        self.assertEqual(actual[0],ch)
                                        if ch==' ':
                                            self.assertIsNone(actual[2],'stale background in erased cell')
                                        else:
                                            fg,bg=colour if len(colour)==2 else (colour,None)
                                            self.assertEqual(actual[1:],(fg,bg),'terminal SGR differs from intended frame')

    def test_sixty_hz_scheduler_holds_each_thirty_fps_frame_for_two_ticks(self):
        theme=get_theme('google');brand=theme.brands['claude'];lock=art.choose(brand,81,36)
        scene=theme.create_scene(81,40,theme.dark,brand,lock=lock,top=2)
        picture=Mock(return_value=[])
        sequence=[str(i) for i in range(91)]
        scene.mark=SimpleNamespace(logo_cols=60,picture=picture,
            asset={'frames':{'dark':{'intro':{scene.variant:sequence}}}})
        for tick in range(180):
            scene._hero('intro',(tick/60)/3)
            self.assertEqual(picture.call_args.args[0],str(tick//2),'uneven frame hold at scheduler tick '+str(tick))

    def test_production_cadence_matches_the_approved_thirty_fps_timeline(self):
        for name in THEME_NAMES[2:]:
            asset=get_theme(name).art
            self.assertEqual(asset['fps'],30,name)
            for palette in asset['frames'].values():
                self.assertEqual(len(palette['idle']),61,name)
                for sequence in palette['intro'].values():self.assertEqual(len(sequence),91,name)

    def test_english_titles_use_vector_lettering_like_apple(self):
        for name in THEME_NAMES[2:]:
            if name=='nintendo':continue
            asset=get_theme(name).art
            self.assertTrue(asset.get('word_polys'),name)
            self.assertIn('Inter 4.1',asset.get('title_source',''),name)


if __name__=='__main__':unittest.main()
