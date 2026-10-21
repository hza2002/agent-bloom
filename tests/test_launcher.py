import errno
import fcntl
import os
import signal
import termios
import unittest
from unittest.mock import Mock, patch

from agent_theme.launcher import Launcher


class OutputQueueTests(unittest.TestCase):
    def make(self):
        launcher = object.__new__(Launcher)
        launcher.output = bytearray()
        launcher.overlay = None
        return launcher

    def test_partial_output_and_eagain_preserve_fifo(self):
        launcher = self.make()
        launcher._queue_output(b'first')
        launcher._queue_output(b'second')
        sent = bytearray()
        calls = 0
        def write(fd, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise BlockingIOError(errno.EAGAIN, 'full')
            n = min(3, len(data))
            sent.extend(data[:n])
            return n
        with patch('agent_theme.launcher.os.write', side_effect=write):
            while launcher.output:
                launcher._write_output()
        self.assertEqual(sent, b'firstsecond')

    def test_tick_does_not_advance_overlay_with_backlog(self):
        launcher = self.make()
        launcher.output.extend(b'pending')
        class Overlay:
            def tick(self):
                raise AssertionError('must not advance unpresented state')
        launcher.overlay = Overlay()
        launcher.tick()
        self.assertIsNotNone(launcher.overlay)

    def test_exit_flush_has_deadline(self):
        launcher = self.make()
        launcher.output.extend(b'pending')
        with patch('agent_theme.launcher.select.select', return_value=([], [], [])), \
             patch('agent_theme.launcher.time.monotonic', side_effect=[0, 0, 1]):
            launcher._flush_output(timeout=0.2)
        self.assertEqual(launcher.output, b'pending')

    def test_restore_restores_stdout_flags(self):
        launcher = self.make()
        launcher.cooked = None
        launcher.app_alt = False
        launcher.stdout_flags = 123
        with patch('agent_theme.launcher.fcntl.fcntl') as flags:
            launcher.restore()
        flags.assert_called_once_with(1, fcntl.F_SETFL, 123)

    def test_feed_failure_preserves_previously_held_bytes(self):
        launcher = self.make()
        class Replacer:
            def feed(self, data, flush=False):
                return data
        class Overlay:
            carry = b'\x1b]0;title'
            def feed(self, data):
                self.carry = b''
                raise ValueError('parser failed')
        launcher.replacer = Replacer()
        launcher.overlay = Overlay()
        launcher.alt_buf = b''
        launcher.app_alt = False
        self.assertEqual(launcher.send(b' rest\x07'), b'\x1b]0;title rest\x07')
        self.assertIsNone(launcher.overlay)

    def test_other_overlay_failures_also_release_held_bytes(self):
        for method in ('tick', 'note_input'):
            with self.subTest(method=method):
                launcher = self.make()
                launcher.overlay = Mock(carry=b'\x1b]0;unfinished')
                getattr(launcher.overlay, method).side_effect = ValueError('failed')
                getattr(launcher, method)(*(() if method == 'tick' else (b'input',)))
                self.assertEqual(launcher.output, b'\x1b]0;unfinished')
                self.assertIsNone(launcher.overlay)

    def test_signal_during_exit_drain_does_not_target_reaped_pid(self):
        launcher = self.make()
        launcher.status = 0
        launcher.events = [signal.SIGTERM]
        launcher.pid = 123
        with patch('agent_theme.launcher.os.kill') as kill:
            launcher.handle_events()
        kill.assert_not_called()
        self.assertEqual(launcher.term_signal, signal.SIGTERM)

    def test_alt_entry_at_start_of_large_chunk_is_detected(self):
        launcher = self.make()
        launcher.alt_buf = b''
        launcher.app_alt = False
        launcher._note_alt(b'\x1b[?1049h' + b'x' * 1000)
        self.assertTrue(launcher.app_alt)

    def test_suspend_restores_shared_stdout_flags_until_resume(self):
        launcher = self.make()
        launcher.cooked = []
        launcher.stdout_flags = os.O_RDWR
        launcher.master = 7
        launcher.pid = 123
        calls = []
        with patch('agent_theme.launcher.fcntl.fcntl', side_effect=lambda *args: calls.append(args)), \
             patch('agent_theme.launcher.fcntl.ioctl'), \
             patch('agent_theme.launcher.termios.tcsetattr'), \
             patch('agent_theme.launcher.tty.setraw') as raw, \
             patch('agent_theme.launcher.winsize', return_value=(b'packed', 111, 55)), \
             patch('agent_theme.launcher.os.kill', side_effect=lambda *args: calls.append(args)):
            launcher.suspend()
        stop = next(i for i, call in enumerate(calls) if call[-1] == signal.SIGSTOP)
        self.assertIn((1, fcntl.F_SETFL, os.O_RDWR), calls[:stop])
        self.assertIn((1, fcntl.F_SETFL, os.O_RDWR | os.O_NONBLOCK), calls[stop + 1:])
        raw.assert_called_once_with(0, termios.TCSANOW)

    def test_exit_drain_retries_interrupted_read(self):
        launcher = self.make()
        launcher.events = []
        launcher.term_deadline = None
        launcher.master = 7
        sent = bytearray()
        def write(fd, data):
            sent.extend(data)
            return len(data)
        with patch('agent_theme.launcher.os.read', side_effect=[InterruptedError(), b'payload', b'']), \
             patch('agent_theme.launcher.os.write', side_effect=write), \
             patch('agent_theme.launcher.select.select', return_value=([], [1], [])):
            launcher.send = lambda data, flush=False: data
            launcher.drain(8)
        self.assertEqual(sent, b'payload')

    def test_exit_cleanup_failure_releases_the_original_carry(self):
        launcher = self.make()
        launcher.events = []
        launcher.term_deadline = None
        launcher.master = 7
        class Overlay:
            carry = b'\x1b]0;unfinished'
            def finish(self):
                self.carry = b''
                raise ValueError('cleanup failed')
        launcher.overlay = Overlay()
        sent = bytearray()
        def write(fd, data):
            sent.extend(data)
            return len(data)
        with patch('agent_theme.launcher.os.read', return_value=b''), \
             patch('agent_theme.launcher.os.write', side_effect=write), \
             patch('agent_theme.launcher.select.select', return_value=([], [1], [])):
            launcher.drain(8)
        self.assertEqual(sent, b'\x1b]0;unfinished')
        self.assertIsNone(launcher.overlay)
