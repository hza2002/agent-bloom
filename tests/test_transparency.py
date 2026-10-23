"""The decoration layer may insert bytes, but must preserve application output."""
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme.themes import get_theme
from agent_theme import art, overlay


class MarkedOverlay(overlay.Overlay):
    """Make decoration insertions distinguishable from application bytes."""

    def _wrap(self, body):
        return b'\x00BLOOM<' + body.encode('utf-8') + b'>BLOOM\x00' if body else b''


class TransparencyTests(unittest.TestCase):
    def make(self, in_alt=False, cls=overlay.Overlay):
        return cls(81, 40, get_theme().brands['claude'], in_alt=in_alt)

    def test_app_alt_entry_is_never_replaced(self):
        for sequence in (b'\x1b[?1049h', b'\x1b[?1047h', b'\x1b[?47h'):
            with self.subTest(sequence=sequence):
                self.assertEqual(self.make(in_alt=True).feed(sequence), sequence)

    def test_inline_output_does_not_change_application_screen(self):
        for sequence in (b'hello', b'\x1b[1;1Hhello', '你好'.encode()):
            with self.subTest(sequence=sequence):
                self.assertEqual(self.make(in_alt=True).feed(sequence), sequence)

    def test_unknown_intermediate_does_not_permanently_disable_decoration(self):
        ov = self.make()
        ov.feed(b'\x1b[?1049h\x1b[2J')
        sequence = b'\x1b[1+z'
        self.assertEqual(ov.feed(sequence), sequence)
        ov.feed(b'\x1b[2J')
        self.assertTrue(ov.known)
        self.assertFalse(ov.disabled)
        self.assertFalse(ov.passthrough)

    def test_nonpainting_controls_are_transparent_at_every_split(self):
        sequences = (
            b'\x1b[?2026$p', b'\x1b[4$p', b'\x1b[2 q',
            b'\x1b[c', b'\x1b[>0c', b'\x1b[6n',
            b'\x1b]0;window title\x07', b'\x1b]10;?\x1b\\',
            b'\x1bP$qm\x1b\\',
        )
        for sequence in sequences:
            for split in range(len(sequence) + 1):
                with self.subTest(sequence=sequence, split=split):
                    ov = self.make()
                    ov.feed(b'\x1b[?1049h\x1b[2J')
                    result = ov.feed(sequence[:split]) + ov.feed(sequence[split:])
                    self.assertEqual(result, sequence)
                    self.assertTrue(ov.known)
                    self.assertFalse(ov.disabled)

    def test_stripping_insertions_recovers_original_stream_at_every_split(self):
        # Explicit application sync frames also exercise decoration at frame-end,
        # without confusing its inserted sync wrappers with application controls.
        stream = (b'\x1b[?1049h\x1b[?2026h\x1b[2J\x1b[1;1HHEADER'
                  b'\x1b[39;1HPROMPT\x1b[39;7H\x1b[?2026l'
                  b'\x1b[?2026h\x1b[4;1H' + ('界' * 81).encode() +
                  b'\x1b[?2026l\x1b[?1049l\x1b[?1049h\x1b[2J')
        insertions = re.compile(rb'\x00BLOOM<.*?>BLOOM\x00', re.DOTALL)
        for split in range(len(stream) + 1):
            with self.subTest(split=split):
                ov = self.make(in_alt=True, cls=MarkedOverlay)
                result = ov.feed(stream[:split]) + ov.feed(stream[split:])
                self.assertIn(b'\x00BLOOM<', result)
                self.assertEqual(insertions.sub(b'', result), stream)


if __name__ == '__main__':
    unittest.main()
