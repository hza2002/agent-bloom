"""Apple varies its entrance, never its settled brand identity."""
import unittest
from agent_theme import art
from agent_theme.themes import get_theme


class AppleIdentityTests(unittest.TestCase):
    def test_entrances_share_final_artwork_and_three_text_lines(self):
        for app in ('claude', 'codex'):
            for palette in ('dark', 'light'):
                endings, openings = [], []
                for animation in ('spectrum', 'constellation'):
                    _, theme = get_theme('apple').select_animation(animation)
                    brand, pal = theme.brands[app], getattr(theme, palette)
                    lock = art.choose(brand, 111, 49)
                    rows = art.small_text_rows(lock, 3, pal=pal)
                    lines = [(col, cells) for row in sorted(rows) for col, cells in rows[row]]
                    self.assertEqual([''.join(ch for ch, _, _ in cells) for _, cells in lines],
                                     ['Choose your superpower', ' '.join('Think different'), '──  Apple silicon · macOS  ──'])
                    for col, cells in lines:
                        self.assertEqual(col, lock.centre(sum(art.text_width(ch) for ch, _, _ in cells)))
                    self.assertTrue(all(rgb == pal['ink'] and bold for _, rgb, bold in lines[0][1]))
                    self.assertTrue(all(rgb == pal['muted'] and not bold for _, rgb, bold in lines[1][1]))
                    self.assertTrue(all(rgb == pal['accent'] and not bold for _, rgb, bold in lines[2][1]))
                    scene = theme.create_scene(111, 55, pal, brand, lock=lock, top=3)
                    openings.append(scene.frame(.7))
                    endings.append((scene.frame(scene.duration), art.home_rows(lock, 3, pal=pal)))
                self.assertNotEqual(*openings)
                self.assertEqual(*endings)

    def test_idle_highlights_logo_decodes_word_and_returns_to_exact_home(self):
        for animation in ('spectrum', 'constellation'):
            _, theme = get_theme('apple').select_animation(animation)
            brand = theme.brands['claude']
            lock = art.choose(brand, 111, 49)
            for palette in ('dark', 'light'):
                scene = theme.create_scene(111, 55, getattr(theme, palette), brand, lock=lock, top=3)
                final = scene.frame(scene.duration)
                self.assertEqual(scene.ambient_frame(0), final)
                self.assertEqual(scene.ambient_frame(1), final)
                early = scene.ambient_frame(.15)
                self.assertEqual(early, scene.ambient_frame(.15))
                self.assertTrue(any(early[key][0] != final[key][0] for key in scene.word))
                self.assertTrue(all(scene.ambient_frame(.5)[key][0] == final[key][0]
                                    for key in scene.word))
                peak_change = 0
                for u in (.2, .35, .5, .65, .8):
                    frame = scene.ambient_frame(u)
                    self.assertEqual(frame.keys(), final.keys())
                    for key in scene.logo:
                        self.assertEqual(frame[key][0], final[key][0])
                        peak_change = max(peak_change, max(abs(a-b) for a,b in
                                                          zip(frame[key][1], final[key][1])))
                self.assertGreater(peak_change, 60)


if __name__ == '__main__':
    unittest.main()
