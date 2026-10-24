"""Offline theme contracts: colour safety, timelines and terminal lifecycle."""
import os
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from agent_theme import art
from agent_theme.animation import make_animated_overlay
from agent_theme.apps import PROFILES
from agent_theme.themes import THEME_NAMES, get_theme
from agent_theme.themes.raster import decode
from tools.terminal_trace import decode as trace_bytes

NAMES = THEME_NAMES[2:]


class BuiltinThemeTests(unittest.TestCase):
    def tearDown(self):
        art.reset_glyphs()

    def test_all_baked_frames_are_complete_and_reference_the_palette(self):
        for name in NAMES:
            asset = get_theme(name).art
            for modes in asset['frames'].values():
                sequences = [modes['idle'], [modes['still']]] + list(modes['intro'].values())
                for sequence in sequences:
                    for frame in sequence:
                        pixels = decode(frame, 192, 128)
                        self.assertLess(max(pixels), len(asset['palette']), name)
            self.assertTrue(asset['sources'])
            self.assertTrue(asset['note'])

    def test_scene_bounds_endpoints_palette_changes_and_shared_word_motion(self):
        for name in NAMES:
            theme = get_theme(name)
            for mode in ('octant', 'quadrant'):
                with patch.dict(os.environ, AGENT_THEME_GLYPHS=mode):
                    art.reset_glyphs()
                    for cols, rows in ((24, 12), (81, 36), (120, 50)):
                        for pal in (theme.dark, theme.light):
                            with self.subTest(name=name, mode=mode, size=(cols, rows), light=pal is theme.light):
                                brand = theme.brands['claude']
                                lock = art.choose(brand, cols, rows-2)
                                scene = theme.create_scene(cols, rows, pal, brand, lock=lock, top=1)
                                if not scene.ok:
                                    continue
                                still = scene.settled()
                                self.assertEqual(scene.frame(3), still)
                                self.assertEqual(scene.frame(2.9), still)
                                self.assertEqual(scene.ambient_frame(0), still)
                                self.assertEqual(scene.ambient_frame(1), still)
                                for frame in (scene.frame(.8), scene.ambient_frame(.4), still):
                                    for row, col in frame:
                                        self.assertTrue(scene.y0 <= row < scene.y1)
                                        self.assertTrue(scene.x0 <= col < scene.x1)
                                self.assertNotEqual(scene.ambient_frame(.4), still)
                                scene.pal = theme.light
                                self.assertEqual(scene.frame(3), scene.settled())

    def test_header_palette_and_two_colour_backgrounds_cannot_leak(self):
        for name in NAMES:
            theme = get_theme(name)
            for mode in ('octant', 'quadrant'):
                with patch.dict(os.environ, AGENT_THEME_GLYPHS=mode):
                    art.reset_glyphs()
                    for pal in ('dark', 'light'):
                        with patch.dict(os.environ, AGENT_THEME_PALETTE=pal):
                            rows = art.header_rows(theme)
                            self.assertEqual(len(rows), 3, name)
                            for row in rows:
                                self.assertTrue(row.endswith(b'\x1b[39m\x1b[49m'), name)
        paired = ((200, 100, 30), (30, 60, 90))
        text = art.render_run([('▀', paired, False), (' ', None, False), ('x', (1, 2, 3), False)])
        self.assertIn('\x1b[49m ', text)
        self.assertIn('\x1b[38;2;1;2;3m', text.replace('22;', ''))

    def test_recorded_app_startups_submit_clear_and_resize(self):
        for file in (Path(__file__).parent/'fixtures/terminal').glob('*.json'):
            trace = json.loads(file.read_text())
            for name in NAMES:
                theme = get_theme(name)
                profile = PROFILES[trace['app']]
                cls = make_animated_overlay(profile.overlay_type(), theme.create_scene)
                state = cls(*trace['size'], theme.brands[trace['app']])
                with self.subTest(name=name, fixture=file.name):
                    with patch('time.monotonic', return_value=100):
                        state.feed(trace_bytes(trace['events'][0])); state.tick()
                    with patch('time.monotonic', return_value=100.6):
                        self.assertTrue(state.tick())
                    state.note_input(b'hello\r');state.tick()
                    self.assertTrue(state.submitted)
                    self.assertFalse(state.visible)
                    state.resize(*trace['size'])
                    self.assertEqual(state.tick(), b'')


if __name__ == '__main__':
    unittest.main()
