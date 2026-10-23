"""The shipped header must reproduce the approved pixels without colour leaks."""
import json
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from agent_theme import art, overlay
from agent_theme.themes import get_theme


class AppleHeaderTests(unittest.TestCase):
    def tearDown(self):
        art.reset_glyphs()
        art._MINI_CACHE.clear()

    def test_matches_approved_colours_and_resets_after_each_row(self):
        expected = json.loads((Path(__file__).parent / 'fixtures/apple-header-approved.json').read_text())
        inverse = {ch: bits for bits, ch in enumerate(art.OCTANT_TABLE)}
        for mode in ('octant', 'quadrant'):
            for palette in ('dark', 'light'):
                with patch.dict(os.environ, AGENT_THEME_GLYPHS=mode, AGENT_THEME_PALETTE=palette):
                    art.reset_glyphs()
                    for animation in ('spectrum', 'constellation'):
                        with self.subTest(mode=mode, palette=palette, animation=animation):
                            _, theme = get_theme('apple').select_animation(animation)
                            pixels = [[None] * 18 for _ in range(12)]
                            rows = art.header_rows(theme)
                            self.assertEqual(len(rows), 3)
                            for r, (line, width) in enumerate(zip(rows, (8, 9, 9))):
                                foreground = background = '#ff00ff'  # inherited app colour
                                column = 0
                                for token in re.findall(r'\x1b\[[0-9;]*m|[^\x1b]', line.decode()):
                                    if token.startswith('\x1b'):
                                        args = token[2:-1].split(';')
                                        if args[0] == '39': foreground = None
                                        elif args[0] == '49': background = None
                                        elif args[0] in ('38', '48'):
                                            self.assertEqual(args[1], '2')
                                            colour = '#' + ''.join('%02x' % int(v) for v in args[2:])
                                            if args[0] == '38': foreground = colour
                                            else: background = colour
                                        else: self.assertEqual(args, ['22'])
                                        continue
                                    self.assertEqual(overlay.cwidth(token), 1)
                                    bits = inverse[token]
                                    for k in range(8):
                                        pixels[r * 4 + k // 2][column * 2 + k % 2] = (
                                            foreground if bits & (1 << k) else background)
                                    column += 1
                                self.assertEqual(column, width)
                                self.assertIsNone(background, 'stripe background leaks into app text')
                                self.assertIsNone(foreground, 'badge foreground leaks into app text')
                            reference = expected[mode][palette]
                            if mode == 'quadrant':
                                reference = [line for line in reference for _ in range(2)]
                            self.assertEqual(pixels, reference)
                            self.assertEqual(art.header_rows(theme), rows)  # cached repaint


if __name__ == '__main__':
    unittest.main()
