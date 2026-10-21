import os
import sys
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True

from agent_theme import i18n  # noqa: E402


class LanguageTests(unittest.TestCase):
    def detect(self, env):
        with mock.patch.dict(os.environ, env, clear=True):
            return i18n.detect_lang()

    def test_traditional_locales(self):
        for locale in ('zh_TW.UTF-8', 'zh_HK.UTF-8', 'zh_Hant.UTF-8'):
            with self.subTest(locale=locale):
                self.assertEqual(self.detect({'LANG': locale}), 'zh-Hant')

    def test_simplified_locales(self):
        for locale in ('zh_CN.UTF-8', 'zh_SG.UTF-8', 'zh_Hans.UTF-8'):
            with self.subTest(locale=locale):
                self.assertEqual(self.detect({'LANG': locale}), 'zh-Hans')

    def test_non_chinese_defaults_to_traditional(self):
        self.assertEqual(self.detect({'LANG': 'en_US.UTF-8'}), 'zh-Hant')

    def test_explicit_override_wins(self):
        self.assertEqual(self.detect({'LANG': 'zh_CN.UTF-8',
                                      'AGENT_THEME_LANG': 'zh-Hant'}), 'zh-Hant')
        self.assertEqual(self.detect({'LANG': 'zh_TW.UTF-8',
                                      'AGENT_THEME_LANG': 'zh-Hans'}), 'zh-Hans')


if __name__ == '__main__':
    unittest.main()
