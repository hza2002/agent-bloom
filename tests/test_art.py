import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme import art, intro  # noqa: E402


class LayoutTests(unittest.TestCase):
    def test_choose_drops_small_text_before_the_brand_groups(self):
        brand = art.BRANDS['claude']
        lock = art.choose(brand, 120, 16)
        self.assertIsNotNone(lock)
        self.assertTrue(lock.show_mark)
        self.assertTrue(lock.show_word)
        self.assertFalse(lock.show_small)
        self.assertLessEqual(lock.height, 16)

    def test_choose_falls_back_to_a_complete_mark(self):
        brand = art.BRANDS['claude']
        lock = art.choose(brand, 20, 10)
        self.assertIsNotNone(lock)
        self.assertTrue(lock.show_mark)
        self.assertFalse(lock.show_word)
        self.assertFalse(lock.show_small)
        self.assertGreaterEqual(lock.height, art.MIN_MARK_ROWS)

    def test_choose_band_ignores_a_single_notice_row(self):
        brand = art.BRANDS['codex']
        count = [0] * 55
        for row in (1, 2, 3, 5, 49, 50, 51, 52, 53, 54):
            count[row] = 1
        band = art.choose_band(brand, 91, 55, count)
        self.assertIsNotNone(band)
        lock, start, end = band
        self.assertEqual((start, end), (6, 48))
        self.assertLessEqual(lock.height, end - start + 1)

    def test_choose_band_refuses_equal_candidates(self):
        brand = art.BRANDS['claude']
        count = [0] * 25
        for row in (0, 5, 10, 15, 20):
            count[row] = 1
        self.assertIsNone(art.choose_band(brand, 80, 25, count))

    def test_choose_band_needs_top_and_bottom_chrome(self):
        brand = art.BRANDS['claude']
        count = [0] * 40
        for row in (0, 1, 2):
            count[row] = 1
        self.assertIsNone(art.choose_band(brand, 80, 40, count))

    def test_missing_groups_are_not_painted(self):
        brand = art.BRANDS['claude']
        reduced = art.choose(brand, 120, 16)
        chars = {ch for entries in art.home_rows(reduced, 0, 1.0, art.DARK).values()
                 for _, cells in entries for ch, _, _ in cells}
        self.assertNotIn('─', chars)
        self.assertNotIn(brand.slogan[0], chars)
        self.assertTrue(all(row < reduced.height
                            for row in art.home_rows(reduced, 0, 1.0, art.DARK)))

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

    def test_platform_rules_match_the_text_colour(self):
        brand = art.BRANDS['claude']
        lock = art.choose(brand, 120, 55)
        cells = [cell for entries in art.home_rows(lock, 0, 1.0, art.DARK).values()
                 for _, run in entries for cell in run]
        self.assertEqual({rgb for ch, rgb, _ in cells if ch == '─'},
                         {art.DARK['red']})
        self.assertEqual({rgb for ch, rgb, _ in cells if ch == brand.platform[0]},
                         {art.DARK['red']})

    def test_pixel_slogans_are_not_used(self):
        for rows in (44, 55, 65):
            lock = art.choose(art.BRANDS['claude'], 120, rows)
            self.assertEqual(lock.slogan_rows, 0)

    def test_choose_refuses_what_cannot_fit(self):
        brand = art.BRANDS['claude']
        self.assertIsNone(art.choose(brand, 3, 2))
        self.assertIsNone(art.choose(brand, 20, 2))

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


class BloomComponentTests(unittest.TestCase):
    def test_mark_only_lockup_still_blooms(self):
        brand = art.BRANDS['claude']
        lock = art.Lockup(brand, 0, 0, 120, show_mark=True,
                          show_word=False, show_small=False, logo_cols=20)
        scene = intro.Bloom(120, 32, art.palette(), brand, lock=lock, top=5)
        self.assertTrue(scene.ok)
        self.assertTrue(scene.frame(1.0))

    def test_lockup_without_a_mark_has_no_bloom(self):
        brand = art.BRANDS['claude']
        lock = art.Lockup(brand, 2, 0, 120, show_mark=False,
                          show_word=True, show_small=False)
        scene = intro.Bloom(120, 32, art.palette(), brand, lock=lock, top=5)
        self.assertFalse(scene.ok)

    def test_settled_wordmark_shows_the_red_sheen(self):
        brand = art.BRANDS['claude']
        lock = art.choose(brand, 111, 55)
        scene = intro.Bloom(111, 55, art.DARK, brand, lock=lock, top=5)
        base = scene.frame(2.95)
        word = list(scene.word_draw)
        for i in range(36):
            cells = scene.frame(2.02 + i * 0.02)
            if any(cells[k][1][1] < base[k][1][1] - 50 for k in word):
                return
        self.fail('wordmark never shows the red sheen')

    def test_ambient_frame_redecodes_then_settles_the_wordmark(self):
        brand = art.BRANDS['claude']
        lock = art.choose(brand, 111, 55)
        scene = intro.Bloom(111, 55, art.DARK, brand, lock=lock, top=5)
        settled = scene.frame(2.95)
        word = list(scene.word_draw)
        start = scene.ambient_frame(0.0)
        self.assertTrue(all(k in start for k in word))
        self.assertTrue(any(start[k][0] in intro.CODE for k in word))
        late = scene.ambient_frame(0.9)
        self.assertTrue(all(late[k][0] == settled[k][0] for k in word))


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
