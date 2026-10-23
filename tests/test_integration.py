"""End-to-end contract tests: the real wrapper around a fake TUI in a PTY."""
import errno
import fcntl
import json
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
WRAPPER = ROOT / 'agent-bloom'
FAKE_TUI = ROOT / 'tests' / 'fake_tui.py'
BRAND_CLAUDE = '盘古·Claude'.encode()
BRAND_CODEX = '盘古 · Codex'.encode()
PLATFORM = '盘古大模型'.encode()


class Wrapper:
    """Run agent-bloom with a fake claude/codex binary on PATH."""

    def __init__(self, app='claude', args=(), size=(40, 100), env_extra=None,
                 shell=False):
        self.tmp = tempfile.TemporaryDirectory(prefix='hb-test-')
        fakebin = Path(self.tmp.name) / 'bin'
        fakebin.mkdir()
        for name in ('claude', 'codex'):
            script = fakebin / name
            script.write_text(
                '#!/bin/sh\nFAKE_APP=%s exec %s %s "$@"\n'
                % (name, shlex.quote(sys.executable), shlex.quote(str(FAKE_TUI))))
            script.chmod(0o755)
        # Only used when a test sets TMUX_PANE: widen the startup window so a
        # termination signal lands while the wrapper is still setting up.
        tmux = fakebin / 'tmux'
        tmux.write_text('#!/bin/sh\nexec sleep 5\n')
        tmux.chmod(0o755)

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
        command = [sys.executable, str(WRAPPER), app, *args]
        def controlling_terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        if shell:
            env.update(PS1='HB_SHELL> ', PROMPT_COMMAND='', BASH_ENV='', ENV='')
        self.proc = subprocess.Popen(
            ['/bin/bash', '--noprofile', '--norc', '-i'] if shell else command,
            stdin=slave, stdout=slave, stderr=slave,
            cwd=str(ROOT), env=env, close_fds=True,
            preexec_fn=controlling_terminal if shell else None)
        os.close(slave)
        self.buf = b''
        if shell:
            self.read_until(b'HB_SHELL> ')
            self.buf = b''
            self.send(shlex.join(command).encode() + b'\n')

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
            # Cleanup must keep consuming output: otherwise animation can fill
            # the PTY and turn an ordinary teardown into a forced-exit test.
            self.proc.terminate()
            try:
                if self.master < 0:
                    self.proc.wait(timeout=3)
                else:
                    self.wait(timeout=3)
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
    def test_apple_theme_through_the_real_wrapper(self):
        for app, header in (('claude', 'AppleClaude'), ('codex', 'Apple Codex')):
            for animation in ('spectrum', 'constellation'):
                with self.subTest(app=app, animation=animation), Wrapper(
                        app, ('--theme', 'apple', '--animation', animation, '--no-ambient'),
                        size=(111, 55)) as session:
                    session.read_until(header.encode())
                    session.read_until('Apple silicon · macOS'.encode())
                    self.assertNotIn(PLATFORM, session.buf)
                    session.send(b'apple-input\r')
                    session.read_until(b'ACK apple-input')
                    session.send(b'/exit\r')
                    self.assertEqual(session.wait(), 7)

    def test_resume_stream_cancel_clear_and_submit(self):
        # Real wrapper/PTY, synthetic app: this pins the transport and session
        # contract without treating invented output as a real app recording.
        for app, resume, brand in (('claude', ('--continue',), BRAND_CLAUDE),
                                   ('codex', ('resume', 'fixture'), BRAND_CODEX)):
            with self.subTest(app=app), Wrapper(
                    app, ('--no-ambient',) + resume, size=(120, 40)) as session:
                session.read_until(brand)
                session.send(b'/stream\r')
                session.read_until(b'chunk-1')
                self.assertNotIn(PLATFORM, session.buf)
                session.send(b'\x03')
                session.read_until(b'STREAM_CANCELLED')
                self.assertNotIn(PLATFORM, session.buf)
                session.buf = b''
                session.send(b'/clear\r')
                session.read_until(PLATFORM)
                session.buf = b''
                session.send(b'after-clear\r')
                session.read_until(b'ACK after-clear')
                self.assertNotIn(PLATFORM, session.buf)
                session.send(b'/exit\r')
                self.assertEqual(session.wait(), 7)

    def test_ctrl_z_returns_to_shell_and_fg_restores_input(self):
        with Wrapper('claude', ('--no-home',), shell=True) as session:
            session.read_until(BRAND_CLAUDE)
            session.buf = b''
            session.send(b'\x1a')
            session.read_until(b'HB_SHELL> ')
            # Prove that the shell owns a usable terminal, not just that a
            # signal mock was called. Split the marker to avoid matching echo.
            session.send(b"printf 'SHELL_%s\\n' READY\n")
            session.read_until(b'SHELL_READY')
            session.buf = b''
            session.send(b'fg\n')
            session.send(b'after-resume\r')
            session.read_until(b'ACK after-resume')
            session.buf = b''
            session.send(b'/exit\r')
            session.read_until(b'HB_SHELL> ')
            session.send(b'exit\n')
            session.wait()

    def test_terminal_close_kills_app_ignoring_hangup(self):
        with tempfile.TemporaryDirectory(prefix='hb-hangup-') as directory:
            pid_path = Path(directory) / 'pid'
            with Wrapper('claude', ('--no-home',),
                         env_extra={'FAKE_PID_PATH': str(pid_path)}) as session:
                session.read_until(BRAND_CLAUDE)
                session.send(b'/ignore-hup\r')
                session.read_until(b'IGNORING_HUP')
                app_pid = int(pid_path.read_text())
                app_gone = False
                try:
                    os.close(session.master)
                    session.master = -1
                    self.assertEqual(session.proc.wait(timeout=7), 129)
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline:
                        try:
                            os.kill(app_pid, 0)
                        except ProcessLookupError:
                            app_gone = True
                            break
                        time.sleep(0.02)
                    else:
                        self.fail('app survived the closed terminal')
                finally:
                    if not app_gone:
                        try:
                            os.kill(app_pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass

    def test_codex_startup_preserves_user_arguments_without_overrides(self):
        args = ('-m', 'test-model', '-c', 'user.setting=true')
        for flags in ((), ('--no-home',)):
            with self.subTest(flags=flags), Wrapper('codex', flags + args,
                                                   size=(111, 55)) as session:
                session.read_until(BRAND_CODEX, timeout=3)
                session.send(b'/args\r')
                out = session.read_until(b':ARGS_END', timeout=3)
                payload = out.split(b'ARGS_BEGIN:', 1)[1].split(b':ARGS_END', 1)[0]
                self.assertEqual(json.loads(payload), list(args))

    def test_header_is_replaced_for_both_apps(self):
        for app, brand in (('claude', BRAND_CLAUDE), ('codex', BRAND_CODEX)):
            with self.subTest(app=app), Wrapper(app, ('--no-home',)) as session:
                session.read_until(brand, timeout=3)
                self.assertNotIn(b'Claude Code', session.buf)
                self.assertNotIn(b'OpenAI Codex', session.buf)

    def test_home_is_painted(self):
        with Wrapper('claude') as session:
            session.read_until(PLATFORM, timeout=8)

    def test_input_is_forwarded_during_intro(self):
        with Wrapper('claude') as session:
            session.read_until(BRAND_CLAUDE, timeout=3)
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

    def test_input_reaches_app_while_animation_output_is_blocked(self):
        with tempfile.TemporaryDirectory(prefix='hb-ack-') as directory:
            ack = Path(directory) / 'received'
            with Wrapper('claude', size=(111, 55),
                         env_extra={'FAKE_ACK_PATH': str(ack)}) as session:
                session.read_until(BRAND_CLAUDE, timeout=3)
                time.sleep(0.5)
                session.send(b'/ack\r')
                deadline = time.monotonic() + 1
                while not ack.exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ack.exists(), 'input stalled behind stdout backpressure')

    def test_sigterm_interrupts_normal_exit_waiting_for_stdout(self):
        with Wrapper('claude', ('--no-home',)) as session:
            session.read_until(BRAND_CLAUDE, timeout=3)
            session.send(b'/tail\r')
            time.sleep(0.5)
            self.assertIsNone(session.proc.poll())
            session.proc.terminate()
            self.assertEqual(session.proc.wait(timeout=3), 128 + signal.SIGTERM)

    def test_large_exit_output_survives_slow_consumer(self):
        with Wrapper('claude', ('--no-home',)) as session:
            session.read_until(BRAND_CLAUDE, timeout=3)
            session.send(b'/flood\r')
            time.sleep(0.3)
            deadline = time.monotonic() + 8
            while b':PAYLOAD_END' not in session.buf and time.monotonic() < deadline:
                ready, _, _ = select.select([session.master], [], [], 0.1)
                if ready:
                    try:
                        session.buf += os.read(session.master, 4096)
                    except OSError as exc:
                        if exc.errno != errno.EIO:
                            raise
                        break
                    time.sleep(0.003)
            self.assertTrue(b':PAYLOAD_END' in session.buf, 'exit output was truncated')
            payload = session.buf.split(b'PAYLOAD_BEGIN:', 1)[1].split(b':PAYLOAD_END', 1)[0]
            self.assertEqual(payload, b'z' * (512 * 1024))
            self.assertEqual(session.wait(), 0)

    def test_sigterm_with_unread_animation_output_does_not_hang(self):
        with Wrapper('claude', size=(111, 55)) as session:
            session.read_until(BRAND_CLAUDE, timeout=3)
            # Stop draining the outer PTY while the intro fills its output buffer.
            time.sleep(0.5)
            session.proc.terminate()
            self.assertEqual(session.proc.wait(timeout=3), 128 + signal.SIGTERM)
            attrs = termios.tcgetattr(session.master)
            self.assertTrue(attrs[3] & termios.ECHO)
            self.assertTrue(attrs[3] & termios.ICANON)

    def test_signal_during_startup_restores_terminal(self):
        with Wrapper('claude', ('--no-home',),
                     env_extra={'TMUX_PANE': '%1',
                                'FAKE_SILENT': '1'}) as session:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if not (termios.tcgetattr(session.master)[3] & termios.ECHO):
                    break
                time.sleep(0.01)
            else:
                self.fail('wrapper never entered raw mode')
            session.proc.send_signal(signal.SIGTERM)
            self.assertEqual(session.wait(timeout=5), 128 + signal.SIGTERM)
            attrs = termios.tcgetattr(session.master)
            self.assertTrue(attrs[3] & termios.ECHO)
            self.assertTrue(attrs[3] & termios.ICANON)


if __name__ == '__main__':
    unittest.main()
