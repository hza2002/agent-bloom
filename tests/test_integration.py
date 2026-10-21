"""End-to-end contract tests: the real wrapper around a fake TUI in a PTY."""
import errno
import fcntl
import os
import pty
import select
import shlex
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WRAPPER = ROOT / 'huawei-bloom'
FAKE_TUI = ROOT / 'tests' / 'fake_tui.py'
BRAND_CLAUDE = '盘古·Claude'.encode()
BRAND_CODEX = '盘古 · Codex'.encode()
PLATFORM = '盘古大模型'.encode()


class Wrapper:
    """Run huawei-bloom with a fake claude/codex binary on PATH."""

    def __init__(self, app='claude', args=(), size=(40, 100), env_extra=None):
        self.tmp = tempfile.TemporaryDirectory(prefix='hb-test-')
        fakebin = Path(self.tmp.name) / 'bin'
        fakebin.mkdir()
        for name in ('claude', 'codex'):
            script = fakebin / name
            script.write_text(
                '#!/bin/sh\nFAKE_APP=%s exec %s %s "$@"\n'
                % (name, shlex.quote(sys.executable), shlex.quote(str(FAKE_TUI))))
            script.chmod(0o755)

        self.master, slave = pty.openpty()
        self._set_size(slave, size)
        env = os.environ.copy()
        for key in list(env):
            if (key.startswith('TMUX') or key.startswith('AGENT_THEME_')
                    or key in ('TERM_PROGRAM', 'COLORFGBG', 'FAKE_PLAIN',
                               'LC_ALL', 'LC_MESSAGES')):
                env.pop(key, None)
        env.update({
            'PATH': str(fakebin) + os.pathsep + env.get('PATH', ''),
            'TERM': 'xterm-256color',
            'LANG': 'zh_CN.UTF-8',
            'AGENT_THEME_LANG': 'zh-Hans',
            'AGENT_THEME_GLYPHS': 'quadrant',
            'AGENT_THEME_CELL_RATIO': '2.12',
            'AGENT_THEME_PALETTE': 'dark',
        })
        if env_extra:
            env.update(env_extra)
        self.proc = subprocess.Popen(
            [sys.executable, str(WRAPPER), app, *args],
            stdin=slave, stdout=slave, stderr=slave,
            cwd=str(ROOT), env=env, close_fds=True)
        os.close(slave)
        self.buf = b''

    @staticmethod
    def _set_size(fd, size):
        cols, rows = size
        fcntl.ioctl(fd, termios.TIOCSWINSZ,
                    struct.pack('HHHH', rows, cols, 0, 0))

    def _read(self, timeout):
        ready, _, _ = select.select([self.master], [], [], timeout)
        if not ready:
            return b''
        try:
            return os.read(self.master, 65536)
        except OSError as exc:
            if exc.errno == errno.EIO:
                return b''
            raise

    def read_until(self, needle, timeout=6):
        deadline = time.monotonic() + timeout
        while needle not in self.buf:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            data = self._read(min(0.1, left))
            if data:
                self.buf += data
            elif self.proc.poll() is not None:
                # Drain whatever the PTY still holds after the child exits.
                while True:
                    data = self._read(0)
                    if not data:
                        break
                    self.buf += data
                if needle not in self.buf:
                    break
        if needle not in self.buf:
            tail = self.buf[-800:].decode('utf-8', 'replace')
            raise AssertionError('missing %r; tail=%r' % (needle, tail))
        return self.buf

    def send(self, data):
        os.write(self.master, data)

    def wait(self, timeout=5):
        deadline = time.monotonic() + timeout
        while self.proc.poll() is None and time.monotonic() < deadline:
            data = self._read(0.05)
            if data:
                self.buf += data
        return self.proc.wait(timeout=max(0.1, deadline - time.monotonic()))

    def resize(self, size):
        self._set_size(self.master, size)
        os.kill(self.proc.pid, signal.SIGWINCH)

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=3)
        try:
            os.close(self.master)
        except OSError:
            pass
        self.tmp.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()


class IntegrationTests(unittest.TestCase):
    def test_header_is_replaced_for_both_apps(self):
        for app, brand in (('claude', BRAND_CLAUDE), ('codex', BRAND_CODEX)):
            with self.subTest(app=app), Wrapper(app, ('--no-home',)) as session:
                session.read_until(brand, timeout=3)
                self.assertNotIn(b'Claude Code', session.buf)
                self.assertNotIn(b'OpenAI Codex', session.buf)

    def test_home_is_painted_and_input_is_not_blocked(self):
        with Wrapper('claude') as session:
            session.read_until(PLATFORM, timeout=8)
            session.send(b'hello\r')
            session.read_until(b'ACK hello', timeout=3)

    def test_resize_reaches_the_app(self):
        with Wrapper('claude', ('--no-home',)) as session:
            session.read_until(BRAND_CLAUDE, timeout=3)
            session.resize((120, 50))
            session.read_until(b'RESIZED', timeout=3)
            self.assertIsNone(session.proc.poll())

    def test_no_alt_screen_fails_open(self):
        with Wrapper('claude', env_extra={'FAKE_PLAIN': '1'}) as session:
            out = session.read_until(b'plain output', timeout=3)
            self.assertNotIn(PLATFORM, out)
            self.assertEqual(session.proc.wait(timeout=5), 0)

    def test_exit_status_is_forwarded(self):
        with Wrapper('claude', ('--no-home',)) as session:
            session.read_until(BRAND_CLAUDE, timeout=3)
            session.send(b'/exit\r')
            self.assertEqual(session.wait(timeout=5), 7)

    def test_sigterm_exits_without_hanging(self):
        with Wrapper('claude', ('--no-home',)) as session:
            session.read_until(BRAND_CLAUDE, timeout=3)
            session.proc.terminate()
            self.assertEqual(session.wait(timeout=5), 128 + signal.SIGTERM)


if __name__ == '__main__':
    unittest.main()
