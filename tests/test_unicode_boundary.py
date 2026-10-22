"""Decoration cannot split application text across PTY read boundaries."""
import json
import re
from pathlib import Path
import unittest
from unittest.mock import patch

from agent_theme import art, intro, overlay
from agent_theme.animation import make_animated_overlay
from tools import terminal_trace


class UnicodeBoundaryTests(unittest.TestCase):
    def home(self):
        state = overlay.ClaudeOverlay(81, 40, art.BRANDS['claude'])
        state.feed(b'\x1b[?1049h\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H')
        self.assertTrue(state.visible)
        return state

    def test_retire_before_text_and_wait_for_explicit_position(self):
        state = self.home()
        output = state.feed(b'\x1b[2;1H1')
        self.assertIn(b'\x1b[2K', output)
        # Only the row the text touched is retired; distant art stays.
        self.assertNotIn(1, state.visible)
        self.assertTrue(state.visible)
        self.assertTrue(state.text_tail)
        self.assertEqual(state.feed(b'\x1b[0m\x1b[?2026h\x1b[?2026l'),
                         b'\x1b[0m\x1b[?2026h\x1b[?2026l')
        self.assertEqual(state.tick(), b'')
        state.feed(b'\x1b[40;1H')
        self.assertFalse(state.text_tail)
        # An explicit position does not itself make dirty content a home;
        # the positive startup fixture above proves decoration is available.

    def test_split_modifier_is_forwarded_without_insertion(self):
        for text in ('❤️', '1️⃣', '👨‍👩‍👧‍👦', '🇨🇳'):
            with self.subTest(text=text):
                state = self.home()
                state.feed(b'\x1b[10;80H')
                raw = text.encode()
                output = b''.join(state.feed(raw[i:i + 1]) for i in range(len(raw)))
                self.assertTrue(output.endswith(raw))
                self.assertTrue(state.passthrough)
                # Retire only after an explicit cursor boundary; the unsupported
                # run may still be an open grapheme.
                state.feed(b'\x1b[40;1H')
                self.assertFalse(state.visible)
                self.assertFalse(state.known)
                self.assertEqual(state.finish(), b'')

    def test_plain_cjk_and_box_drawing_keep_known_occupancy(self):
        state = self.home()
        state.feed('界─│'.encode())
        self.assertTrue(state.known)
        self.assertTrue(state.text_tail)

    def test_finish_flushes_incomplete_utf8_without_cleanup(self):
        state = self.home()
        state.feed(b'\x1b[10;1HX')
        self.assertEqual(state.feed(b'\xe2\x9d'), b'')
        self.assertEqual(state.finish(), b'\xe2\x9d')

    def test_real_startup_fixtures_keep_intro_animation(self):
        fixtures = Path(__file__).parent / 'fixtures' / 'terminal'
        for app, name, base in (
                ('claude', 'claude-2.1.304.json', overlay.ClaudeOverlay),
                ('codex', 'codex-0.163.0.json', overlay.CodexOverlay)):
            trace = json.loads((fixtures / name).read_text())
            for chunk in (1, 4096):
                with self.subTest(app=app, chunk=chunk):
                    state = make_animated_overlay(base, intro)(*trace['size'], art.BRANDS[app])
                    data = terminal_trace.decode(trace['events'][0])
                    with patch('time.monotonic', return_value=100.0):
                        for start in range(0, len(data), chunk):
                            state.feed(data[start:start + chunk])
                        state.tick()
                    self.assertTrue(state.known)
                    self.assertFalse(state.text_tail)
                    self.assertTrue(state.visible)
                    with patch('time.monotonic', return_value=100.5):
                        self.assertTrue(state.tick())
                        self.assertIsNotNone(state.next_timeout())

    def test_split_final_position_restores_static_home(self):
        home = b'\x1b[?1049h\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT'
        position = b'\x1b[40;1H'
        for chunk in (1, len(position)):
            with self.subTest(chunk=chunk):
                state = overlay.ClaudeOverlay(81, 40, art.BRANDS['claude'])
                state.feed(home)
                self.assertFalse(state.visible)
                for start in range(0, len(position), chunk):
                    state.feed(position[start:start + chunk])
                self.assertTrue(state.visible)
                self.assertFalse(state.text_tail)

    def test_animation_ticks_cannot_split_text_cluster(self):
        state = make_animated_overlay(overlay.ClaudeOverlay, intro)(
            81, 40, art.BRANDS['claude'])
        state.feed(b'\x1b[?1049h\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H')
        with patch('time.monotonic', return_value=100.0):
            state.tick()
        self.assertTrue(state.visible)
        state.feed(b'\x1b[10;80H')
        raw = '1️⃣X'.encode()
        output = bytearray()
        for i, byte in enumerate(raw):
            output.extend(state.feed(bytes([byte])))
            with patch('time.monotonic', return_value=101.0 + i):
                self.assertEqual(state.tick(), b'')
                self.assertIsNone(state.next_timeout())
        self.assertTrue(output.endswith(raw))
        self.assertTrue(state.passthrough)
        state.feed(b'\x1b[40;1H')
        self.assertFalse(state.visible)

    def test_unsupported_width_quarantine_recovers_after_clear_and_cursor(self):
        state = overlay.ClaudeOverlay(81, 40, art.BRANDS['claude'])
        state.alt = True
        state.entered_alt = True
        state.known = True
        state.feed('😀'.encode())
        self.assertTrue(state.quarantine)
        self.assertTrue(state.passthrough)
        state.feed(b'\x1b[2J')
        self.assertTrue(state.quarantine)
        self.assertFalse(state.known)
        state.feed(b'\x1b[5;10H')
        self.assertFalse(state.quarantine)
        self.assertTrue(state.known)
        self.assertFalse(state.passthrough)

    def test_relative_cursor_does_not_recover_quarantine(self):
        state = overlay.ClaudeOverlay(81, 40, art.BRANDS['claude'])
        state.alt = True
        state.entered_alt = True
        state.known = True
        state.feed('😀'.encode())
        state.feed(b'\x1b[2J\x1b[3B')
        self.assertTrue(state.quarantine)
        self.assertFalse(state.known)

    def test_text_before_cursor_requires_another_clear(self):
        state = overlay.ClaudeOverlay(81, 40, art.BRANDS['claude'])
        state.alt = True
        state.entered_alt = True
        state.known = True
        state.feed('😀'.encode())
        state.feed(b'\x1b[2JX')
        state.feed(b'\x1b[10;1H')
        self.assertTrue(state.quarantine)
        state.feed(b'\x1b[2J\x1b[10;1H')
        self.assertFalse(state.quarantine)
        self.assertTrue(state.known)

    def test_erase_all_never_clears_an_app_owned_row(self):
        state = overlay.ClaudeOverlay(81, 40, art.BRANDS['claude'])
        state.feed(b'\x1b[?1049h\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H')
        self.assertTrue(state.visible)
        owned = min(state.visible)
        other = max(state.visible)
        state.count[owned] = 1
        output = state._erase_all()
        self.assertNotIn(b'\x1b[%d;1H\x1b[2K' % (owned + 1), output)
        self.assertNotIn(owned, state.visible)
        if other != owned:
            self.assertIn(b'\x1b[%d;1H\x1b[2K' % (other + 1), output)

    def test_unsafe_mode_blocks_quarantine_recovery(self):
        state = overlay.ClaudeOverlay(81, 40, art.BRANDS['claude'])
        state.alt = True
        state.entered_alt = True
        state.known = True
        state.feed('😀'.encode())
        state.feed(b'\x1b[2J\x1b[?6h\x1b[5;10H')
        self.assertTrue(state.quarantine)
        state.feed(b'\x1b[?6l\x1b[6;10H')
        self.assertFalse(state.quarantine)
        self.assertTrue(state.known)

    def test_unsupported_width_recovers_after_a_repaint(self):
        for chunks in (1, 4096):
            with self.subTest(chunks=chunks):
                state = self.home()
                state.feed(b'\x1b[10;80H')
                raw = '❤️X'.encode() + b'\x1b[2J\x1b[B\x1b[DZ'
                output = b''.join(state.feed(raw[i:i + chunks])
                                  for i in range(0, len(raw), chunks))
                # The retirement erase is an insertion; removing it recovers
                # the application stream byte for byte.
                insertions = re.compile(rb'\x1b7.*?\x1b8', re.DOTALL)
                self.assertEqual(insertions.sub(b'', output), raw)
                self.assertTrue(state.passthrough)
                self.assertTrue(state.quarantine)
                self.assertFalse(state.known)
                repaint = b'\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H'
                repainted = state.feed(repaint)
                self.assertTrue(repainted.startswith(repaint))
                self.assertFalse(state.quarantine)
                self.assertFalse(state.passthrough)
                self.assertTrue(state.known)
                self.assertTrue(state.visible)

    def test_unsupported_text_preserves_following_incomplete_utf8_tail(self):
        state = self.home()
        state.feed(b'\x1b[10;1H')
        raw = '❤️'.encode() + b'\xe2\x9d'
        output = state.feed(raw)
        self.assertTrue(output.endswith('❤️'.encode()))
        self.assertTrue(state.passthrough)
        self.assertTrue(state.quarantine)
        self.assertEqual(state.carry, b'\xe2\x9d')
        completed = state.feed(b'\xa4')
        self.assertTrue(completed.endswith(b'\xe2\x9d\xa4'))
        self.assertEqual(state.carry, b'')
        self.assertEqual(state.finish(), b'')
