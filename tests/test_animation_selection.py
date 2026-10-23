"""CLI candidate selection and Apple motion contracts, independent of a live app."""
import contextlib
import io
import os
import unittest
from unittest.mock import patch

from agent_theme import art, cli
from agent_theme.apps import PROFILES
from agent_theme.launcher import Launcher
from agent_theme.themes import get_theme


class SelectionTests(unittest.TestCase):
    def test_candidate_semantics_and_validation(self):
        theme = get_theme('apple')
        self.assertEqual(theme.candidates(), ('spectrum', 'constellation'))
        self.assertEqual(theme.candidates('spectrum, constellation,spectrum'),
                         ('spectrum', 'constellation'))
        for value in ('', ',', 'spectrum,', ',spectrum', 'random,spectrum',
                      'bloom', '../spectrum', 'SPECTRUM'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                theme.candidates(value)
        with self.assertRaises(ValueError):
            get_theme().candidates('constellation')
        self.assertEqual(get_theme().candidates('random'), ('bloom',))

    def test_cli_resolves_against_final_theme_and_preserves_app_arguments(self):
        _, args, overrides, _, _ = cli.parse([
            '--animation=spectrum,constellation', 'codex', '--theme', 'apple',
            '--', '--animation', 'literal', '--list'])
        self.assertEqual(args, ['--animation', 'literal', '--list'])
        self.assertEqual(dict(overrides)['animation'], 'spectrum,constellation')
        for argv in (['--animation'], ['--animation=', 'claude'],
                     ['--theme', 'apple', '--animation=bloom', 'codex'],
                     ['--theme', 'orbit', 'codex']):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    cli.parse(argv)
                self.assertEqual(caught.exception.code, 2)

    def test_list_is_standalone_and_does_not_choose(self):
        for argv, present, absent in ((['--list'], 'huawei', None),
                                     (['--list', '--theme=apple'], 'constellation', 'huawei')):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch('agent_theme.themes.random.choice') as choose:
                with self.assertRaises(SystemExit) as caught:
                    cli.parse(argv)
            self.assertEqual(caught.exception.code, 0)
            self.assertIn(present, output.getvalue())
            self.assertIn('spectrum', output.getvalue())
            if absent:
                self.assertNotIn(absent, output.getvalue())
            choose.assert_not_called()
        for argv in (['--list', '--check'], ['--list', '--raw'],
                     ['--list', '--animation=random'], ['--list', 'codex', 'resume']):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                cli.parse(argv)
            self.assertEqual(caught.exception.code, 2)

    def test_fixed_selection_does_not_call_random_and_templates_are_unchanged(self):
        theme = get_theme('apple')
        with patch('agent_theme.themes.random.choice') as choose:
            key, selected = theme.select_animation('constellation,constellation')
        choose.assert_not_called()
        self.assertEqual(key, 'constellation')
        self.assertEqual(selected.brands['claude'].slogan, 'Choose your superpower')
        self.assertEqual(theme.brands['claude'].slogan, 'Choose your superpower')
        self.assertEqual(selected.art['gradient']['type'], 'bands')
        self.assertEqual(theme.art['gradient']['type'], 'bands')

    def test_launch_pins_choice_through_reconstruction_resize_and_clear(self):
        profile = PROFILES['claude']
        with patch('agent_theme.themes.random.choice', return_value='constellation') as choose:
            launcher = Launcher(profile, 'claude', [], dict(profile.defaults, theme='apple',
                                animation='spectrum,constellation'))
            home = b'\x1b[?1049h\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H'
            for _ in range(2):
                state = launcher._make_overlay(120, 40)
                with patch('time.monotonic', return_value=100):
                    state.feed(home)
                    state.tick()
                self.assertEqual(type(state.anim_scene).__name__, 'Constellation')
                state.resize(120, 40)
                state.note_input(b'/clear\r')
                state.feed(home)
                state.tick()
                self.assertEqual(state.brand.slogan, 'Choose your superpower')
            choose.assert_called_once_with(('spectrum', 'constellation'))
        self.assertEqual(launcher.animation, 'constellation')

    def test_check_exercises_every_candidate(self):
        with patch('sys.argv', ['agent-bloom', '--theme=apple', '--check', 'codex']), \
                patch.object(cli, 'binary_check', return_value=[]), \
                patch.object(cli, 'engine_check', wraps=cli.engine_check) as check, \
                contextlib.redirect_stdout(io.StringIO()), \
                patch('agent_theme.themes.random.choice') as choose:
            self.assertEqual(cli.main(), 0)
        self.assertEqual(check.call_count, 2)
        self.assertEqual({call.args[1].brands['codex'].slogan for call in check.call_args_list},
                         {'Choose your superpower'})
        choose.assert_not_called()


class AppleMotionTests(unittest.TestCase):
    def test_frames_stay_inside_owned_region_and_settle_exactly(self):
        for key in ('spectrum', 'constellation'):
            _, theme = get_theme('apple').select_animation(key)
            for mode in ('octant', 'quadrant'):
                with patch.dict(os.environ, AGENT_THEME_GLYPHS=mode):
                    art.reset_glyphs()
                    for size in ((20, 12), (80, 30), (111, 55)):
                        for palette in (theme.dark, theme.light):
                            with self.subTest(key=key, mode=mode, size=size, palette=palette):
                                brand = theme.brands['claude']
                                lock = art.choose(brand, size[0], size[1] - 4)
                                scene = theme.create_scene(*size, palette, brand, lock=lock, top=2)
                                if not scene.ok:
                                    continue
                                expected = {}
                                for row, entries in art.home_rows(lock, 2, 1.0, palette).items():
                                    if row >= scene.y1:
                                        continue
                                    for left, cells in entries:
                                        for col, (ch, rgb, _) in enumerate(cells, left):
                                            if ch != ' ':
                                                expected[row, col] = ch, rgb
                                self.assertEqual(scene.frame(scene.duration), expected)
                                self.assertEqual(scene.ambient_frame(0), expected)
                                self.assertEqual(scene.ambient_frame(1), expected)
                                self.assertEqual(scene.frame(2.99), scene.frame(2.99))
                                for stamp in (0, .2, .7, 1.4, 2.05, 2.5, 3.19):
                                    for row, col in scene.frame(stamp):
                                        self.assertTrue(scene.y0 <= row < scene.y1)
                                        self.assertTrue(scene.x0 <= col < scene.x1)
                                scene.pal = theme.light
                                expected_word = {(2 + lock.word_top + r, lock.centre(scene.mark.word_cols) + c): cell
                                                 for r, line in enumerate(scene.mark.word_cells(theme.light))
                                                 for c, cell in enumerate(line) if cell[0] != ' '}
                                self.assertEqual({pos: scene.frame(scene.duration)[pos] for pos in scene.word},
                                                 expected_word)
        art.reset_glyphs()

    def test_distinct_motion_and_no_mark_fallback(self):
        scenes = []
        for key in ('spectrum', 'constellation'):
            _, theme = get_theme('apple').select_animation(key)
            brand = theme.brands['codex']
            lock = art.choose(brand, 111, 49)
            scene = theme.create_scene(111, 55, theme.dark, brand, lock=lock, top=3)
            self.assertNotEqual(scene.frame(.7), scene.frame(1.4))
            self.assertEqual(scene.frame(0), {})
            scenes.append(scene)
            self.assertFalse(theme.create_scene(10, 3, theme.dark, brand).ok)
        self.assertNotEqual(scenes[0].frame(1), scenes[1].frame(1))


if __name__ == '__main__':
    unittest.main()
