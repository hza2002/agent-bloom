import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme import art  # noqa: E402


class LayoutTests(unittest.TestCase):
    def test_choose_returns_text_fallback_when_mark_does_not_fit(self):
        brand = art.BRANDS['claude']
        lock = art.choose(brand, 120, 16)
        self.assertIsNotNone(lock)
        self.assertIsNone(lock.mark)
        self.assertGreaterEqual(lock.width, 0)

    def test_compact_fit_gains_a_wordmark_row(self):
        brand = art.BRANDS['claude']
        # The 95x55 pane leaves 42 rows between chrome; the normal gap would
        # pick five wordmark rows, the compact gap six.
        lock = art.choose(brand, 95, 42)
        self.assertEqual(lock.word_rows, 6)
        self.assertEqual(lock.gap_logo, 2)
        self.assertLessEqual(lock.height, 42)

    def test_platform_line_keeps_one_blank_row(self):
        for brand in art.BRANDS.values():
            for rows in (42, 44):
                lock = art.choose(brand, 95, rows)
                self.assertIsNotNone(lock)
                self.assertEqual(lock.platform_top, lock.tag_top + 2)

    def test_pixel_slogans_are_not_used(self):
        for rows in (44, 55, 65):
            lock = art.choose(art.BRANDS['claude'], 120, rows)
            self.assertEqual(lock.slogan_rows, 0)

    def test_choose_refuses_what_cannot_fit(self):
        brand = art.BRANDS['claude']
        self.assertIsNone(art.choose(brand, 20, 10))
        self.assertIsNone(art.choose(brand, 120, 3))

    def test_home_rows_never_use_negative_columns(self):
        brand = art.BRANDS['claude']
        lock = art.choose(brand, 120, 16)
        rows = art.home_rows(lock, 5, 1.0, art.DARK)
        for entries in rows.values():
            for col, _cells in entries:
                self.assertGreaterEqual(col, 0)

    def test_wordmark_arm_corners_are_square(self):
        """Hinting must leave each horizontal arm with one left and right edge.

        Before snapping, the threshold sampled halfway across the E's arm ends,
        so the last row or column got chipped and the letter looked incomplete.
        """
        for cols in (111, 95):
            lock = art.choose(art.BRANDS['claude'], cols, 55)
            mark = lock.mark
            bits = mark.word_bits()
            wb = art.ART['word_bbox']
            poly = art.ART['word'][3]  # E
            sx0 = int(math.floor((min(p[0] for p in poly) - wb[0]) * mark.wkx))
            sx1 = int(math.ceil((max(p[0] for p in poly) - wb[0]) * mark.wkx))
            c0, c1 = sx0 // 2, (sx1 + 1) // 2
            spans = []
            for r, line in enumerate(bits):
                for dy in range(4):
                    on = [c * 2 + dx
                          for c in range(c0, c1 + 1)
                          for dx in range(2) if (line[c] >> (dy * 2 + dx)) & 1]
                    if on:
                        spans.append((r * 4 + dy, min(on), max(on)))
            widest = max(right - left for _, left, right in spans)
            arms = [s for s in spans if s[2] - s[1] > widest * 0.55]
            groups = []
            for span in arms:
                if groups and span[0] == groups[-1][-1][0] + 1:
                    groups[-1].append(span)
                else:
                    groups.append([span])
            self.assertEqual(len(groups), 3)
            for group in groups:
                self.assertGreaterEqual(len(group), 4)
                self.assertEqual(len({s[1] for s in group}), 1)
                self.assertEqual(len({s[2] for s in group}), 1)


class PaletteTests(unittest.TestCase):
    def test_palette_for_both_directions(self):
        light = art.palette_for((250, 250, 250))
        dark = art.palette_for((10, 10, 10))
        self.assertLess(light['ink'][0], light['bg'][0])
        self.assertGreater(dark['ink'][0], dark['bg'][0])

    def test_palette_for_unknown_keeps_current(self):
        self.assertEqual(art.palette_for(None), art.palette())


if __name__ == '__main__':
    unittest.main()
