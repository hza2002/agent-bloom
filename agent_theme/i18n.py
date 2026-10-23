"""Small language switch for the few visible Chinese strings.

The process locale picks the script: zh_TW/HK/MO -> Traditional, zh_CN/SG ->
Simplified.  A non-Chinese locale keeps the theme's Traditional default.
AGENT_THEME_LANG=zh-Hant|zh-Hans overrides detection.
"""
import os

def detect_lang():
    override = os.environ.get('AGENT_THEME_LANG', '').strip().lower().replace('_', '-')
    if override in ('zh-hant', 'hant', 'traditional'):
        return 'zh-Hant'
    if override in ('zh-hans', 'hans', 'simplified'):
        return 'zh-Hans'
    locale = ''
    for key in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        value = os.environ.get(key, '').strip()
        if value:
            locale = value.lower().replace('-', '_')
            break
    if 'hant' in locale or any(x in locale for x in ('zh_tw', 'zh_hk', 'zh_mo')):
        return 'zh-Hant'
    if 'hans' in locale or any(x in locale for x in ('zh_cn', 'zh_sg')):
        return 'zh-Hans'
    return 'zh-Hant'


LANG = detect_lang()


def pick(traditional, simplified):
    return traditional if LANG == 'zh-Hant' else simplified
