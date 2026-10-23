"""Diagnostics stay bounded, private, structured and optional."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from agent_theme.themes import huawei_bloom as intro
from agent_theme.themes import get_theme
from agent_theme import animation, art, diagnostics, overlay


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'debug.log'
        diagnostics.set_context(app='codex', size='91x55')
        diagnostics.configure(str(self.path))

    def tearDown(self):
        diagnostics.configure(None)
        diagnostics.set_context()
        self.tmp.cleanup()

    def read(self):
        return self.path.read_text()

    def test_structured_event_has_context_and_row_ranges(self):
        diagnostics.event('band', decision='chosen', band='6-48',
                          used=(1, 2, 3, 5, 49, 50, 51, 52, 53, 54),
                          candidates=2, lock='mark,word,small', word_rows=6)
        text = self.read()
        self.assertIn('event=band', text)
        self.assertIn('decision=chosen', text)
        self.assertIn('band=6-48', text)
        self.assertIn('used=1-3,5,49-54', text)
        self.assertIn('app=codex', text)
        self.assertIn('size=91x55', text)
        self.assertIn('pid=', text)
        self.assertIn('candidates=2', text)

    def test_size_rotation_keeps_recent_records(self):
        diagnostics.configure(str(self.path), max_bytes=300, max_age=9999)
        diagnostics.event('old', payload='x' * 200)
        diagnostics.event('recent', payload='y' * 80)
        text = self.read()
        self.assertIn('event=log-start reason=size', text)
        self.assertNotIn('event=old', text)
        self.assertIn('event=recent', text)
        self.assertIn('reason=size', text)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [self.path])

    def test_age_rotation_keeps_recent_records(self):
        diagnostics.configure(str(self.path), max_bytes=100000, max_age=1)
        diagnostics.event('old')
        old = time.time() - 10
        os.utime(self.path, (old, old))
        diagnostics.event('recent')
        text = self.read()
        self.assertIn('event=log-start reason=age', text)
        self.assertNotIn('event=old', text)
        self.assertIn('event=recent', text)

    def test_disabled_and_unwritable_are_harmless(self):
        diagnostics.configure(None)
        diagnostics.event('ignored')
        self.assertFalse(self.path.exists())
        with tempfile.TemporaryDirectory() as directory:
            diagnostics.configure(directory)
            diagnostics.event('ignored')
            self.assertTrue(Path(directory).is_dir())

    def test_exception_logs_frames_without_its_message(self):
        try:
            raise RuntimeError('private application text')
        except RuntimeError as exc:
            diagnostics.exception('where', exc)
        text = self.read()
        self.assertIn('event=exception', text)
        self.assertIn('where=where', text)
        self.assertIn('type=RuntimeError', text)
        self.assertIn('frames=', text)
        self.assertNotIn('private', text)

    def test_state_changes_and_heartbeat_are_structured(self):
        state = animation.make_animated_overlay(
            overlay.ClaudeOverlay, intro.Bloom)(100, 40, get_theme().brands['claude'])
        state.next_timeout()
        self.assertIn('event=state', self.read())
        self.assertIn('reason=unknown-screen', self.read())
        state.known = True
        state.next_timeout()
        self.assertIn('reason=main-screen', self.read())
        state.alt = True
        state.note_input(b'private prompt\r')
        state.next_timeout()
        text = self.read()
        self.assertIn('reason=submitted', text)
        self.assertIn('event=input', text)
        self.assertNotIn('private', text)
        with patch.object(diagnostics, 'HEARTBEAT_SECONDS', 0.0):
            state.next_timeout()
        self.assertIn('event=heartbeat', self.read())

    def test_unsupported_text_reports_kind_without_text(self):
        state = overlay.ClaudeOverlay(100, 40, get_theme().brands['claude'])
        state.known = True
        state.alt = True
        state.entered_alt = True
        state.feed('private 😀'.encode())
        self.assertTrue(state.passthrough)
        text = self.read()
        self.assertIn('event=unsupported', text)
        self.assertIn('kind=emoji', text)
        self.assertNotIn('private', text)


if __name__ == '__main__':
    unittest.main()
