"""Replay reviewed real application streams, plus a labelled protocol scenario."""
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from agent_theme.themes import get_theme
from agent_theme import art, overlay
from tools import terminal_trace

MARKER = re.compile(rb'\x00BLOOM<.*?>BLOOM\x00', re.DOTALL)
SYNC = (b'\x1b[?2026h', b'\x1b[?2026l')


def marked(cls):
    class Marked(cls):
        def _wrap(self, body):
            return b'\x00BLOOM<' + body.encode('utf-8') + b'>BLOOM\x00' if body else b''
    return Marked


def preserved(original, result):
    """All app bytes survive; only marked draws and extra sync wrappers may occur.

    Identical app/inserted sync bytes cannot be distinguished after emission.
    Match app bytes first, allowing extra complete sync controls at mismatches.
    """
    result = MARKER.sub(b'', result)
    # Atomic tokens prevent an inserted ESC from partially consuming an app CSI.
    token = re.compile(rb'\x1b\[\?2026[hl]|[\s\S]')
    expected = token.findall(original)
    pos = 0
    for item in token.findall(result):
        if pos < len(expected) and item == expected[pos]:
            pos += 1
        elif item not in SYNC:
            return False
    return pos == len(expected)


def snapshot(ov):
    state = {name: getattr(ov, name) for name in
             ('alt', 'known', 'disabled', 'passthrough', 'submitted',
              'cols', 'rows', 'cx', 'cy', 'carry')}
    # Copy mutable occupancy state: later clears/resizes must not rewrite an
    # earlier checkpoint's evidence. Decoration placement is deliberately absent.
    state['grid'] = tuple(bytes(row) for row in ov.grid)
    state['count'] = tuple(ov.count)
    state['unsafe_modes'] = sorted(ov.unsafe_modes)
    return state


def replay(trace, chunk):
    cls = {'claude': overlay.ClaudeOverlay, 'codex': overlay.CodexOverlay}[trace['app']]
    ov = marked(cls)(*trace['size'], get_theme().brands[trace['app']])
    original = bytearray()
    result = bytearray()
    states = []
    with patch.object(overlay.time, 'monotonic', return_value=100.0):
        for event in trace['events']:
            kind = event['type']
            if kind == 'output':
                data = terminal_trace.decode(event)
                original.extend(data)
                for start in range(0, len(data), chunk):
                    result.extend(ov.feed(data[start:start + chunk]))
            elif kind == 'input':
                ov.note_input(terminal_trace.decode(event))
            elif kind == 'resize':
                ov.resize(*event['size'])
            elif kind == 'checkpoint':
                state = snapshot(ov)
                for key, expected in event['expect'].items():
                    if key not in state:
                        raise AssertionError('unsupported checkpoint key: ' + key)
                    if state[key] != expected:
                        raise AssertionError('%s: expected %r, got %r' % (key, expected, state[key]))
                states.append(state)
        # EOF must release an incomplete control sequence unchanged too.
        final = snapshot(ov)
        result.extend(ov.finish())
    return bytes(original), bytes(result), states, final


class ReplayTests(unittest.TestCase):
    def check_trace(self, trace):
        baseline = None
        for chunk in (1, 7, 4096, 1024 * 1024):
            with self.subTest(chunk=chunk):
                original, result, states, final = replay(trace, chunk)
                self.assertTrue(preserved(original, result), 'application stream changed')
                # App occupancy, cursor and safety state must be independent of
                # PTY read boundaries at every checkpoint and at EOF. Cosmetic
                # header anchors and decoration timing are outside this contract.
                stable = (states, final)
                if baseline is None:
                    baseline = stable
                self.assertEqual(stable, baseline)

    def test_protocol_scenario(self):
        # Synthetic, explicitly not evidence of real application compatibility.
        def output(data):
            return {'type': 'output', 'data': terminal_trace.encode(data)}
        self.check_trace({'app': 'claude', 'size': [93, 55], 'events': [
            output(b'\x1b[?1049h\x1b[2J\x1b[?2026$p'),
            {'type': 'checkpoint', 'expect': {'alt': True, 'known': True, 'disabled': False}},
            {'type': 'resize', 'size': [81, 40]},
            {'type': 'checkpoint', 'expect': {'known': False}},
            output(b'\x1b[2J\x1b[1;1HHEADER\x1b[39;1HPROMPT'),
            {'type': 'checkpoint', 'expect': {'known': True, 'disabled': False}},
            output(b'\x1b[?1049l\x1b]unfinished'),
            {'type': 'checkpoint', 'expect': {'alt': False}},
        ]})

    def test_real_recordings(self):
        fixtures = sorted((ROOT / 'tests' / 'fixtures' / 'terminal').glob('*.json'))
        self.assertTrue(fixtures, 'real terminal recordings are missing')
        apps = set()
        for path in fixtures:
            with self.subTest(fixture=path.name):
                trace = terminal_trace.load(path)
                self.assertEqual(trace['provenance']['kind'], 'real-capture')
                self.assertIs(trace['provenance']['sanitized'], True)
                self.assertTrue(any(event['type'] == 'checkpoint' for event in trace['events']))
                apps.add(trace['app'])
                if path.name == 'claude-2.1.304.json':
                    output = b''.join(terminal_trace.decode(event) for event in trace['events']
                                      if event['type'] == 'output')
                    self.assertIn(b'\x1b[?2026$p', output, 'Claude query regression absent from capture')
                self.check_trace(trace)
        self.assertEqual(apps, {'claude', 'codex'})

    def test_redaction_preserves_controls_and_osc_selectors(self):
        source = (b'2026\x1b[?2026$p\x1b]2026;2026\x07'
                  b'\x1b]0;2026\x1b\\\x1bP2026\x1b\\\x1b[2026')
        expected = (b'xxxx\x1b[?2026$p\x1b]2026;xxxx\x07'
                    b'\x1b]0;xxxx\x1b\\\x1bP2026\x1b\\\x1b[2026')
        self.assertEqual(terminal_trace.redact(source, '2026'), expected)
        self.assertEqual(terminal_trace.redact('姓名 A'.encode(), '姓名 A'), '界界 x'.encode())
        with self.assertRaises(ValueError):
            terminal_trace.redact(source, '\x1b[2026')

    def test_preservation_rejects_loss_reorder_and_mutation(self):
        original = b'\x1b[2Jabc\x1b[6n'
        for altered in (original[:-1], original.replace(b'abc', b'cba'), original + b'x'):
            self.assertFalse(preserved(original, altered))
        self.assertFalse(preserved(SYNC[0] + SYNC[0] + b'abc', SYNC[0] + b'abc'))
        self.assertFalse(preserved(SYNC[0] + SYNC[1], SYNC[1] + SYNC[0]))
        self.assertTrue(preserved(original, SYNC[0] + b'\x00BLOOM<draw>BLOOM\x00' + SYNC[1] + original))


if __name__ == '__main__':
    unittest.main()
