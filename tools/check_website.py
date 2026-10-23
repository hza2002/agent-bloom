#!/usr/bin/env python3
"""Validate built links, asset budgets and copied canonical Markdown."""
from html.parser import HTMLParser
from pathlib import Path
import json
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'website/dist'
BASE = '/agent-bloom/'


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        self.urls.extend(value for name, value in attrs if name in ('href', 'src') and value)


def main():
    failures = []
    pages = list(DIST.rglob('*.html'))
    if not pages:
        raise SystemExit('No generated HTML')
    for page in pages:
        parser = Links()
        parser.feed(page.read_text())
        for url in parser.urls:
            parsed = urlsplit(url)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = unquote(parsed.path)
            if path.startswith('/'):
                if not path.startswith(BASE):
                    failures.append(f'{page.relative_to(DIST)}: missing project base: {url}')
                    continue
                target = DIST / path[len(BASE):]
            else:
                target = page.parent / path
            if target.is_dir():
                target /= 'index.html'
            if not target.is_file():
                failures.append(f'{page.relative_to(DIST)}: broken link: {url}')
    for source in (ROOT / 'docs/user').rglob('*.md'):
        copied = DIST / 'raw' / source.relative_to(ROOT)
        if not copied.exists() or copied.read_bytes() != source.read_bytes():
            failures.append(f'Markdown drift: {source.relative_to(ROOT)}')
    metrics = json.loads((DIST / 'generated/metrics.json').read_text())
    for clip in metrics:
        if clip['bytes'] > 2_000_000:
            failures.append(f'Clip exceeds 2 MB uncompressed: {clip["preview"]}/{clip["phase"]}')
    size = sum(path.stat().st_size for path in DIST.rglob('*') if path.is_file())
    if size > 500_000_000:
        failures.append('Site exceeds the 500 MB project budget')
    if failures:
        raise SystemExit('\n'.join(failures))
    print(f'Checked {len(pages)} pages, canonical Markdown and clip budgets; site {size:,} bytes.')


if __name__ == '__main__':
    main()
