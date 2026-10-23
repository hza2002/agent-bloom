#!/usr/bin/env python3
"""Import a reviewed raw terminal recording into a portable replay fixture.

Capture with the application's real terminal (for example tmux pipe-pane), then
review the recording for secrets. Redaction masks exact printable strings with
nonblank glyphs of the same approximate cell width; it does not claim to discover sensitive content.
Widths use the observer's codepoint model, not full grapheme segmentation.
CSI/ESC controls and OSC selectors remain unchanged; OSC payload text is masked.
DCS/APC/PM/SOS payloads and incomplete controls require manual privacy review.
Input/resize events and explicit state checkpoints may be added after import.
"""
import argparse
import base64
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_theme.overlay import Overlay, cwidth

FORMAT = 'agent-bloom-terminal-trace'


def encode(data):
    return base64.b64encode(data).decode('ascii')


def decode(event):
    return base64.b64decode(event['data'], validate=True)


def load(path):
    trace = json.loads(Path(path).read_text(encoding='utf-8'))
    if trace.get('format') != FORMAT or trace.get('version') != 1:
        raise ValueError('unsupported terminal trace format')
    if trace['app'] not in ('claude', 'codex'):
        raise ValueError('unknown application')
    check_size(trace['size'])
    for event in trace['events']:
        kind = event['type']
        if kind in ('output', 'input'):
            decode(event)
        elif kind == 'resize':
            check_size(event['size'])
        elif kind == 'checkpoint':
            if not event.get('expect'):
                raise ValueError('checkpoint needs independent expected state')
        else:
            raise ValueError('unknown trace event: ' + kind)
    return trace


def check_size(size):
    if (len(size) != 2 or any(type(n) is not int or n < 1 or n > 1000 for n in size)):
        raise ValueError('terminal size must contain two integers in 1..1000')


def redact(data, text):
    """Mask text without rewriting terminal control parameters or OSC selectors."""
    if not text or not text.isprintable():
        raise ValueError('redaction text must be nonempty and printable')
    mask = ''.join(ch if ch.isspace() else {0: '\u0301', 1: 'x', 2: '界'}[cwidth(ch)]
                   for ch in text).encode('utf-8')
    needle = text.encode('utf-8')

    def printable(payload):
        return re.sub(rb'[^\x00-\x1f\x7f]+',
                      lambda match: match[0].replace(needle, mask), payload)

    result = bytearray()
    pos = 0
    while pos < len(data):
        esc = data.find(b'\x1b', pos)
        if esc < 0:
            result.extend(printable(data[pos:]))
            break
        result.extend(printable(data[pos:esc]))
        end = Overlay._seq_end(data, esc)
        if end < 0:
            result.extend(data[esc:])
            break
        control = data[esc:end]
        osc = re.match(rb'\x1b\][0-9]+;', control)
        if osc:
            # Retain selector and BEL/ST terminator. Only mask the text payload.
            tail = 1 if control.endswith(b'\x07') else 2
            control = control[:osc.end()] + printable(control[osc.end():-tail]) + control[-tail:]
        result.extend(control)
        pos = end
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--app', choices=('claude', 'codex'), required=True)
    parser.add_argument('--app-version', required=True)
    parser.add_argument('--cols', type=int, required=True)
    parser.add_argument('--rows', type=int, required=True)
    parser.add_argument('--note', required=True, help='capture method and scenario; no secrets')
    parser.add_argument('--redact', action='append', default=[], help='exact printable text to mask')
    parser.add_argument('--reviewed-sanitized', action='store_true', help='confirm manual privacy review')
    args = parser.parse_args()
    check_size([args.cols, args.rows])
    data = args.raw.read_bytes()
    if len(data) > 16 * 1024 * 1024:
        parser.error('recording exceeds 16 MiB; capture a shorter scenario')
    for text in args.redact:
        try:
            data = redact(data, text)
        except ValueError as error:
            parser.error(str(error))
    trace = {
        'format': FORMAT, 'version': 1, 'app': args.app,
        'provenance': {'kind': 'real-capture', 'app_version': args.app_version,
                       'sanitized': args.reviewed_sanitized, 'note': args.note},
        'size': [args.cols, args.rows],
        'events': [{'type': 'output', 'data': encode(data)}],
    }
    # Refuse accidental overwrite of an existing fixture.
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(trace, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
