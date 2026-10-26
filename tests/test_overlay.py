import os
import sys
import time
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme.themes import huawei_bloom as intro
from agent_theme.themes import get_theme
from agent_theme import art, overlay  # noqa: E402
from agent_theme.animation import make_animated_overlay  # noqa: E402


class InputStateTests(unittest.TestCase):
    def make(self, cls=overlay.ClaudeOverlay):
        ov = cls(120, 32, get_theme().brands['claude'], in_alt=True, reveal=False)
        ov.alt = True
        ov.entered_alt = True
        return ov

    def test_empty_enter_does_not_submit(self):
        ov = self.make()
        ov.note_input(b'\r')
        self.assertFalse(ov.submitted)

    def test_empty_enter_after_terminal_reports_does_not_submit(self):
        ov = self.make()
        ov.note_input(b'\x1bP>|tmux 3.8\x1b\\\x1b[?1;2;4c')
        ov.note_input(b'\r')
        self.assertFalse(ov.submitted)

    def test_prompt_submission_survives_screen_clear(self):
        ov = self.make()
        ov.note_input(b'hello\r')
        self.assertTrue(ov.submitted)
        ov._new_screen()
        self.assertTrue(ov.submitted)

    def test_clear_marks_a_fresh_screen(self):
        ov = self.make()
        ov.note_input(b'/clear\r')
        self.assertTrue(ov.submitted)
        self.assertTrue(ov.is_fresh())
        ov._new_screen()
        self.assertTrue(ov.submitted)
        self.assertTrue(ov.is_fresh())

    def test_codex_tracks_input_too(self):
        ov = self.make(overlay.CodexOverlay)
        ov.note_input(b'hello\r')
        self.assertTrue(ov.submitted)


