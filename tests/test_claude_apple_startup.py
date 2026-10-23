"""Our replacement badge must not quarantine Claude's own startup."""
import os
import unittest
from unittest.mock import patch

from agent_theme import art, overlay
from agent_theme.apps import PROFILES
from agent_theme.launcher import Launcher
from agent_theme.themes import get_theme


class ClaudeAppleStartupTests(unittest.TestCase):
    def tearDown(self):
        art.reset_glyphs()

    def test_renderer_block_glyphs_have_known_single_cell_width(self):
        for ch in art.OCTANT_TABLE:
            self.assertEqual(overlay.cwidth(ch), 1, hex(ord(ch)))
        state = overlay.ClaudeOverlay(91, 55, get_theme('apple').brands['claude'])
        raw = b'\x1b[?1049h\x1b[2J\x1b[2;1H' + '\U0001fb85'.encode() + b'\x1b[54;1HPROMPT\x1b[55;1H'
        state.feed(raw)
        self.assertFalse(state.quarantine)
        self.assertTrue(state.visible)
        state.feed(b'\x1b[3;1H' + '😀'.encode())
        self.assertTrue(state.quarantine)

    def test_replaced_claude_header_allows_both_intros(self):
        for mode in ('octant', 'quadrant'):
            with patch.dict(os.environ, AGENT_THEME_GLYPHS=mode):
                art.reset_glyphs()
                for animation in ('spectrum', 'constellation'):
                    profile = PROFILES['claude']
                    opts = dict(profile.defaults, theme='apple', animation=animation)
                    for chunk in (1, 4096):
                        with self.subTest(animation=animation, chunk=chunk):
                            launcher = Launcher(profile, 'claude', [], opts)
                            state = launcher._make_overlay(91, 55)
                            data = (profile.replace(profile.sample, opts)
                                    + b'\x1b[54;1HPROMPT\x1b[55;1H')
                            with patch('time.monotonic', return_value=100):
                                for start in range(0, len(data), chunk):
                                    state.feed(data[start:start+chunk])
                                state.tick()
                            self.assertFalse(state.quarantine)
                            self.assertIsNotNone(state.anim_scene)
                            with patch('time.monotonic', return_value=100.5):
                                self.assertTrue(state.tick())


if __name__ == '__main__':
    unittest.main()
