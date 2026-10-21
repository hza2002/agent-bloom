"""Input tracking and submission must preserve commands and stop home decoration."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.dont_write_bytecode = True

from agent_theme import art, intro, overlay
from agent_theme.animation import make_animated_overlay


class InputTrackingTests(unittest.TestCase):
    def make(self):
        return overlay.ClaudeOverlay(120, 32, art.BRANDS['claude'])

    def test_large_paste_retains_tail_and_edit_controls(self):
        state = self.make()
        state.note_input(b'x' * (2 * 1024 * 1024) + '\u4e2d\U0001f600'.encode())
        self.assertEqual(state.typed, 'x' * 62 + '\u4e2d\U0001f600')
        state.note_input(b'\x7f\x08')
        self.assertEqual(state.typed, 'x' * 62)
        state.note_input(b'\x15/clear\r')
        self.assertEqual(state.typed, '')
        self.assertTrue(state.submitted)
        self.assertTrue(state.is_fresh())

    def test_submitted_home_is_erased_once_and_clear_rearms_it(self):
        for base, brand in ((overlay.ClaudeOverlay, 'claude'),
                            (overlay.CodexOverlay, 'codex')):
            with self.subTest(app=brand):
                cls = make_animated_overlay(base, intro)
                state = cls(120, 32, art.BRANDS[brand], in_alt=True,
                            reveal=False, play_intro=False)
                state.feed(b'\x1b[2J\x1b[2;1Hheader\x1b[30;1Hprompt')
                self.assertTrue(state.visible)
                state.note_input(b'hello\r')
                ack = b'\x1b[30;1Hresponse'
                with mock.patch.object(state, '_paint', wraps=state._paint) as paint:
                    state.feed(ack)
                    state.tick()
                    self.assertFalse(state.visible)
                    for _ in range(30):
                        self.assertEqual(state.feed(ack), ack)
                        self.assertEqual(state.tick(), b'')
                    paint.assert_not_called()
                state.note_input(b'/clear\r')
                state.feed(b'\x1b[30;1Hprompt  ')
                self.assertFalse(state.submitted)
                self.assertTrue(state.visible)


if __name__ == '__main__':
    unittest.main()