class LayoutTests(unittest.TestCase):
    def test_clear_and_resize_rearm_a_disabled_overlay(self):
        ov = overlay.ClaudeOverlay(120, 32, get_theme().brands['claude'],
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
        ov = overlay.ClaudeOverlay(300, 40, get_theme().brands['claude'],
                                   in_alt=True, reveal=False)
        ov._clear_rows(0, 1, filled=True)
        self.assertEqual(len(ov.grid[0]), 300)
        self.assertEqual(ov.count[0], 300)

    def test_notice_above_the_art_keeps_the_anchor(self):
        cls = make_animated_overlay(overlay.CodexOverlay, intro.Bloom)
        ov = cls(91, 55, get_theme().brands['codex'], in_alt=True, reveal=True,
                 play_intro=True)
        ov.known = True
        for row in (1, 2, 3, 49, 50, 51, 52, 53, 54):
            ov.count[row] = 1
        ov._frame_end()
        self.assertIsNotNone(ov.anchor)
        top = ov.anchor[1]
        ov.count[4] = 1  # a notice above the art, not touching it
        ov._frame_end()
        self.assertEqual(ov.anchor[1], top)

    def test_notice_touching_the_art_reanchors(self):
        cls = make_animated_overlay(overlay.CodexOverlay, intro.Bloom)
        ov = cls(91, 55, get_theme().brands['codex'], in_alt=True, reveal=True,
                 play_intro=True)
        ov.known = True
        for row in (1, 2, 3, 49, 50, 51, 52, 53, 54):
            ov.count[row] = 1
        ov._frame_end()
        old_top = ov.anchor[1]
        ov.count[min(ov.rows_used)] = 1
        ov._frame_end()
        self.assertIsNotNone(ov.anchor)
        self.assertGreater(ov.anchor[1], old_top)

    def test_intro_reanchors_below_a_late_notice(self):
        cls = make_animated_overlay(overlay.CodexOverlay, intro.Bloom)
        ov = cls(91, 55, get_theme().brands['codex'], in_alt=True, reveal=True,
                 play_intro=True)
        ov.known = True
        ov.anchor = (None, 5, (91, 55))
        for row in (1, 2, 3, 5, 49, 50, 51, 52, 53, 54):
            ov.count[row] = 1
        ov._frame_end()
        self.assertIsNotNone(ov.anchor)
        self.assertGreater(ov.anchor[1], 5)
        self.assertTrue(ov.intro_owns_home)


class WarningScenarioTests(unittest.TestCase):
    WARNING = ('⚠ Heads up, you have less than 25% of your weekly limit '
               'left. Run /status for a breakdown.')

    def state(self):
        cls = make_animated_overlay(overlay.CodexOverlay, intro.Bloom)
        ov = cls(91, 55, get_theme().brands['codex'], in_alt=True, reveal=True,
                 play_intro=True)
        ov.alt = True
        ov.entered_alt = True
        ov.known = True
        for row in (1, 2, 3, 49, 50, 51, 52, 53, 54):
            ov.count[row] = 1
        ov._frame_end()
        with mock.patch('time.monotonic', return_value=100.0):
            ov.tick()
        return ov

    def test_warning_above_the_art_keeps_the_intro(self):
        ov = self.state()
        top = ov.anchor[1]
        ov.count[4] = 1
        ov.feed(('\x1b[5;1H%s\x1b[50;3H' % self.WARNING).encode())
        self.assertEqual(ov.anchor[1], top)
        with mock.patch('time.monotonic', return_value=100.5):
            ov.tick()
        self.assertTrue(ov.visible)
        self.assertFalse(ov.anim_done)

    def test_warning_on_the_art_reanchors_the_intro(self):
        ov = self.state()
        old_top = ov.anchor[1]
        ov.feed(('\x1b[6;1H%s\x1b[50;3H' % self.WARNING).encode())
        self.assertIsNotNone(ov.anchor)
        self.assertGreater(ov.anchor[1], old_top)
        with mock.patch('time.monotonic', return_value=100.5):
            ov.tick()
        self.assertTrue(ov.visible)
        self.assertFalse(ov.anim_done)

    def test_vs16_warning_quarantines_and_recovers(self):
        ov = self.state()
        ov.feed('⚠️ Heads up'.encode())
        self.assertTrue(ov.quarantine)
        self.assertTrue(ov.passthrough)
        ov.feed(b'\x1b[2J\x1b[10;1H')
        self.assertFalse(ov.quarantine)
        self.assertFalse(ov.passthrough)
        self.assertTrue(ov.known)


class TerminalBoundaryTests(unittest.TestCase):
    def test_wide_wrap_erases_each_touched_row_before_app_text(self):
        for cls, key in ((overlay.ClaudeOverlay, 'claude'),
                         (overlay.CodexOverlay, 'codex')):
            with self.subTest(app=key):
                ov = cls(81, 40, get_theme().brands[key])
                ov.feed(b'\x1b[?1049h\x1b[2J\x1b[1;1Hheader'
                        b'\x1b[39;1Hprompt\x1b[39;7H')
                self.assertIn(5, ov.visible)
                raw = ('界' * 81).encode()
                out = ov.feed(b'\x1b[4;1H' + raw)
                erase = b'\x1b[6;1H\x1b[2K'
                self.assertIn(erase, out)
                self.assertLess(out.index(erase), out.index(raw))
                self.assertEqual(ov.count[3:6], [80, 80, 2])

    def test_wide_wrap_at_bottom_invalidates_screen(self):
        ov = self.make()
        ov.feed(b'\x1b[54;1H' + ('界' * 111).encode())
        self.assertFalse(ov.known)

    def test_alignment_test_erases_before_forwarding_and_waits_for_clear(self):
        ov = self.make()
        ov.feed(b'\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
        self.assertTrue(ov.visible)
        out = ov.feed(b'\x1b#8')
        self.assertTrue(out.endswith(b'\x1b#8'))
        self.assertIn(b'\x1b[2K', out)
        self.assertFalse(ov.known)
        self.assertEqual(ov.tick(), b'')
        ov.feed(b'\x1b[2J\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
        self.assertTrue(ov.visible)

    def test_persistent_terminal_controls_isolate_until_hard_reset(self):
        for seq in (b'\x1b[132$|', b'\x1b[1"q', b'\x1b#6'):
            with self.subTest(seq=seq):
                ov = self.make()
                ov.feed(seq + b'\x1b[2J')
                self.assertFalse(ov.known)
                ov.feed(b'\x1bc\x1b[?1049h\x1b[2J')
                self.assertTrue(ov.known)

    def test_rectangle_edits_only_invalidate_occupancy(self):
        for seq in (b'\x1b[65;5;1;8;80$x', b'\x1b[5;1;8;80$z',
                    b'\x1b[5;1;8;80$r'):
            with self.subTest(seq=seq):
                ov = self.make()
                ov.feed(b'\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
                self.assertTrue(ov.visible)
                out = ov.feed(seq)
                self.assertTrue(out.endswith(seq))
                self.assertIn(b'\x1b[2K', out[:-len(seq)])
                self.assertFalse(ov.known)
                self.assertFalse(ov.unsafe_modes)
                ov.feed(b'\x1b[2J\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
                self.assertTrue(ov.known)
                self.assertTrue(ov.visible)

    def test_cursor_style_is_safe_to_ignore(self):
        ov = self.make()
        self.assertEqual(ov.feed(b'\x1b[2 q'), b'\x1b[2 q')
        self.assertTrue(ov.known)

    def make(self):
        ov = overlay.Overlay(111, 55, get_theme().brands['claude'])
        ov.feed(b'\x1b[?1049h\x1b[2J')
        return ov

    def test_persistent_modes_survive_clear_resize_and_alt_switch(self):
        for mode in (b'\x1b[5;50r\x1b[?6h', b'\x1b[?7l', b'\x1b[4h'):
            with self.subTest(mode=mode):
                ov = self.make()
                ov.feed(mode)
                ov.resize(111, 55)
                out = ov.feed(b'\x1b[?1049l\x1b[?1049h\x1b[2J'
                              b'\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
                self.assertFalse(ov.known)
                self.assertFalse(ov.visible)
                self.assertNotIn(b'\x1b7', out)

    def test_explicit_mode_restore_then_clear_allows_home(self):
        ov = self.make()
        ov.feed(b'\x1b[5;50r\x1b[?6h\x1b[?7l\x1b[4h')
        ov.feed(b'\x1b[r\x1b[?6l\x1b[?7h\x1b[4l')
        out = ov.feed(b'\x1b[2J\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
        self.assertTrue(ov.known)
        self.assertTrue(ov.visible)
        self.assertIn(b'\x1b7', out)

    def test_origin_mode_restore_homes_the_cursor_before_ed2(self):
        ov = self.make()
        ov.feed(b'\x1b[20;20H\x1b[?6h\x1b[?6l\x1b[2JH')
        self.assertTrue(ov.known)
        self.assertEqual((ov.cy, ov.cx), (0, 1))
        self.assertEqual(ov.count[0], 1)

    def test_clear_cannot_release_an_app_owned_cursor_save_slot(self):
        ov = self.make()
        ov.feed(b'\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
        self.assertTrue(ov.visible)
        ov.feed(b'\x1b7')
        out = ov.feed(b'\x1b[2J\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
        self.assertFalse(ov.known)
        self.assertFalse(ov.visible)
        self.assertNotIn(b'\x1b7', out)

    def test_oversized_unclosed_strings_release_original_bytes(self):
        for prefix in (b'\x1b]', b'\x1bP', b'\x1b_', b'\x1b^', b'\x1bX'):
            with self.subTest(prefix=prefix):
                ov = self.make()
                first = prefix + b'x' * 4096
                self.assertEqual(ov.feed(first), b'')
                tail = b'x' * 65536
                self.assertEqual(ov.feed(tail), first + tail)
                self.assertEqual(ov.carry, b'')
                # Even a later clear must not insert ANSI into the open string.
                later = b'\x1b[2J\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H'
                self.assertEqual(ov.feed(later), later)

    def test_split_control_string_still_parses_normally(self):
        ov = self.make()
        self.assertEqual(ov.feed(b'\x1b]0;title'), b'')
        self.assertEqual(ov.feed(b'\x07'), b'\x1b]0;title\x07')
        out = ov.feed(b'\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
        self.assertTrue(ov.visible)
        self.assertIn(b'\x1b7', out)

    def test_finish_releases_even_a_short_incomplete_sequence(self):
        ov = self.make()
        self.assertEqual(ov.feed(b'\x1b]0;unfinished'), b'')
        self.assertEqual(ov.finish(), b'\x1b]0;unfinished')
        self.assertEqual(ov.carry, b'')
        self.assertEqual(ov.feed(b'raw'), b'raw')

    def test_overflow_erases_art_before_forwarding_the_open_string(self):
        ov = self.make()
        ov.feed(b'\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
        self.assertTrue(ov.visible)
        raw = b'\x1b]' + b'x' * 65536
        out = ov.feed(raw)
        self.assertTrue(out.endswith(raw))
        erase = out[:-len(raw)]
        self.assertIn(b'\x1b[2K', erase)
        self.assertFalse(ov.visible)


class AnimationStateTests(unittest.TestCase):
    def test_no_ambient_keeps_intro_and_home_without_idle_work(self):
        for app, base in (('claude', overlay.ClaudeOverlay),
                          ('codex', overlay.CodexOverlay)):
            with self.subTest(app=app):
                visible = mock.Mock(return_value=True)
                cls = make_animated_overlay(base, intro.Bloom)
                ov = cls(120, 40, get_theme().brands[app], reveal=True,
                         ambient=False, visibility=visible)
                home = (b'\x1b[?1049h\x1b[2J\x1b[HHEADER'
                        b'\x1b[39;1HPROMPT\x1b[40;1H')
                with mock.patch('time.monotonic', return_value=100.0):
                    ov.feed(home)
                    self.assertTrue(ov.tick())
                    self.assertFalse(ov.anim_done)
                with mock.patch('time.monotonic', return_value=110.0):
                    self.assertTrue(ov.tick())
                    self.assertTrue(ov.anim_done)
                    self.assertTrue(ov.visible)
                with mock.patch('time.monotonic', return_value=112.0):
                    ov.tick()  # Finish the opening small-text fade.
                    self.assertIsNone(ov.next_timeout())
                with mock.patch('time.monotonic', return_value=130.0):
                    self.assertEqual(ov.tick(), b'')
                    self.assertIsNone(ov.next_timeout())
                    ov.note_input(b'hello\r')
                    ov.tick()
                    ov.note_input(b'/clear\r')
                    ov.feed(home)
                    ov.tick()
                with mock.patch('time.monotonic', return_value=140.0):
                    ov.tick()  # Finish the restored home's small-text fade.
                    self.assertTrue(ov.visible)
                    self.assertIsNone(ov.next_timeout())
                    self.assertEqual(ov.tick(), b'')
                visible.assert_not_called()

    def test_mode_queries_do_not_stop_the_intro(self):
        for query in (b'\x1b[?2026$p', b'\x1b[4$p'):
            with self.subTest(query=query):
                cls = make_animated_overlay(overlay.ClaudeOverlay, intro.Bloom)
                ov = cls(93, 55, get_theme().brands['claude'], reveal=True)
                ov.feed(b'\x1b[?1049h\x1b[2J'
                        b'\x1b[1;1HHEADER\x1b[49;1HPROMPT\x1b[49;7H')
                with mock.patch('time.monotonic', return_value=100.0):
                    ov.tick()
                with mock.patch('time.monotonic', return_value=100.5):
                    self.assertTrue(ov.tick())
                self.assertEqual(ov.feed(query), query)
                self.assertTrue(ov.known)
                self.assertFalse(ov.unsafe_modes)
                with mock.patch('time.monotonic', return_value=100.6):
                    self.assertIsNotNone(ov.next_timeout())
                    self.assertTrue(ov.tick())

    def make(self, play_intro=False):
        cls = make_animated_overlay(overlay.ClaudeOverlay, intro.Bloom)
        ov = cls(120, 32, get_theme().brands['claude'], in_alt=True,
                 reveal=play_intro, pal=art.palette(), strict=False,
                 play_intro=play_intro, visibility=lambda: True)
        ov.alt = True
        ov.entered_alt = True
        ov.known = True
        # A normal home: header rows and a bottom prompt leave a blank band.
        for row in (1, 2, 3, 28, 29, 30, 31):
            ov.count[row] = 1
        return ov

    def test_no_drawable_rows_advance_deadline_and_finish_intro(self):
        ov = self.make(play_intro=True)
        with mock.patch('time.monotonic', return_value=100.0):
            self.assertTrue(ov.tick())
        ov.count = [1] * ov.rows
        with mock.patch('time.monotonic', return_value=101.0):
            self.assertEqual(ov.tick(), b'')
            self.assertGreater(ov.next_timeout(), 0)
        with mock.patch('time.monotonic', return_value=104.0):
            ov.tick()
            self.assertTrue(ov.anim_done)
            self.assertIsNone(ov.next_timeout())

    def test_alt_screen_switch_invalidates_settled_cells(self):
        ov = self.make(play_intro=True)
        self.assertTrue(ov.tick())
        scene = ov.anim_scene
        cells = scene.frame(1.95)
        self.assertTrue(scene.ansi(cells))
        self.assertEqual(scene.ansi(cells), '')
        ov.feed(b'\x1b[?1049l\x1b[?1049h\x1b[2J')
        self.assertTrue(scene.ansi(cells))

    def test_unknown_surface_has_no_timer_or_paint(self):
        ov = self.make(play_intro=True)
        self.assertTrue(ov.tick())
        ov.feed(b'\x1b[5;28r')
        self.assertFalse(ov.known)
        self.assertEqual(ov.tick(), b'')
        self.assertIsNone(ov.next_timeout())

    def test_resize_waits_for_a_known_screen(self):
        ov = self.make(play_intro=True)
        self.assertTrue(ov.tick())
        ov.resize(111, 55)
        self.assertFalse(ov.known)
        self.assertEqual(ov.tick(), b'')
        self.assertIsNone(ov.next_timeout())

    def test_fade_obeys_deadline_when_app_output_wakes_loop(self):
        ov = self.make()
        ov.want_reveal = True
        ov.reveal_from = 100.0
        lock = art.choose(get_theme().brands['claude'], 120, 32)
        ov.anchor = (lock, 2, (120, 32))
        ov.visible = {2 + lock.slogan_top}
        ov.dynamic_rows = set(ov.visible)
        with mock.patch('time.monotonic', return_value=100.1):
            self.assertTrue(ov.tick())
            due = ov.next_frame
            self.assertEqual(ov.tick(), b'')
            self.assertEqual(ov.next_frame, due)

    def test_ambient_restores_settled_frame_after_missed_deadlines(self):
        ov = self.make()
        for row in (1, 2, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertTrue(ov._frame_end())
        ov.ambient_next = 100.0
        with mock.patch('time.monotonic', return_value=100.0):
            ov.tick()
        with mock.patch('time.monotonic', return_value=100.8):
            self.assertTrue(ov.tick())
        # A slow terminal can skip the entire second half of the sweep.
        with mock.patch('time.monotonic', return_value=102.1):
            self.assertTrue(ov.tick())
        scene = ov.anim_scene
        self.assertEqual(scene.ansi(scene.frame(2.95), ov._rows()), '')

    def test_ambient_sheen_crosses_the_small_text(self):
        ov = self.make()
        for row in (1, 2, 3, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertTrue(ov._frame_end())
        base = ov._ambient_text(0.0)
        mid = ov._ambient_text(0.5)
        end = ov._ambient_text(1.0)
        self.assertTrue(base)
        self.assertNotEqual(mid, base)
        # The pass starts and ends on the settled palette: no stuck highlight.
        self.assertEqual(end, base)

    def test_ambient_sheen_skips_app_owned_text_rows(self):
        ov = self.make()
        for row in (1, 2, 3, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertTrue(ov._frame_end())
        lock, top, _ = ov.anchor
        row = top + lock.platform_top
        ov.count[row] = 1
        out = ov._ambient_text(0.5)
        self.assertNotIn(b'\x1b[%d;1H\x1b[2K' % (row + 1), out)

    def test_hidden_tmux_pane_skips_ambient_until_visible(self):
        ov = self.make()
        for row in (1, 2, 3, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertTrue(ov._frame_end())
        ov.visibility = lambda: False
        ov.ambient_next = 100.0
        with mock.patch('time.monotonic', return_value=100.0):
            self.assertEqual(ov.tick(), b'')
        self.assertIsNone(ov.ambient_start)
        self.assertEqual(ov.ambient_next, 108.0)
        self.assertTrue(ov.pane_hidden)
        # The next check is still scheduled; no 30 Hz spin while hidden.
        with mock.patch('time.monotonic', return_value=100.0):
            self.assertGreater(ov.next_timeout(), 7.0)
        ov.visibility = lambda: True
        with mock.patch('time.monotonic', return_value=108.0):
            self.assertTrue(ov.tick())
        self.assertEqual(ov.ambient_start, 108.0)
        self.assertFalse(ov.pane_hidden)

    def test_visibility_check_failure_keeps_the_ambient(self):
        ov = self.make()
        for row in (1, 2, 3, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertTrue(ov._frame_end())
        ov.visibility = lambda: (_ for _ in ()).throw(RuntimeError('no tmux'))
        ov.ambient_next = 100.0
        with mock.patch('time.monotonic', return_value=100.0):
            self.assertTrue(ov.tick())
        self.assertEqual(ov.ambient_start, 100.0)

    def test_pending_visibility_query_yields_to_transport(self):
        ov = self.make()
        for row in (1, 2, 3, 28, 29, 30, 31):
            ov.count[row] = 1
        self.assertTrue(ov._frame_end())
        ov.visibility = lambda: None
        ov.ambient_next = 100.0
        with mock.patch('time.monotonic', return_value=100.0):
            self.assertEqual(ov.tick(), b'')
            self.assertFalse(ov.pane_hidden)
            self.assertGreater(ov.next_timeout(), 0)
            self.assertLess(ov.next_timeout(), 0.1)
        ov.visibility = lambda: True
        with mock.patch('time.monotonic', return_value=100.1):
            self.assertTrue(ov.tick())

    def test_inline_session_has_no_frame_timer(self):
        ov = self.make(play_intro=True)
        ov.alt = False
        self.assertIsNone(ov.next_timeout())

    def test_app_output_does_not_render_extra_frames(self):
        ov = self.make(play_intro=True)
        self.assertTrue(ov.tick())
        due = time.monotonic() + 1.0
        ov.next_frame = due
        # A wake-up caused by app output before the next frame is due must not
        # repaint or move the deadline.
        self.assertEqual(ov.tick(), b'')
        self.assertEqual(ov.next_frame, due)
        self.assertAlmostEqual(ov.next_timeout(), 1.0, delta=0.1)

    def test_cell_cache_skips_unchanged_frames_until_art_is_erased(self):
        ov = self.make(play_intro=True)
        self.assertTrue(ov.tick())
        scene = ov.anim_scene
        row = min(ov.visible)
        cells = scene.frame(1.5)
        self.assertTrue(scene.ansi(cells))
        self.assertEqual(scene.ansi(cells), '')
        self.assertTrue(ov._erase([row]))
        self.assertEqual(scene.prev_cells, {})
        self.assertTrue(scene.ansi(cells))

    def test_home_repaint_invalidates_the_scene_cache(self):
        ov = self.make(play_intro=True)
        self.assertTrue(ov.tick())
        lock = art.choose(get_theme().brands['claude'], 120, 32)
        ov.anchor = (lock, 5, (120, 32))
        ov.visible = set()
        self.assertTrue(ov._paint([5 + lock.logo_top]))
        self.assertEqual(ov.anim_scene.prev_cells, {})

    def test_cell_cache_only_resends_the_changed_span(self):
        lock = art.choose(get_theme().brands['claude'], 111, 55)
        scene = intro.Bloom(111, 55, get_theme().dark, get_theme().brands['claude'], lock=lock, top=5)
        cells = scene.frame(2.3)
        scene.ansi(cells)
        row, col = max(cells, key=lambda key: key[1])
        changed = dict(cells)
        changed[(row, col)] = ('█', (1, 2, 3))
        out = scene.ansi(changed)
        self.assertIn('\x1b[%d;%dH' % (row + 1, col + 1), out)
        self.assertNotIn('\x1b[%d;%dH' % (row + 1, scene.x0 + 1), out)

    def test_no_intro_mode_starts_finished(self):
        ov = self.make()
        self.assertTrue(ov.anim_done)

    def test_both_brands_share_the_same_bloom_duration(self):
        for brand in get_theme().brands.values():
            lock = art.choose(brand, 120, 24)
            scene = intro.Bloom(120, 32, art.palette(), brand, lock=lock, top=4)
            self.assertEqual(scene.duration, 2.95)

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
        # A text-only fallback has no mark, so the Bloom cannot start.
        lock = art.Lockup(get_theme().brands['claude'], 0, 0, 120,
                          show_mark=False, show_word=False, show_small=True)
        ov.anchor = (lock, 5, (120, 32))
        ov.visible = {7}
        ov.ambient_next = 0.0
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

    def test_screen_clear_does_not_rearm_ambient(self):
        ov = self.make()
        ov.ambient_stopped = True
        ov._new_screen()
        self.assertTrue(ov.ambient_stopped)

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

    def test_unconfirmed_reset_does_not_rearm_ambient(self):
        ov = self.make()
        ov.submitted = True
        ov.ambient_stopped = True
        ov.fresh_pending = time.monotonic()
        ov.visible = set()
        ov.tick()
        self.assertTrue(ov.ambient_stopped)


if __name__ == '__main__':
    unittest.main()
