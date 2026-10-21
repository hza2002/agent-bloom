import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme import art, intro, overlay  # noqa: E402
from agent_theme.animation import make_animated_overlay  # noqa: E402


class InputStateTests(unittest.TestCase):
    def make(self, cls=overlay.ClaudeOverlay):
        ov = cls(120, 32, art.BRANDS['claude'], in_alt=True, reveal=False)
        ov.alt = True
        ov.entered_alt = True
        return ov

    def test_empty_enter_does_not_submit(self):
        ov = self.make()
        ov.note_input(b'\r')
        self.assertFalse(ov.submitted)

    def test_prompt_submits_and_new_screen_resets(self):
        ov = self.make()
        ov.note_input(b'hello\r')
        self.assertTrue(ov.submitted)
        ov._new_screen()
        self.assertFalse(ov.submitted)

    def test_clear_marks_a_fresh_screen(self):
        ov = self.make()
        ov.note_input(b'/clear\r')
        self.assertTrue(ov.submitted)
        self.assertTrue(ov.is_fresh())
        ov._new_screen()
        self.assertFalse(ov.submitted)
        self.assertFalse(ov.is_fresh())

    def test_codex_tracks_input_too(self):
        ov = self.make(overlay.CodexOverlay)
        ov.note_input(b'hello\r')
        self.assertTrue(ov.submitted)


class LayoutTests(unittest.TestCase):
    def test_claude_clear_layout_accepts_the_echo_row(self):
        ov = overlay.ClaudeOverlay(120, 32, art.BRANDS['claude'],
                                   in_alt=True, reveal=False)
        ov.alt = True
        ov.entered_alt = True
        ov.known = True
        ov.fresh_pending = time.monotonic()
        for row in (1, 2, 3, 6, 25, 26, 27, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertEqual(ov._layout(), (6, 25))
        self.assertFalse(ov.submitted)

    def test_clear_and_resize_rearm_a_disabled_overlay(self):
        ov = overlay.ClaudeOverlay(120, 32, art.BRANDS['claude'],
                                   in_alt=True, reveal=False)
        ov.alt = True
        ov.entered_alt = True
        ov.disabled = True
        ov._new_screen()
        self.assertFalse(ov.disabled)
        ov.disabled = True
        ov.resize(100, 30)
        self.assertFalse(ov.disabled)

    def test_filled_clear_tracks_wide_screens(self):
        ov = overlay.ClaudeOverlay(300, 40, art.BRANDS['claude'],
                                   in_alt=True, reveal=False)
        ov._clear_rows(0, 1, filled=True)
        self.assertEqual(len(ov.grid[0]), 300)
        self.assertEqual(ov.count[0], 300)

    def test_codex_help_list_belongs_to_the_top_block(self):
        ov = overlay.CodexOverlay(120, 32, art.BRANDS['codex'],
                                  in_alt=True, reveal=False)
        ov.known = True
        ov.help_row = 4
        for row in (1, 2, 4, 6, 7, 8, 9, 10, 28, 30, 31):
            ov.count[row] = 1
        self.assertEqual(ov._layout(), (10, 28))
        ov.submitted = True
        self.assertIsNone(ov._layout())


class AnimationStateTests(unittest.TestCase):
    def make(self, play_intro=False):
        cls = make_animated_overlay(overlay.ClaudeOverlay, intro)
        ov = cls(120, 32, art.BRANDS['claude'], in_alt=True,
                 reveal=play_intro, pal=art.palette(), strict=False,
                 play_intro=play_intro)
        ov.alt = True
        ov.entered_alt = True
        return ov

    def test_inline_session_has_no_frame_timer(self):
        ov = self.make(play_intro=True)
        ov.alt = False
        self.assertIsNone(ov.next_timeout())

    def test_no_intro_mode_starts_finished(self):
        ov = self.make()
        self.assertTrue(ov.anim_done)

    def test_both_brands_share_the_same_bloom_duration(self):
        for brand in art.BRANDS.values():
            self.assertEqual(intro.Bloom(120, 32, art.palette(), brand).duration, 2.95)

    def test_intro_does_not_flash_the_static_home(self):
        ov = self.make(play_intro=True)
        ov.known = True
        for row in (1, 2, 3, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertEqual(ov._frame_end(), b'')
        self.assertIsNotNone(ov.anchor)
        out = ov._finish(paint=True)
        self.assertIn(b'\x1b[?2026h', out)
        self.assertTrue(ov.visible)

    def test_finish_repaints_the_whole_home(self):
        ov = self.make(play_intro=True)
        ov.known = True
        for row in (1, 2, 3, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertEqual(ov._frame_end(), b'')
        ov.visible = {7}
        out = ov._finish(paint=True)
        self.assertIn(b'\x1b[8;1H\x1b[2K', out)
        self.assertTrue(ov.visible)

    def test_unavailable_scene_does_not_spin(self):
        ov = self.make()
        lock = art.choose(art.BRANDS['claude'], 120, 16)
        ov.anchor = (lock, 5, (120, 32))
        ov.visible = {7}
        ov.tick()
        self.assertTrue(ov.scene_failed)
        self.assertIsNone(ov.next_timeout())

    def test_animation_defers_during_sync_or_carry_or_disabled(self):
        ov = self.make()
        for attr in ('sync', 'carry', 'disabled'):
            with self.subTest(attr=attr):
                setattr(ov, attr, True)
                self.assertEqual(ov.tick(), b'')
                setattr(ov, attr, False)

    def test_new_screen_rearms_ambient(self):
        ov = self.make()
        ov.ambient_stopped = True
        ov._new_screen()
        self.assertFalse(ov.ambient_stopped)

    def test_submit_erases_art_even_after_stale_stop(self):
        ov = self.make()
        ov.ambient_stopped = True
        ov.visible = {7}
        ov.submitted = True
        out = ov.tick()
        self.assertIn(b'\x1b[8;1H\x1b[2K', out)
        self.assertNotIn(7, ov.visible)

    def test_submit_stops_ambient_timer(self):
        ov = self.make()
        ov.note_input(b'hello\r')
        self.assertIsNone(ov.next_timeout())
        ov.visible = {7}
        ov.tick()
        self.assertTrue(ov.ambient_stopped)

    def test_clear_rearms_ambient(self):
        ov = self.make()
        ov.submitted = True
        ov.ambient_stopped = True
        ov.fresh_pending = time.monotonic()
        ov.visible = set()
        ov.tick()
        self.assertFalse(ov.ambient_stopped)


if __name__ == '__main__':
    unittest.main()
