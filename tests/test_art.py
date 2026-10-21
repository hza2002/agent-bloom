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
