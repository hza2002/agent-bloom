"""Apple silhouette coverage and the reported bright-rim regression."""
import os
import unittest
from unittest.mock import patch

from agent_theme import art
from agent_theme.themes import get_theme


class AppleQualityTests(unittest.TestCase):
    def tearDown(self):
        art.reset_glyphs()

    def test_font_stroke_overlaps_do_not_make_holes(self):
        contours = [[(0, 0), (2, 0), (2, 2), (0, 2)],
                    [(1, 0), (3, 0), (3, 2), (1, 2)]]
        self.assertEqual(art.coverage(contours, 3, 2, 0, 0, 1, 1, fill_rule='nonzero'),
                         [[1, 1, 1], [1, 1, 1]])
        self.assertEqual(art.coverage(contours, 3, 2, 0, 0, 1, 1),
                         [[1, 0, 1], [1, 0, 1]])

    def test_convergence_settles_without_a_bright_rim(self):
        _, theme = get_theme('apple').select_animation('constellation')
        brand = theme.brands['claude']
        lock = art.choose(brand, 111, 49)
        scene = theme.create_scene(111, 55, theme.dark, brand, lock=lock, top=3)
        final = scene.frame(scene.duration)
        logo_keys = {key for key in final if key[0] < 3 + lock.word_top}
        self.assertTrue(logo_keys)
        # The guard distinguishes actual animation from a static/empty scene.
        self.assertNotEqual(scene.frame(.7), final)
        for t in (2.1, 2.2, 2.35, 2.5, 2.7, 2.9):
            with self.subTest(t=t):
                frame = scene.frame(t)
                self.assertEqual({key: frame[key] for key in logo_keys},
                                 {key: final[key] for key in logo_keys})

    def test_apple_uses_solid_blocks_like_huawei(self):
        for mode in ('octant', 'quadrant'):
            with patch.dict(os.environ, AGENT_THEME_GLYPHS=mode):
                art.reset_glyphs()
                for key in ('spectrum', 'constellation'):
                    _, theme = get_theme('apple').select_animation(key)
                    lock = art.choose(theme.brands['claude'], 111, 49)
                    mark = lock.mark
                    grid = art.coverage(theme.art['mark'], mark.logo_cols * 2, mark.logo_rows * 4,
                                        mark.logo_ox, mark.logo_oy, mark.kx, mark.ky_sub, samples=8)
                    self.assertEqual(mark.logo_bits(), art.octant_cells(grid))
                    for pal in (theme.dark, theme.light):
                        for r, line in enumerate(mark.logo_cells(pal)):
                            for c, (ch, rgb) in enumerate(line):
                                if ch != ' ':
                                    self.assertEqual(rgb, mark.logo_color(r, c))
                        self.assertEqual({rgb for line in mark.word_cells(pal)
                                          for ch, rgb in line if ch != ' '}, {pal['ink']})
                    for palette in ('dark', 'light'):
                        with patch.dict(os.environ, AGENT_THEME_PALETTE=palette):
                            self.assertEqual({rgb for line in art.mini_logo(theme, shrink=1)
                                              for ch, rgb in line if ch != ' '},
                                             {getattr(theme, palette)['ink']})

    def test_mini_leaf_stays_separate_from_body(self):
        theme = get_theme('apple')
        with patch.dict(os.environ, AGENT_THEME_GLYPHS='octant', AGENT_THEME_PALETTE='dark'):
            art.reset_glyphs()
            inverse = {ch: bits for bits, ch in enumerate(art.glyphs())}
            pixels = set()
            for r, line in enumerate(art.mini_logo(theme, shrink=1)):
                for c, (ch, rgb) in enumerate(line):
                    alpha = (rgb[0] - theme.dark['bg'][0]) / (theme.dark['ink'][0] - theme.dark['bg'][0])
                    if alpha > .5:
                        pixels.update((c * 2 + bit % 2, r * 4 + bit // 2)
                                      for bit in range(8) if inverse[ch] & (1 << bit))
            sizes = []
            while pixels:
                pending, size = [pixels.pop()], 0
                while pending:
                    x, y = pending.pop()
                    size += 1
                    for point in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
                        if point in pixels:
                            pixels.remove(point)
                            pending.append(point)
                sizes.append(size)
            self.assertEqual(len(sizes), 2, sizes)
            self.assertGreaterEqual(min(sizes), 2)

    def test_tiny_layout_omits_unreadable_two_row_wordmark(self):
        brand = get_theme('apple').brands['claude']
        for rows in range(8, 30):
            lock = art.choose(brand, 80, rows)
            self.assertIsNotNone(lock)
            if lock.show_word:
                self.assertGreaterEqual(lock.word_rows, 3)


if __name__ == '__main__':
    unittest.main()
