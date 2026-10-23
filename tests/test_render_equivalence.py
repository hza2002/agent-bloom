"""Rendering state remains correct when terminal detection changes the palette."""
import unittest
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

from agent_theme.themes import huawei_bloom as intro
from agent_theme.themes import get_theme
from agent_theme import art


class PaletteChangeTests(unittest.TestCase):
    def test_huawei_frames_match_pre_refactor_snapshot(self):
        # A separate process fixes locale before theme copy is constructed and
        # avoids mutating any other test's glyph/environment caches.
        script = textwrap.dedent("""
            import hashlib, json, os
            from agent_theme import art
            from agent_theme.themes import get_theme
            theme = get_theme()
            records = {}
            for mode in ('octant', 'quadrant'):
                os.environ['AGENT_THEME_GLYPHS'] = mode
                art.reset_glyphs()
                for app, brand in theme.brands.items():
                    for pi, pal in enumerate((theme.dark, theme.light)):
                        lock = art.choose(brand, 111, 49)
                        scene = theme.create_scene(111, 55, pal, brand, lock=lock, top=3)
                        scene.rng.seed(7)
                        digest = hashlib.sha256()
                        # repr() changes when a Python Unicode database learns
                        # new glyphs (notably octants). ascii() pins the encoding
                        # without discarding any glyph, position or colour.
                        digest.update(ascii(art.home_rows(lock, 3, 1.0, pal)).encode())
                        for render, count in ((scene.frame, 177), (scene.ambient_frame, 61)):
                            for n in range(count):
                                cells = render(n / 60)
                                digest.update(ascii(sorted(cells.items())).encode())
                                digest.update(scene.ansi(cells).encode())
                        records[f'{mode}/{app}/{pi}/111x55'] = digest.hexdigest()
            print(json.dumps(records))
        """)
        root = Path(__file__).resolve().parents[1]
        env = dict(os.environ, AGENT_THEME_LANG='zh-Hans', AGENT_THEME_CELL_RATIO='2.12')
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=root,
                                env=env, capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr)
        baseline = json.loads((root / 'tests/fixtures/huawei-render.json').read_text())
        self.assertEqual(json.loads(result.stdout), baseline['digests'])

    def test_settled_word_follows_background_detection(self):
        brand = get_theme().brands['claude']
        lock = art.choose(brand, 93, 42)
        self.assertIsNotNone(lock)
        scene = intro.Bloom(93, 55, get_theme().dark, brand, lock=lock, top=5)
        for palette in (get_theme().dark, get_theme().light, get_theme().dark):
            scene.pal = palette
            scene.invalidate()
            cells = scene.frame(scene.duration)
            for (row, col), lock in scene.word_lock.items():
                self.assertEqual(cells[scene.wy + row, scene.wx + col],
                                 (art.glyphs()[scene.word[row][col]], palette['ink']))
            self.assertTrue(scene.ansi(cells))


if __name__ == '__main__':
    unittest.main()
