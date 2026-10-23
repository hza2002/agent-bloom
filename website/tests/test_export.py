import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('export_website', ROOT / 'tools/export_website.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class ExportTests(unittest.TestCase):
    def test_delta_roundtrip_including_erase_and_colour_change(self):
        first = {0: ('A', (1, 2, 3), False), 5: ('中', (9, 8, 7), True)}
        second = {0: ('A', (3, 2, 1), False), 3: ('█', (7, 8, 9), False)}
        originals = [(0, first), (20, second), (40, {})]
        encoded = exporter.encode_frames(originals)
        restored = {}
        for (stamp, delta), (expected_stamp, expected) in zip(encoded['frames'], originals):
            for pos, token in zip(delta[::2], delta[1::2]):
                if token == -1:
                    restored.pop(pos, None)
                else:
                    restored[pos] = encoded['tokens'][token]
            self.assertEqual(stamp, expected_stamp)
            self.assertEqual(restored, expected)

    def test_all_production_variants_settle_and_remain_in_bounds(self):
        for name in exporter.THEME_NAMES:
            theme = exporter.get_theme(name)
            for animation in theme.animations:
                _, selected = theme.select_animation(animation.key)
                for app in theme.brands:
                    for mode in ('dark', 'light'):
                        palette = getattr(theme, mode)
                        scene, lock, top = exporter.scene_for(selected, app, palette)
                        expected = exporter.flatten(exporter.art.home_rows(lock, top, 1, palette))
                        with self.subTest(theme=name, animation=animation.key, app=app, mode=mode):
                            frames = list(exporter.sample_frames(selected, app, palette))
                            self.assertEqual(frames[-1][1], expected)
                            self.assertTrue(any(cells != expected for _, cells in frames))
                            self.assertTrue(all(0 <= pos < exporter.COLS * exporter.ROWS
                                                for _, cells in frames for pos in cells))

    def test_ambient_moves_and_restores_production_home(self):
        for name in exporter.THEME_NAMES:
            theme = exporter.get_theme(name)
            for animation in theme.animations:
                _, selected = theme.select_animation(animation.key)
                for mode in ('light', 'dark'):
                    palette = getattr(selected, mode)
                    _, lock, top = exporter.scene_for(selected, 'claude', palette)
                    expected = exporter.flatten(exporter.art.home_rows(lock, top, 1, palette))
                    frames = list(exporter.sample_ambient(selected, 'claude', palette))
                    with self.subTest(theme=name, animation=animation.key, mode=mode):
                        self.assertEqual(frames[-1][1], expected)
                        self.assertTrue(any(cells != expected for _, cells in frames))
                        self.assertTrue(all(0 <= pos < exporter.COLS * exporter.ROWS
                                            for _, cells in frames for pos in cells))

    def test_preview_is_deterministic(self):
        theme = exporter.get_theme(exporter.DEFAULT_THEME)
        first = list(exporter.sample_frames(theme, 'claude', theme.dark))
        second = list(exporter.sample_frames(theme, 'claude', theme.dark))
        self.assertEqual(first, second)

    def test_wide_text_uses_terminal_columns(self):
        cells = exporter.flatten({2: [(4, [('中', (1, 2, 3), False), ('A', (1, 2, 3), False)])]})
        self.assertEqual(set(cells), {2 * exporter.COLS + 4, 2 * exporter.COLS + 6})

    def test_header_assets_are_valid_in_both_palettes(self):
        for name in exporter.THEME_NAMES:
            for mode in ('light', 'dark'):
                with self.subTest(theme=name, mode=mode):
                    svg = ET.fromstring(exporter.header_poster(exporter.get_theme(name), mode))
                    self.assertTrue(list(svg))
                    self.assertEqual(svg.attrib['viewBox'].split()[:3], ['0', '0', '72'])


if __name__ == '__main__':
    unittest.main()
