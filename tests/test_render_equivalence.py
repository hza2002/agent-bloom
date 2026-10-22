"""Rendering state remains correct when terminal detection changes the palette."""
import unittest

from agent_theme import art, intro


class PaletteChangeTests(unittest.TestCase):
    def test_settled_word_follows_background_detection(self):
        brand = art.BRANDS['claude']
        lock = art.choose(brand, 93, 42)
        self.assertIsNotNone(lock)
        scene = intro.Bloom(93, 55, art.DARK, brand, lock=lock, top=5)
        for palette in (art.DARK, art.LIGHT, art.DARK):
            scene.pal = palette
            scene.invalidate()
            cells = scene.frame(scene.duration)
            for (row, col), lock in scene.word_lock.items():
                self.assertEqual(cells[scene.wy + row, scene.wx + col],
                                 (art.glyphs()[scene.word[row][col]], palette['ink']))
            self.assertTrue(scene.ansi(cells))


if __name__ == '__main__':
    unittest.main()
