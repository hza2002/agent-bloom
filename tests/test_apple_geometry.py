"""The source silhouette must fit the render box, including its curved left edge."""
import unittest
from agent_theme import art
from agent_theme.themes import get_theme


class AppleGeometryTests(unittest.TestCase):
    def test_render_bounds_enclose_every_outline_point(self):
        for key in ('spectrum', 'constellation'):
            _, theme = get_theme('apple').select_animation(key)
            x0, y0, x1, y1 = theme.art['logo_bbox']
            for polygon in theme.art['mark']:
                for x, y in polygon:
                    self.assertTrue(x0 <= x <= x1 and y0 <= y <= y1,
                                    '%s clips source point %r outside %r' % (key, (x, y), theme.art['logo_bbox']))

    def test_orange_bite_single_pixel_notch_is_filled_at_reported_size(self):
        asset = get_theme('apple').art
        mark = art.Mark(38, 4, asset)
        grid = art.coverage(asset['mark'], 76, mark.logo_rows * 4,
                            mark.logo_ox, mark.logo_oy, mark.kx, mark.ky_sub, samples=8)
        expected = art.octant_cells(grid)
        self.assertFalse(expected[12][31] & 2)
        expected[12][31] |= 2  # x=63, y=48: isolated notch between two filled pixels
        self.assertEqual(mark.logo_bits(), expected)

    def test_horizontal_padding_does_not_recover_missing_pixels(self):
        # A reference raster with extra room on both sides must contain exactly
        # the same silhouette: padding must never reveal previously clipped art.
        asset = get_theme('apple').art
        mark = art.Mark(80, 3, asset)
        width, height = mark.logo_cols * 2, mark.logo_rows * 4
        normal = art.coverage(asset['mark'], width, height, mark.logo_ox, mark.logo_oy,
                              mark.kx, mark.ky_sub, samples=16)
        padded = art.coverage(asset['mark'], width + 16, height,
                              mark.logo_ox - 8 / mark.kx, mark.logo_oy,
                              mark.kx, mark.ky_sub, samples=16)
        self.assertGreater(sum(map(sum, normal)), 100)
        self.assertAlmostEqual(sum(map(sum, normal)), sum(map(sum, padded)), places=6)


if __name__ == '__main__':
    unittest.main()
