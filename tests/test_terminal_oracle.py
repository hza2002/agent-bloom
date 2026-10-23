"""Optional real-terminal regressions; tmux runs on an isolated temporary socket."""
import os
from pathlib import Path
import shutil
import shlex
import struct
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_theme.themes import get_theme
from agent_theme import art, overlay


@unittest.skipUnless(shutil.which('tmux'), 'requires tmux')
class TerminalOracleTests(unittest.TestCase):
    def test_custom_tab_stop_wrap_preserves_application_text(self):
        # X reaches the last column and Y wraps; default eight-column tabs
        # would leave both on one row and let decoration overwrite Y.
        self.check_terminal({'tab-wrap':
            b'\x1b[3g\x1b[10;81H\x1bH\r\tXY\x1b[40;1H'},
            chunks=(1, 4096))

    def test_quarantine_exit_preserves_main_screen(self):
        prefix = b'\x1b[2J\x1b[2;1HMAIN_SENTINEL'
        stream = b'\x1b[40;1H1' + '\ufe0f'.encode() + b'\x1b[?1049l'
        self.check_terminal({'exit': stream, 'exit-cursor': stream + b'\x1b[H'},
                            chunks=(1, 4096), main=prefix, finish=True)

    def test_repeated_alt_entry_does_not_authorize_paint(self):
        text = b'\x1b[20;1HRETAINED_SENTINEL' + '😀'.encode()
        chrome = b'\x1b[HHEADER\x1b[39;1HPROMPT\x1b[40;1H'
        self.check_terminal({str(mode): text + b'\x1b[?%dh' % mode + chrome
                             for mode in (47, 1047, 1049)}, chunks=(1, 4096))

    def test_application_content_and_cursor(self):
        cases = {
            'margin': b'\x1b[10;1H' + b'X' * 81,
            'margin-sgr': b'\x1b[10;1H' + b'X' * 81 + b'\x1b[0mZ',
            'margin-lf': b'\x1b[10;1H' + b'X' * 81 + b'\nZ',
            'margin-lf-lf': b'\x1b[10;1H' + b'X' * 81 + b'\n\nZ',
            'margin-cr': b'\x1b[10;1H' + b'X' * 81 + b'\rZ',
            'margin-bs': b'\x1b[10;1H' + b'X' * 81 + b'\x08Z',
            'margin-cub': b'\x1b[10;1H' + b'X' * 81 + b'\x1b[DZ',
            'margin-lf-cub': b'\x1b[10;1H' + b'X' * 81 + b'\n\x1b[DZ',
            'margin-ht': b'\x1b[10;1H' + b'X' * 81 + b'\tZ',
            'margin-cup': b'\x1b[10;1H' + b'X' * 81 + b'\x1b[20;20HZ',
            'margin-up': b'\x1b[10;1H' + b'X' * 81 + b'\x1b[AZ',
        }
        self.check_terminal(cases)

    def test_split_vs16_keeps_application_cells(self):
        # The observer can refuse unknown widths; it must preserve app cells
        # and the real cursor even when a cluster arrives one byte at a time.
        self.check_terminal({name: ('\x1b[10;80H' + text).encode() for name, text in
                             [('vs16', '❤️X'), ('zwj', '👨‍👩‍👧‍👦X'), ('keycap', '1️⃣X'), ('combining', 'éX'), ('flag', '🇨🇳X'),
                              ('vs16-clear-relative', '❤️X\x1b[2J\x1b[B\x1b[DZ'),
                              ('zwj-clear-relative', '👨‍👩‍👧‍👦X\x1b[2J\x1b[B\x1b[DZ')]}, chunks=(1, 4, 4096))

    def check_terminal(self, cases, chunks=None, main=b'', finish=False):
        with tempfile.TemporaryDirectory(prefix='bloom-terminal-') as directory:
            socket = directory + '/socket'
            runner = Path(directory, 'writer.py')
            runner.write_text('import os,struct,sys,tty\ntty.setraw(1)\n'
                              'with open(sys.argv[1],"rb",buffering=0) as f:\n'
                              ' while True:\n'
                              '  h=f.read(4)\n'
                              '  if not h: break\n'
                              '  n=struct.unpack("!I",h)[0]; d=b""\n'
                              '  while len(d)<n: d+=f.read(n-len(d))\n'
                              '  while d: d=d[os.write(1,d):]\n')
            def tm(*args):
                return subprocess.check_output(['tmux', '-f', '/dev/null', '-S', socket, *args],
                                               stderr=subprocess.PIPE).decode()
            writers = {}
            sequence = 0
            try:
                for target in ('plain', 'bloom'):
                    fifo = directory + '/' + target
                    os.mkfifo(fifo)
                    tm('new-session', '-d', '-s', target, '-x', '81', '-y', '40',
                       shlex.join([sys.executable, str(runner), fifo]))
                    writers[target] = open(fifo, 'wb', buffering=0)
                def write(target, data):
                    nonlocal sequence
                    sequence += 1
                    marker = 'bloom-fence-' + str(sequence)
                    data += b'\x1b]2;' + marker.encode() + b'\x07'
                    packet = struct.pack('!I', len(data)) + data
                    while packet:
                        packet = packet[writers[target].write(packet):]
                    deadline = time.monotonic() + 3
                    while tm('display-message', '-p', '-t', target, '#{pane_title}').strip() != marker:
                        if time.monotonic() >= deadline:
                            self.fail('terminal output completion fence timed out')
                        time.sleep(.005)
                reset = b'\x1bc' + main + b'\x1b[?1049h\x1b[2J\x1b[H'
                home = b'HEADER\x1b[39;1HPROMPT\x1b[40;1H'
                for name, stream in cases.items():
                    for chunk in chunks or (1, len(stream)):
                        with self.subTest(case=name, chunk=chunk):
                            observer = overlay.ClaudeOverlay(81, 40, get_theme().brands['claude'])
                            write('plain', reset + home)
                            write('bloom', observer.feed(reset + home))
                            self.assertTrue(observer.visible, 'startup decoration must remain enabled')
                            decorated_rows = set(observer.visible)
                            pieces = []
                            for start in range(0, len(stream), chunk):
                                pieces.append(observer.feed(stream[start:start + chunk]))
                                decorated_rows.update(observer.visible)
                            transformed = b''.join(pieces)
                            if finish:
                                transformed += observer.finish()
                            write('plain', stream)
                            write('bloom', transformed)
                            plain = tm('capture-pane', '-p', '-t', 'plain').splitlines()
                            bloom = tm('capture-pane', '-p', '-t', 'bloom').splitlines()
                            if main:
                                self.assertIn('MAIN_SENTINEL', plain)
                            # Deferred wrap/quarantine can leave old art in the
                            # unused suffix of a row. Verify every app-text
                            # prefix, including rows the old observer excluded
                            # as "visible". Main-screen rows must match fully.
                            for i, expected in enumerate(plain):
                                actual = bloom[i]
                                if observer.alt and i in decorated_rows:
                                    actual = actual[:len(expected)]
                                self.assertEqual(actual, expected, 'row %d' % i)
                            state = '#{cursor_x},#{cursor_y},#{alternate_on},#{insert_flag}'
                            self.assertEqual(tm('display-message', '-p', '-t', 'plain', state),
                                             tm('display-message', '-p', '-t', 'bloom', state))
                            terminal_cursor = tm('display-message', '-p', '-t', 'plain',
                                                 '#{cursor_x},#{cursor_y}').strip()
                            if observer.known:
                                self.assertEqual(terminal_cursor, f'{observer.cx},{observer.cy}')
            finally:
                for writer in writers.values():
                    writer.close()
                subprocess.run(['tmux', '-S', socket, 'kill-server'], capture_output=True)
