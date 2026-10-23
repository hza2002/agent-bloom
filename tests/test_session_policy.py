"""Screen repaint and session permission are independent."""
import unittest

from agent_theme.themes import huawei_bloom as intro
from agent_theme.themes import get_theme
from agent_theme import art, overlay
from agent_theme.animation import make_animated_overlay


class SessionPolicyTests(unittest.TestCase):
    def states(self):
        for name, base in (('claude', overlay.ClaudeOverlay), ('codex', overlay.CodexOverlay)):
            cls = make_animated_overlay(base, intro.Bloom)
            state = cls(120, 40, get_theme().brands[name], in_alt=True, play_intro=False)
            state.feed(b'\x1b[2J\x1b[2;1Hheader\x1b[39;1Hprompt\x1b[39;7H')
            self.assertTrue(state.visible)
            yield state

    def test_repaint_does_not_reopen_submitted_session(self):
        for state in self.states():
            state.note_input(b'hello\r')
            state.tick()
            state.feed(b'\x1b[2J\x1b[2;1Hanswer\x1b[39;1Hprompt\x1b[39;7H')
            state.tick()
            self.assertTrue(state.submitted)
            self.assertFalse(state.visible)

    def test_pasted_reset_is_not_a_session_reset(self):
        for state in self.states():
            state.note_input(b'hello\r')
            state.tick()
            state.note_input(b'\x1b[200~/clear\n\x1b[201~')
            state.feed(b'\x1b[39;1Hprompt\x1b[39;7H')
            self.assertTrue(state.submitted)
            self.assertFalse(state.is_fresh())
            self.assertFalse(state.visible)

    def test_reset_needs_application_output(self):
        for state in self.states():
            state.note_input(b'hello\r')
            state.tick()
            state.note_input(b'/clear\r')
            state._band()
            state.tick()
            self.assertTrue(state.submitted)
            self.assertFalse(state.visible)
            state.feed(b'\x1b[39;1Hprompt\x1b[39;7H')
            self.assertFalse(state.submitted)
            self.assertTrue(state.visible)

    def test_later_submission_cancels_pending_reset(self):
        for state in self.states():
            state.note_input(b'/clear\r')
            state.note_input(b'hello\r')
            state.feed(b'\x1b[39;1Hprompt\x1b[39;7H')
            self.assertTrue(state.submitted)
            self.assertFalse(state.visible)


if __name__ == '__main__':
    unittest.main()
