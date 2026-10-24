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
                elif token.endswith('C'):
                    self.col += int(token[2:-1] or '1')
                elif token.endswith('D'):
                    self.col -= int(token[2:-1] or '1')
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

    def test_nintendo_header_dots_are_isolated_two_by_two_in_both_modes(self):
        asset = get_theme('nintendo').art
        for palette in ('dark', 'light'):
            for mode in ('octant', 'quadrant'):
                pixels = decode(asset['headers'][palette][mode], 18, 12)
                # Find disconnected ink on the left and enclosed holes on the
                # right, independently of the hand-authored pixel coordinates.
                for start, stop, ink in ((0, 9, True), (9, 18, False)):
                    remaining = {(x, y) for y in range(12) for x in range(start, stop)
                                 if bool(pixels[y * 18 + x]) == ink}
                    components = []
                    while remaining:
                        pending = [remaining.pop()]
                        component = set(pending)
                        while pending:
                            x, y = pending.pop()
                            for point in ((x+dx, y+dy) for dx in (-1, 0, 1)
                                          for dy in (-1, 0, 1) if dx or dy):
                                if point in remaining:
                                    remaining.remove(point)
                                    component.add(point)
                                    pending.append(point)
                        components.append(component)
                    if ink:
                        self.assertEqual(len(components), 2, 'dot must not touch the shell')
                        dot = min(components, key=len)
                    else:
                        holes = [c for c in components if all(
                            start < x < stop-1 and 0 < y < 11 for x, y in c)]
                        self.assertEqual(len(holes), 1)
                        dot = holes[0]
                    with self.subTest(palette=palette, mode=mode, ink=ink):
                        self.assertEqual(len(dot), 4)
                        self.assertEqual(max(x for x, y in dot)-min(x for x, y in dot)+1, 2)
                        self.assertEqual(max(y for x, y in dot)-min(y for x, y in dot)+1, 2)

    def test_mario_header_moves_right_without_clipping_or_moving_following_text(self):
        theme = get_theme('mario')
        self.assertEqual(theme.art['layout']['header_offset_cols'], 1)
        for mode in ('octant', 'quadrant'):
            with patch.dict(os.environ, AGENT_THEME_GLYPHS=mode):
                art.reset_glyphs()
                for palette in ('dark', 'light'):
                    with patch.dict(os.environ, AGENT_THEME_PALETTE=palette):
                        original = art._colour_header_rows(
                            theme.art['header_cells_by_palette'][palette][mode])
                        shifted = art.header_rows(theme)
                        for before, after in zip(original, shifted):
                            baseline, actual = ColourTerminal(), ColourTerminal()
                            baseline.col = actual.col = 1
                            actual.bg = (255, 0, 255)
                            baseline.feed(before.decode())
                            actual.feed(after.decode())
                            self.assertEqual(actual.col, baseline.col)
                            self.assertEqual(actual.screen[0, 1][0], ' ')
                            self.assertIsNone(actual.screen[0, 1][2])
                            for (row, col), cell in baseline.screen.items():
                                self.assertEqual(actual.screen[row, col+1], cell)
                            # Claude places the adjacent text at column 12.
                            baseline.feed('\x1b[1;12HT')
                            actual.feed('\x1b[1;12HT')
                            self.assertEqual(actual.screen[0, 11], baseline.screen[0, 11])
                            self.assertTrue(all(col < 11 for row, col in actual.screen
                                                if (row, col) != (0, 11)))

    def test_compact_footers_survive_first_ambient_frame_and_completion(self):
        from agent_theme.animation import make_animated_overlay
        from agent_theme.overlay import ClaudeOverlay
        for name in ('google', 'nintendo', 'intel', 'amd'):
            theme = get_theme(name)
            cls = make_animated_overlay(ClaudeOverlay, theme.create_scene)
            state = cls(81, 40, theme.brands['claude'], in_alt=True,
                        reveal=False, play_intro=False, pal=theme.dark)
            state.known = state.entered_alt = True
            for row in (1, 2, 36, 37, 38, 39):
                state.count[row] = 1
            terminal = ColourTerminal()
            with patch('time.monotonic', return_value=100):
                terminal.feed(state._frame_end().decode())
            self.assertIsNotNone(state.anchor)
            lock, top, _ = state.anchor
            row = top + lock.slogan_top
            def slogan():
                return ''.join(terminal.screen.get((row, col), (' ', None, None))[0]
                               for col in range(state.cols)).strip()
            expected = theme.brands['claude'].slogan
            self.assertEqual(slogan(), expected, 'exercise a visible static footer')
            state.ambient_next = 100
            for stamp in (100, 100.05, 102.1):
                # A repaint invalidates the frame cache; completion must also be
                # safe if backpressure skipped the intermediate sweep frames.
                if state.anim_scene is not None:
                    state.anim_scene.invalidate()
                with patch('time.monotonic', return_value=stamp):
                    terminal.feed(state.tick().decode())
                with self.subTest(theme=name, stamp=stamp):
                    self.assertEqual(slogan(), expected)
            self.assertIsNone(state.ambient_start)

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
            self.assertIn('Inter',asset.get('title_source',''),name)
            # Release 4.1 embeds an internal 4.001 version; verify the actual font.
            self.assertEqual(asset.get('title_font_sha256'),
                '4989b125924991b90d05b2d16e0e388c48f7d5bb8b30539bbf9c755278d0ccaf',name)


if __name__=='__main__':unittest.main()
