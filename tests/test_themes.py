"""Built-in themes share transport/layout while owning independent visuals."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from agent_theme import art, cli, overlay
from agent_theme.apps import PROFILES
from agent_theme.animation import make_animated_overlay
from agent_theme.launcher import Launcher
from agent_theme.replacer import Replacer
from agent_theme.themes import THEME_NAMES, get_theme
from tools.terminal_trace import decode


HOME = b'\x1b[?1049h\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H'


class ThemeTests(unittest.TestCase):
    def test_theme_loading_waits_for_terminal_geometry_detection(self):
        script = '''
import os, sys
from agent_theme.apps import PROFILES
from agent_theme.launcher import Launcher
from agent_theme.themes import THEME_NAMES
for name in THEME_NAMES:
    Launcher(PROFILES['claude'], 'claude', [], dict(PROFILES['claude'].defaults, theme=name))
assert 'agent_theme.art' not in sys.modules
# Terminal detection publishes the cell ratio before constructing the overlay.
os.environ['AGENT_THEME_CELL_RATIO'] = '3.0'
launcher = Launcher(PROFILES['claude'], 'claude', [], dict(PROFILES['claude'].defaults, theme='apple'))
state = launcher._make_overlay(120, 40)
assert state is not None
from agent_theme import art
assert art.CELL_RATIO == 3.0
assert art.SUB_ASPECT == 1.5
'''
        result = subprocess.run([sys.executable, '-B', '-c', script],
                                cwd=Path(__file__).resolve().parents[1],
                                env=dict(os.environ, AGENT_THEME_CELL_RATIO='2.12'),
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_selection_and_argument_boundary(self):
        _, args, overrides, _, _ = cli.parse(
            ['--theme', 'apple', 'claude', '--theme=huawei', '--', '--theme', 'literal'])
        self.assertEqual(overrides, [('theme', 'apple'), ('theme', 'huawei')])
        self.assertEqual(args, ['--theme', 'literal'])
        for args in (['--theme'], ['--theme='], ['--theme', '../apple', 'claude']):
            with self.subTest(args=args), patch('sys.stderr', new=io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    cli.parse(args)
                self.assertEqual(caught.exception.code, 2)

    def test_each_theme_has_working_profiles_and_split_headers(self):
        for name in THEME_NAMES:
            theme = get_theme(name)
            for app, profile in PROFILES.items():
                with self.subTest(theme=name, app=app):
                    opts = dict(profile.defaults, theme=name, title=True)
                    self.assertTrue(all(ok for _, ok, _ in profile.check(opts)))
                    self.assertTrue(all(ok for _, ok, _ in cli.engine_check(profile, theme)))
                    expected = profile.replace(profile.sample, opts)
                    stream = Replacer(profile, opts)
                    output = b''.join(stream.feed(bytes([byte])) for byte in profile.sample)
                    self.assertEqual(output + stream.feed(b'', flush=True), expected)
                    self.assertIn(theme.brands[app].title.encode(), expected)
                    self.assertEqual(art.text_width(profile.header_name(opts,
                                     11 if app == 'claude' else 12).decode()),
                                     11 if app == 'claude' else 12)

    def test_instances_do_not_share_theme_or_palette_state(self):
        states = []
        for name in ('apple', 'huawei', 'apple'):
            profile = PROFILES['claude']
            launcher = Launcher(profile, 'claude', [], dict(profile.defaults, theme=name))
            state = launcher._make_overlay(120, 40)
            self.assertIsNotNone(state)
            self.assertEqual(state.brand.theme.key, name)
            launcher.overlay = state
            launcher.update_palette(b'\x1b]11;rgb:fa/fa/fa\x07')
            self.assertEqual(state.pal['accent'], get_theme(name).light['accent'])
            self.assertEqual(state.pal['bg'], (250, 250, 250))
            states.append(state)
        self.assertEqual(states[0].pal, states[2].pal)
        self.assertNotEqual(states[0].pal, states[1].pal)
        self.assertEqual(get_theme('apple').light['bg'], (250, 250, 250))
        self.assertNotEqual(art.header_rows(get_theme('apple')),
                            art.header_rows(get_theme('huawei')))

    def test_scene_settles_to_static_art_within_the_layout(self):
        for name in THEME_NAMES:
            theme = get_theme(name)
            for size in ((20, 10), (81, 40), (111, 55)):
                for palette in (theme.dark, theme.light):
                    with self.subTest(theme=name, size=size, palette=palette):
                        brand = theme.brands['claude']
                        lock = art.choose(brand, *size)
                        self.assertIsNotNone(lock)
                        scene = theme.create_scene(*size, palette, brand, lock=lock, top=0)
                        if not scene.ok:  # Huawei intentionally skips word-only layouts.
                            self.assertFalse(lock.show_mark)
                            continue
                        expected = {}
                        for row, entries in art.home_rows(lock, 0, 1.0, palette).items():
                            # Footer can now share rows with the transparent intro stage.
                            if row >= scene.y1 or (lock.show_small and row >= lock.slogan_top):
                                continue
                            for left, cells in entries:
                                for col, (ch, rgb, _) in enumerate(cells, left):
                                    if ch != ' ':
                                        expected[row, col] = (ch, rgb)
                        settled = scene.frame(scene.duration)
                        self.assertTrue(expected)
                        self.assertEqual(settled, expected)
                        self.assertTrue(scene.ansi(settled))
                        self.assertEqual(scene.ansi(settled), '')
                        scene.invalidate()
                        self.assertTrue(scene.ansi(settled))
                        for stamp in (0.0, 0.2, 0.7, 1.0):
                            cells = scene.frame(scene.duration * stamp)
                            for row, col in cells:
                                self.assertTrue(0 <= row < size[1] and 0 <= col < size[0])

    def test_apple_session_and_resize_preserve_safety(self):
        theme = get_theme('apple')
        for app, profile in PROFILES.items():
            with self.subTest(app=app):
                cls = make_animated_overlay(profile.overlay_type(), theme.create_scene)
                state = cls(120, 40, theme.brands[app], ambient=False)
                with patch('time.monotonic', return_value=100.0):
                    state.feed(HOME)
                    state.tick()
                with patch('time.monotonic', return_value=100.5):
                    self.assertTrue(state.tick())
                with patch('time.monotonic', return_value=104.0):
                    state.tick()
                state.note_input(b'hello\r')
                state.tick()
                self.assertTrue(state.submitted)
                self.assertFalse(state.visible)
                state.note_input(b'/clear\r')
                state.feed(HOME)
                self.assertTrue(state.visible)
                state.resize(120, 40)
                self.assertFalse(state.known)
                self.assertEqual(state.tick(), b'')
                state.feed(HOME)
                self.assertTrue(state.visible)
                state.feed(b'\x1b[40;1H' + '😀'.encode())
                self.assertTrue(state.quarantine)
                self.assertEqual(state.tick(), b'')

    def test_real_startup_recordings_allow_apple_intro(self):
        theme = get_theme('apple')
        fixtures = Path(__file__).parent / 'fixtures/terminal'
        for path in fixtures.glob('*.json'):
            trace = json.loads(path.read_text())
            profile = PROFILES[trace['app']]
            for chunk in (1, 4096):
                with self.subTest(fixture=path.name, chunk=chunk):
                    cls = make_animated_overlay(profile.overlay_type(), theme.create_scene)
                    state = cls(*trace['size'], theme.brands[trace['app']])
                    data = decode(trace['events'][0])
                    with patch('time.monotonic', return_value=100.0):
                        for start in range(0, len(data), chunk):
                            state.feed(data[start:start + chunk])
                        state.tick()
                    with patch('time.monotonic', return_value=100.5):
                        self.assertTrue(state.tick())
                        self.assertTrue(state.visible)


if __name__ == '__main__':
    unittest.main()
