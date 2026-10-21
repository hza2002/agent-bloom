import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme import cli  # noqa: E402
from agent_theme.apps import PROFILES  # noqa: E402


class ParseTests(unittest.TestCase):
    def test_wrapper_flags_before_and_after_app(self):
        app, args, overrides, raw, check = cli.parse(
            ['--no-title', 'claude', '--no-home', 'hello'])
        self.assertEqual(app, 'claude')
        self.assertEqual(args, ['hello'])
        self.assertEqual(overrides, [('title', False), ('home', False)])
        self.assertFalse(raw or check)

    def test_terminator_forwards_wrapper_looking_flags(self):
        app, args, overrides, _, _ = cli.parse(
            ['claude', '--', '--no-home'])
        self.assertEqual(app, 'claude')
        self.assertEqual(args, ['--no-home'])
        self.assertEqual(overrides, [])

    def test_terminator_before_app(self):
        app, args, _, _, _ = cli.parse(['--', 'codex', 'resume'])
        self.assertEqual(app, 'codex')
        self.assertEqual(args, ['resume'])


class CheckTests(unittest.TestCase):
    def test_engine_check_for_both_apps(self):
        for key, profile in PROFILES.items():
            with self.subTest(app=key):
                rows = cli.engine_check(profile)
                self.assertTrue(all(passed for _name, passed, _detail in rows), rows)


if __name__ == '__main__':
    unittest.main()
