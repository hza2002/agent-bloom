"""Diagnostics must remain bounded, private and optional."""
import fcntl
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_theme import animation, art, diagnostics, intro, overlay


class DiagnosticsTests(unittest.TestCase):
    def test_bounded_file_replaces_old_records(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'debug.log'
            with patch.object(diagnostics, 'DEBUG', str(path)), patch.object(diagnostics, 'MAX_BYTES', 100):
                diagnostics.debug('old' * 20)
                diagnostics.debug('recent' * 6)
            self.assertLessEqual(path.stat().st_size, 100)
            self.assertNotIn('old', path.read_text())
            self.assertIn('recent', path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_disabled_and_unwritable_are_harmless(self):
        with patch.object(diagnostics, 'DEBUG', None), patch.object(diagnostics.os, 'open') as opened:
            diagnostics.debug('ignored')
            opened.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(diagnostics, 'DEBUG', directory):
                diagnostics.debug('ignored')

    def test_busy_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'debug.log'
            with path.open('w') as locked, patch.object(diagnostics, 'DEBUG', str(path)):
                fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
                diagnostics.debug('skip')
            self.assertEqual(path.read_bytes(), b'')

    def test_state_changes_only_and_no_input_text(self):
        state = animation.make_animated_overlay(overlay.ClaudeOverlay, intro)(100, 40, art.BRANDS['claude'])
        with patch.object(animation, 'DEBUG', True), patch.object(animation, 'debug') as log:
            self.assertIsNone(state.next_timeout())
            state.next_timeout()
            self.assertEqual(log.call_count, 1)
            self.assertEqual(log.call_args.args[1], 'unknown-screen')
            state.known = True
            state.next_timeout()
            self.assertEqual(log.call_args.args[1], 'main-screen')
            state.alt = True
            state.note_input(b'secret prompt\r')
            state.next_timeout()
            self.assertEqual(log.call_args.args[1], 'submitted')
            state.passthrough = True
            state.next_timeout()
            self.assertEqual(log.call_args.args[1], 'passthrough')
            self.assertNotIn('secret', str(log.call_args_list))

    def test_unicode_stop_reports_reason_without_output(self):
        state = overlay.ClaudeOverlay(100, 40, art.BRANDS['claude'])
        with patch.object(overlay, 'debug') as log:
            state.feed('private 😀'.encode())
        self.assertTrue(state.passthrough)
        self.assertIn('unsupported-text-width', str(log.call_args_list))
        self.assertNotIn('private', str(log.call_args_list))
