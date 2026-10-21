import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme import art, terminal  # noqa: E402


class PaletteDetectionTests(unittest.TestCase):
    def test_colorfgbg_dark(self):
        with mock.patch.dict(os.environ, {'COLORFGBG': '15;0'}, clear=True):
            terminal.detect_palette()
            self.assertEqual(os.environ['AGENT_THEME_PALETTE'], 'dark')

    def test_colorfgbg_light(self):
        with mock.patch.dict(os.environ, {'COLORFGBG': '0;15'}, clear=True):
            terminal.detect_palette()
            self.assertEqual(os.environ['AGENT_THEME_PALETTE'], 'light')

    def test_explicit_value_wins(self):
        with mock.patch.dict(os.environ, {'AGENT_THEME_PALETTE': 'light',
                                          'COLORFGBG': '15;0'}, clear=True):
            terminal.detect_palette()
            self.assertEqual(os.environ['AGENT_THEME_PALETTE'], 'light')


class GlyphDetectionTests(unittest.TestCase):
    def tearDown(self):
        art.reset_glyphs()

    def test_ghostty_client_switches_to_octant(self):
        with mock.patch.dict(os.environ, {'TERM_PROGRAM': 'tmux',
                                          'TERM': 'tmux-256color',
                                          'TMUX': '1'}, clear=True):
            art.reset_glyphs()
            quadrant = art.OCTANTS[1]
            with mock.patch.object(terminal.subprocess, 'check_output',
                                   return_value='xterm-ghostty\n'):
                terminal.detect_glyphs()
            self.assertEqual(os.environ['AGENT_THEME_GLYPHS'], 'octant')
            self.assertNotEqual(art.OCTANTS[1], quadrant)
            self.assertEqual(art.OCTANTS[1], art.ART['octants'][1])


class TmuxNameTests(unittest.TestCase):
    @mock.patch.dict(os.environ, {'TMUX_PANE': '%1'}, clear=True)
    def test_renames_an_auto_renamed_window(self):
        with mock.patch.object(terminal.subprocess, 'check_output',
                               return_value='1\n') as check, \
             mock.patch.object(terminal.subprocess, 'run') as run:
            self.assertTrue(terminal.name_tmux_window('claude'))
            check.assert_called_once()
            self.assertEqual(run.call_args.args[0][1:3], ['rename-window', '-t'])

    @mock.patch.dict(os.environ, {'TMUX_PANE': '%1'}, clear=True)
    def test_restore_respects_a_manual_rename(self):
        with mock.patch.object(terminal.subprocess, 'check_output',
                               return_value='0\tmyname\n'), \
             mock.patch.object(terminal.subprocess, 'run') as run:
            terminal.restore_tmux_autorename('claude')
            run.assert_not_called()

    @mock.patch.dict(os.environ, {'TMUX_PANE': '%1'}, clear=True)
    def test_restore_enables_auto_after_its_own_rename(self):
        with mock.patch.object(terminal.subprocess, 'check_output',
                               return_value='0\tclaude\n'), \
             mock.patch.object(terminal.subprocess, 'run') as run:
            terminal.restore_tmux_autorename('claude')
            run.assert_called_once()

    @mock.patch.dict(os.environ, {'TMUX_PANE': '%1'}, clear=True)
    def test_leaves_a_manual_window_name_alone(self):
        with mock.patch.object(terminal.subprocess, 'check_output',
                               return_value='0\n'), \
             mock.patch.object(terminal.subprocess, 'run') as run:
            self.assertFalse(terminal.name_tmux_window('claude'))
            run.assert_not_called()


class AltScreenTests(unittest.TestCase):
    def test_split_alt_sequences_are_detected(self):
        from agent_theme.apps import PROFILES
        from agent_theme.launcher import Launcher
        launcher = Launcher(PROFILES['claude'], 'claude', [], {})
        launcher._note_alt(b'\x1b[?104')
        self.assertFalse(launcher.app_alt)
        launcher._note_alt(b'9h')
        self.assertTrue(launcher.app_alt)


class ExitCodeTests(unittest.TestCase):
    def test_normal_and_signal_statuses(self):
        self.assertEqual(terminal.exit_code(7 << 8), 7)
        self.assertEqual(terminal.exit_code(15), 128 + 15)
        self.assertEqual(terminal.exit_code(9), 128 + 9)


class WriteTests(unittest.TestCase):
    def test_write_all_handles_a_short_write(self):
        read_fd, write_fd = os.pipe()
        try:
            terminal.write_all(write_fd, b'hello')
            self.assertEqual(os.read(read_fd, 16), b'hello')
        finally:
            os.close(read_fd)
            os.close(write_fd)


if __name__ == '__main__':
    unittest.main()
