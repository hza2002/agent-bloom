import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme.themes import get_theme
from agent_theme.apps import PROFILES  # noqa: E402
from agent_theme.replacer import Replacer  # noqa: E402


NEW_CLAUDE = get_theme().brands['claude'].header.encode()

class ReplacerTests(unittest.TestCase):
    def setUp(self):
        self.profile = PROFILES['claude']
        self.opts = dict(self.profile.defaults)

    def test_split_header_sequence(self):
        header = (b'\x1b[12G\x1b[39m\x1b[49m\x1b[1mClaude Code'
                  b'\x1b[24G\x1b[22m')
        replacer = Replacer(self.profile, self.opts)
        out = b''
        cuts = (0, 5, 12, 18, 24, 31, len(header))
        for start, stop in zip(cuts, cuts[1:]):
            out += replacer.feed(header[start:stop])
        out += replacer.feed(b'', flush=True)
        self.assertIn(NEW_CLAUDE, out)
        self.assertNotIn(b'Claude Code', out)

    def test_compact_header_split_points(self):
        header = (b'\x1b[H\r\x1b[11C\x1b[1B\x1b[1mClaude Code'
                  b'\x1b[24G\x1b[22m')
        for cut in range(1, len(header)):
            with self.subTest(cut=cut):
                replacer = Replacer(self.profile, self.opts)
                out = replacer.feed(header[:cut])
                out += replacer.feed(header[cut:], flush=True)
                self.assertIn(NEW_CLAUDE, out)

    def test_every_header_split_point(self):
        header = (b'\x1b[12G\x1b[39m\x1b[49m\x1b[1mClaude Code'
                  b'\x1b[24G\x1b[22m')
        for cut in range(1, len(header)):
            with self.subTest(cut=cut):
                replacer = Replacer(self.profile, self.opts)
                out = replacer.feed(header[:cut])
                out += replacer.feed(header[cut:], flush=True)
                self.assertIn(NEW_CLAUDE, out)

    def test_plain_text_passes_through(self):
        replacer = Replacer(self.profile, self.opts)
        data = b'hello world\n'
        self.assertEqual(replacer.feed(data), data)

    def test_bold_transcript_is_not_a_header(self):
        replacer = Replacer(self.profile, self.opts)
        data = b'\x1b[1mClaude Code in a transcript\n'
        self.assertEqual(replacer.feed(data, flush=True), data)

    def test_large_colored_stream_is_bounded_and_forwarded(self):
        replacer = Replacer(self.profile, self.opts)
        out = b''
        for _ in range(3):
            out += replacer.feed(b'\x1b[38;2;1;2;3m' + b'x' * 100000)
        self.assertGreater(len(out), 250000)
        self.assertLess(len(replacer.buf), 20000)

    def test_flush_releases_held_suffix(self):
        replacer = Replacer(self.profile, self.opts)
        held = b'\x1b[39m\x1b[49m\x1b[1mClaude'
        self.assertEqual(replacer.feed(held), b'')
        self.assertEqual(replacer.feed(b'', flush=True), held)

    def test_replacement_failure_releases_buffer_and_stays_passthrough(self):
        profile = mock.Mock(starts=(b'held',))
        profile.replace.side_effect = ValueError('broken replacement')
        replacer = Replacer(profile, {})
        self.assertEqual(replacer.feed(b'held'), b'')
        self.assertEqual(replacer.feed(b' suffix', flush=True), b'held suffix')
        self.assertEqual(replacer.buf, b'')
        self.assertEqual(replacer.feed(b'raw'), b'raw')
        profile.replace.assert_called_once()


if __name__ == '__main__':
    unittest.main()
