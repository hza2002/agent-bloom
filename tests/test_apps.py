import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme import art  # noqa: E402
from agent_theme.apps import NEW_CLAUDE, NEW_CODEX, PROFILES, flower_rows  # noqa: E402


class EnginePolicyTests(unittest.TestCase):
    def test_profiles_own_their_engine_policy(self):
        claude = PROFILES['claude']
        codex = PROFILES['codex']
        self.assertEqual(claude.home_top, 3)
        self.assertEqual(codex.home_top, 10)
        self.assertEqual(claude.startup_args, ())
        self.assertEqual(codex.startup_args, ('-c', 'tui.effects.welcome=false',
                                              '-c', 'tui.show_tooltips=false'))
        self.assertEqual(claude.overlay_type().__name__, 'ClaudeOverlay')
        self.assertEqual(codex.overlay_type().__name__, 'CodexOverlay')


class ClassificationTests(unittest.TestCase):
    def test_claude_modes(self):
        claude = PROFILES['claude']
        cases = [
            ([], 'intro', False),
            (['hello'], 'intro', True),
            (['-c'], 'overlay', False),
            (['--continue'], 'overlay', False),
            (['--resume', 'id'], 'overlay', True),
            (['doctor'], 'direct', False),
            (['--print', 'hello'], 'direct', True),
            (['--', 'hello'], 'intro', True),
        ]
        for args, mode, prompt in cases:
            with self.subTest(args=args):
                self.assertEqual(claude.classify(args), mode)
                self.assertEqual(claude.has_prompt(args), prompt)

    def test_codex_modes(self):
        codex = PROFILES['codex']
        self.assertEqual(codex.classify([]), 'intro')
        self.assertEqual(codex.classify(['resume']), 'overlay')
        self.assertEqual(codex.classify(['resume', 'id']), 'overlay')
        self.assertEqual(codex.classify(['exec', 'hello']), 'direct')
        self.assertEqual(codex.classify(['--no-alt-screen']), 'direct')
        self.assertFalse(codex.has_prompt(['resume', 'id']))


class PatternTests(unittest.TestCase):
    def test_claude_header_is_scoped(self):
        claude = PROFILES['claude']
        opts = dict(claude.defaults)
        header = (b'\x1b[12G\x1b[39m\x1b[49m\x1b[1mClaude Code'
                  b'\x1b[24G\x1b[22m')
        out = claude.replace(header, opts)
        self.assertIn(NEW_CLAUDE, out)
        self.assertNotIn(b'Claude Code', out)
        bold = b'\x1b[1mClaude Code in a transcript'
        self.assertEqual(claude.replace(bold, opts), bold)

    def test_claude_compact_header(self):
        claude = PROFILES['claude']
        opts = dict(claude.defaults)
        raw = (b'\x1b[H\r\x1b[11C\x1b[1B\x1b[1mClaude Code'
               b'\x1b[24G\x1b[22m')
        self.assertIn(NEW_CLAUDE, claude.replace(raw, opts))

    def test_codex_header_keeps_width(self):
        codex = PROFILES['codex']
        opts = dict(codex.defaults)
        raw = b'\x1b[38;2;1;2;3m>_ \x1b[1m\x1b[39;49mOpenAI Codex'
        out = codex.replace(raw, opts)
        self.assertIn(b'\xe2\x9c\xbf ', out)
        self.assertIn(NEW_CODEX, out)
        # `>_ ` + `OpenAI Codex` is 15 cells; the branded row stays 15 cells.
        self.assertIn(NEW_CODEX + b' ', out)

    def test_codex_header_only(self):
        codex = PROFILES['codex']
        opts = dict(codex.defaults, logo=False)
        raw = b'\x1b[38;2;1;2;3m>_ \x1b[1m\x1b[39;49mOpenAI Codex'
        out = codex.replace(raw, opts)
        self.assertIn(b'>_ ', out)
        self.assertIn(NEW_CODEX, out)
        self.assertNotIn(b'\xe2\x9c\xbf ', out)


class GlyphCacheTests(unittest.TestCase):
    def tearDown(self):
        art.reset_glyphs()

    def test_flower_cache_follows_the_glyph_mode(self):
        with mock.patch.dict(os.environ, {'AGENT_THEME_GLYPHS': 'quadrant'}, clear=True):
            art.reset_glyphs()
            quad = flower_rows()
        with mock.patch.dict(os.environ, {'AGENT_THEME_GLYPHS': 'octant'}, clear=True):
            art.reset_glyphs()
            octa = flower_rows()
        self.assertNotEqual(quad, octa)


if __name__ == '__main__':
    unittest.main()
