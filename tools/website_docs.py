#!/usr/bin/env python3
"""Copy canonical Markdown for agents and verify generated README quick starts."""
import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
MARKER = re.compile(r'(<!-- quickstart:start -->\n)(.*?)(\n<!-- quickstart:end -->)', re.S)


def quickstart(source):
    matches = list(MARKER.finditer(source))
    if len(matches) != 1:
        raise ValueError('Expected exactly one quickstart block')
    return matches[0].group(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sync-readme', action='store_true')
    args = parser.parse_args()
    public = ROOT / 'website/public'
    raw = public / 'raw/docs/user'
    if raw.exists():
        shutil.rmtree(raw)
    raw.mkdir(parents=True)
    index = ['# Agent Bloom', '', '> Terminal themes for Claude Code and Codex CLI.', '',
             'Use the installation guide for both human and agent installs. Read it before changing shell or application configuration.', '',
             '## Guides', '']
    catalogue = json.loads((public / 'generated/catalogue.json').read_text())
    installation = {}
    for locale, readme in (('zh', 'README.md'), ('en', 'README.en.md')):
        folder = ROOT / 'docs/user' / locale
        expected = quickstart((folder / 'get-started.md').read_text())
        installation[locale] = re.fullmatch(r'```sh\n(.*?)\n```', expected, re.S).group(1)
        path = ROOT / readme
        actual = path.read_text()
        if quickstart(actual) != expected:
            if not args.sync_readme:
                raise SystemExit(f'{readme} quickstart drift. Run python3 tools/website_docs.py --sync-readme')
            path.write_text(MARKER.sub(lambda m: m.group(1) + expected + m.group(3), actual))
        for source in sorted(folder.glob('*.md')):
            target = raw / locale / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            index.append(f'- [{locale}: {source.stem}](raw/docs/user/{locale}/{source.name})')
        reference = '# Command reference\n\nGenerated from the current CLI and theme registry.\n\n```text\n' + catalogue['help'] + '```\n\n'
        reference += '| Theme | Animations | Default |\n| --- | --- | --- |\n'
        for theme in catalogue['themes']:
            reference += '| ' + ' | '.join((theme['id'], ', '.join(a['id'] for a in theme['animations']), theme['defaultAnimation'])) + ' |\n'
        (raw / locale / 'reference.md').write_text(reference)
        index.append(f'- [{locale}: reference](raw/docs/user/{locale}/reference.md)')
    (public / 'llms.txt').write_text('\n'.join(index) + '\n')
    (public / 'generated/installation.json').write_text(json.dumps(installation, ensure_ascii=False))


if __name__ == '__main__':
    main()
