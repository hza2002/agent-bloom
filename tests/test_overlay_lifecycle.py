"""Decoration authority ends with its surface or trustworthy observation."""
import unittest
from unittest.mock import patch

from agent_theme.themes import huawei_bloom as intro
from agent_theme.themes import get_theme
from agent_theme import art, overlay
from agent_theme.animation import make_animated_overlay


HOME = b'\x1b[?1049h\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H'
REPAINT = b'\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H'


class OverlayLifecycleTests(unittest.TestCase):
    def test_tab_changes_require_hard_reset(self):
        for control in (b'\x1bH', b'\x1b[g', b'\x1b[0g', b'\x1b[3g',
                        b'\x1b[W', b'\x1b[?5W', b'\x1b[I', b'\x1b[Z'):
            with self.subTest(control=control):
                state = self.home()
                state.feed(control)
                self.assertIn('tab-stops', state.unsafe_modes)
                for repaint in (REPAINT, b'\x1b[?1049l' + HOME):
                    self.assertEqual(state.feed(repaint), repaint)
                    self.assertFalse(state.visible)
                state.resize(81, 40)
                self.assertEqual(state.feed(REPAINT), REPAINT)
                state.feed(b'\x1bc' + HOME)
                self.assertFalse(state.unsafe_modes)
                self.assertTrue(state.visible)

    def home(self, animated=False):
        cls = (make_animated_overlay(overlay.ClaudeOverlay, intro.Bloom)
               if animated else overlay.ClaudeOverlay)
        state = cls(81, 40, get_theme().brands['claude'])
        with patch('time.monotonic', return_value=100.0):
            state.feed(HOME)
            state.tick()
        self.assertTrue(state.visible, 'exercise an actually decorated surface')
        return state

    def quarantine(self, state):
        state.feed(b'\x1b[40;1H1')
        state.feed('\ufe0f'.encode())
        self.assertTrue(state.quarantine)

    def test_quarantine_observes_surface_exit_without_erasing_main_screen(self):
        for ending in (b'\x1b[H', b''):
            with self.subTest(ending=ending):
                state = self.home()
                self.quarantine(state)
                raw = b'\x1b[?1049l' + ending
                self.assertEqual(state.feed(raw) + state.finish(), raw)
                self.assertFalse(state.alt)
                self.assertFalse(state.visible)

    def test_quarantine_tracks_modes_before_any_cursor_boundary(self):
        for control in (b'\x1b[?6h', b'\x1b[?7l', b'\x1b[?69h',
                        b'\x1b[4h', b'\x1b7', b'\x1b[2;20r'):
            with self.subTest(control=control):
                state = self.home()
                self.quarantine(state)
                raw = control + REPAINT
                self.assertEqual(state.feed(raw), raw)
                self.assertTrue(state.unsafe_modes)
                self.assertTrue(state.quarantine)
                self.assertFalse(state.visible)

    def test_unknown_width_never_authorizes_later_cleanup(self):
        state = self.home()
        self.quarantine(state)
        # These cells/cursor are no longer modelled reliably. Even a later
        # cursor position cannot prove that previously blank rows stayed blank.
        raw = b'\n' * 12 + b'APPLICATION TEXT\x1b[H'
        self.assertEqual(state.feed(raw) + state.finish(), raw)

    def test_unmodelled_edit_releases_ownership_even_at_an_open_text_boundary(self):
        for edit in (b'\x1b#8', b'\x1b[5;1;8;80$z', b'\x1b[S'):
            with self.subTest(edit=edit):
                state = self.home()
                state.feed(b'\x1b[40;1HX')
                self.assertTrue(state.visible)
                raw = edit + b'\x1b[H'
                self.assertEqual(state.feed(raw) + state.finish(), raw)
                self.assertFalse(state.visible)

    def test_partial_clear_cannot_prove_a_fresh_quarantined_surface(self):
        state = self.home()
        state.feed(b'\x1b[H')
        state.feed('😀'.encode())
        state.feed(b'\x1b[J\x1b[H')
        self.assertTrue(state.quarantine)
        state.feed(REPAINT)
        self.assertFalse(state.quarantine)

    def test_alt_entry_requires_an_actual_transition_that_clears(self):
        for mode in (47, 1047, 1049):
            with self.subTest(mode=mode):
                state = self.home()
                self.quarantine(state)
                enter = b'\x1b[?%dh' % mode
                raw = enter + b'\x1b[H'
                self.assertEqual(state.feed(raw), raw)
                self.assertTrue(state.quarantine, 'repeated entry never proves clear')
                state.feed(b'\x1b[?%dl' % mode + raw)
                self.assertEqual(state.quarantine, mode != 1049)
                state.feed(REPAINT)
                self.assertFalse(state.quarantine)

    def test_overflow_is_terminal_even_after_quarantine_or_resize(self):
        for quarantine in (False, True):
            for opener in (b'\x1b]2;', b'\x1bP'):
                with self.subTest(quarantine=quarantine, opener=opener):
                    state = self.home()
                    if quarantine:
                        self.quarantine(state)
                    raw = opener + b'X' * (overlay.MAX_CARRY + 1)
                    self.assertTrue(state.feed(raw).endswith(raw))
                    self.assertEqual(state.feed(REPAINT), REPAINT)
                    state.resize(81, 40)
                    self.assertEqual(state.feed(b'\x1bc' + HOME), b'\x1bc' + HOME)
                    self.assertEqual(state.tick() + state.finish(), b'')
                    self.assertFalse(state.visible)

    def test_new_surface_requires_a_new_band_even_during_intro(self):
        for change in (b'\x1b[?1049l\x1b[?1049h\x1b[2J\x1b[H',
                       b'\x1b[2J\x1b[H'):
            with self.subTest(change=change):
                state = self.home(animated=True)
                state.feed(change)
                with patch('time.monotonic', return_value=100.5):
                    self.assertIsNone(state.next_timeout())
                    self.assertEqual(state.tick(), b'')
                self.assertFalse(state.visible)
                # A new valid layout can still resume the one-shot timeline.
                state.feed(REPAINT)
                with patch('time.monotonic', return_value=100.6):
                    self.assertTrue(state.tick())
                self.assertTrue(state.visible)
