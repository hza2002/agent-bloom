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

    def test_unsupported_unicode_never_rearms_after_clear(self):
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
                self.assertFalse(state.known)
                repaint = b'\x1b[2J\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H'
                self.assertEqual(state.feed(repaint), repaint)
                self.assertFalse(state.visible)

    def test_bypass_flushes_following_incomplete_utf8_tail(self):
        state = self.home()
        state.feed(b'\x1b[10;1H')
        raw = '❤️'.encode() + b'\xe2\x9d'
        output = state.feed(raw)
        self.assertTrue(output.endswith(raw))
        self.assertTrue(state.passthrough)
        self.assertFalse(state.retire_all)
        self.assertEqual(state.carry, b'')
        self.assertEqual(state.feed(b'\xa4'), b'\xa4')
        self.assertEqual(state.finish(), b'')
