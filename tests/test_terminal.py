import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme.themes import get_theme
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
            self.assertEqual(art.OCTANTS[1], art.OCTANT_TABLE[1])


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


class TmuxVisibilityTests(unittest.TestCase):
    def test_no_tmux_is_visible_without_a_query(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(terminal.subprocess, 'Popen') as check:
            self.assertTrue(terminal.TmuxVisibility()())
            check.assert_not_called()


class AsyncVisibilityTests(unittest.TestCase):
    @mock.patch.dict(os.environ, {'TMUX': '1', 'TMUX_PANE': '%1'}, clear=True)
    def test_pending_query_never_waits_and_only_launches_one_process(self):
        probe = terminal.TmuxVisibility()
        proc = mock.Mock()
        proc.poll.return_value = None
        with mock.patch.object(terminal.subprocess, 'Popen', return_value=proc) as start, \
             mock.patch.object(terminal.os, 'set_blocking'), \
             mock.patch.object(terminal.time, 'monotonic', return_value=100):
            self.assertIsNone(probe())
            for _ in range(10):
                self.assertIsNone(probe())
            start.assert_called_once()
            proc.wait.assert_not_called()
            proc.communicate.assert_not_called()
        # Deadline expiry signals the child, then reaping is polled too.
        with mock.patch.object(terminal.time, 'monotonic', return_value=101):
            self.assertIsNone(probe())
            proc.kill.assert_called_once()
            proc.poll.return_value = -9
            self.assertTrue(probe())
        self.assertIsNone(probe.process)

    @mock.patch.dict(os.environ, {'TMUX': '1', 'TMUX_PANE': '%1'}, clear=True)
    def test_completed_query_and_cleanup(self):
        probe = terminal.TmuxVisibility()
        proc = mock.Mock()
        proc.poll.return_value = 0
        with mock.patch.object(terminal.subprocess, 'Popen', return_value=proc), \
             mock.patch.object(terminal.os, 'set_blocking'), \
             mock.patch.object(terminal.os, 'read', return_value=b'1 0 1 0\n'):
            self.assertIsNone(probe())
            self.assertFalse(probe())
            self.assertIsNone(probe.process)
            self.assertIsNone(probe())
            proc.poll.return_value = None
            probe.close()
            proc.kill.assert_called_once()
            proc.wait.assert_called_once()
        self.assertIsNone(probe.process)

    def test_visibility_includes_unfocused_visible_split_panes(self):
        cases = {
            '1 1 1 0': True,
            '1 1 0 0': True,
            '1 1 0 1': False,
            '1 1 1 1': True,
            '2 1 1 0': True,
            '0 1 1 0': False,
            '1 0 1 0': False,
            '1 1': True,
        }
        for state, expected in cases.items():
            with self.subTest(state=state), \
                 mock.patch.dict(os.environ, {'TMUX': '1', 'TMUX_PANE': '%1'},
                                 clear=True), \
                 mock.patch.object(terminal.subprocess, 'Popen') as start, \
                 mock.patch.object(terminal.os, 'set_blocking'), \
                 mock.patch.object(terminal.os, 'read', return_value=state.encode()):
                start.return_value.poll.return_value = 0
                probe = terminal.TmuxVisibility()
                self.assertIsNone(probe())
                self.assertEqual(probe(), expected)

    def test_query_failure_fails_open(self):
        with mock.patch.dict(os.environ, {'TMUX': '1', 'TMUX_PANE': '%1'},
                             clear=True), \
             mock.patch.object(terminal.subprocess, 'Popen',
                               side_effect=OSError('no tmux')):
            self.assertTrue(terminal.TmuxVisibility()())


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


if __name__ == '__main__':
    unittest.main()
