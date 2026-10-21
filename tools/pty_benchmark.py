#!/usr/bin/env python3
"""Compare direct and decorated synthetic TUI sessions through a drained POSIX PTY.

This measures transport, parsing and generated drawing bytes, not terminal/GPU
rendering. CPU is wait4 usage of the session leader and waited descendants;
app_cpu_seconds is independently recorded by the workload for cross-checking.
All session CPU figures include startup, settling and shutdown.
"""
import argparse
import errno
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import pty
import resource
import select
import shlex
import signal
import statistics
import struct
import subprocess
import sys
import tempfile
import termios
import time
import tty

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ('intro', 'home', 'output', 'paste')
READY = b'HB_READY!'
DONE = b'HB_DONE!'
OUTPUT_PREFIX = b'\x1b[4;1H'
OUTPUT_BLOCK = OUTPUT_PREFIX + b'z' * 100 + b'\x1b[K'


def write_all(fd, data):
    data = memoryview(data)
    while data:
        data = data[os.write(fd, data):]


def workload(args):
    """A raw-mode home screen, line acknowledgements and exact-length paste."""
    tty.setraw(0)
    title = (b'\x1b[39m\x1b[49m\x1b[1mClaude Code\x1b[22m'
             if args.app == 'claude' else b'>_ \x1b[1m\x1b[39;49mOpenAI Codex')
    write_all(1, b'\x1b[?1049h\x1b[H\x1b[2J\x1b[1;1H' + title
              + b'\x1b[2;1H~/benchmark\x1b[55;1H> ' + READY)
    pending = bytearray()
    while True:
        while b'\n' not in pending:
            if b'\x01' in pending:
                pending.remove(1)
                # Reuse prompt cells so acknowledgements never wrap/scroll
                # and accidentally stop the very animation being measured.
                write_all(1, b'\x1b[55;3HHB_PING!')
                continue
            data = os.read(0, 65536)
            if not data:
                return
            pending.extend(data)
        command, _, pending = pending.partition(b'\n')
        if command == b'exit':
            usage = resource.getrusage(resource.RUSAGE_SELF)
            Path(args.cpu_file).write_text(json.dumps({
                'user': usage.ru_utime, 'system': usage.ru_stime}))
            write_all(1, b'\x1b[?1049l' + DONE)
            return
        if command == b'output':
            block = OUTPUT_BLOCK
            count = args.bytes
            while count:
                piece = (block * 512)[:min(count, len(block) * 512)]
                write_all(1, piece)
                count -= len(piece)
            write_all(1, b'HB_OUTPUT!')
        elif command == b'paste':
            remaining = args.bytes
            digest = hashlib.sha256()
            while remaining:
                used = min(remaining, len(pending))
                if used:
                    digest.update(pending[:used])
                    del pending[:used]
                    remaining -= used
                else:
                    pending.extend(os.read(0, min(65536, remaining)))
            write_all(1, b'HB_PASTE:' + digest.hexdigest().encode() + b'!')


class Session:
    def __init__(self, args, mode, directory):
        self.master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 55, 111, 0, 0))
        self.cpu_file = Path(directory) / 'app-cpu.json'
        command = [sys.executable, str(Path(__file__).resolve()), '--workload',
                   '--app', args.app, '--bytes', str(args.bytes),
                   '--cpu-file', str(self.cpu_file)]
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('TMUX', 'AGENT_THEME_')) or key in (
                    'TERM_PROGRAM', 'COLORFGBG', 'LC_ALL', 'LC_MESSAGES'):
                env.pop(key, None)
        env.update(TERM='xterm-256color', LANG='C.UTF-8',
                   AGENT_THEME_LANG='zh-Hans', AGENT_THEME_GLYPHS='quadrant',
                   AGENT_THEME_CELL_RATIO='2.12', AGENT_THEME_PALETTE='dark',
                   PYTHONDONTWRITEBYTECODE='1')
        if mode == 'wrapped':
            binary = Path(directory) / args.app
            binary.write_text('#!/bin/sh\nexec ' + shlex.join(command) + '\n')
            binary.chmod(0o755)
            env['PATH'] = directory + os.pathsep + env.get('PATH', '')
            command = [sys.executable, str(ROOT / 'huawei-bloom'), args.app]
        self.start = time.monotonic()
        self.deadline = self.start + args.timeout
        # fork gives this process exclusive wait4 ownership and a controlling
        # terminal. It also lets us account for the wrapper's waited children.
        self.pid = os.fork()
        if self.pid == 0:
            try:
                os.close(self.master)
                os.setsid()
                fcntl.ioctl(slave, termios.TIOCSCTTY, 0)
                for fd in (0, 1, 2):
                    os.dup2(slave, fd)
                if slave > 2:
                    os.close(slave)
                os.execvpe(command[0], command, env)
            finally:
                os._exit(127)
        os.close(slave)
        os.set_blocking(self.master, False)
        self.tail = b''
        self.received = 0
        self.payload_z_bytes = 0
        self.reaped = False

    def pump(self, until=None, send=b'', duration=None):
        end = min(self.deadline, time.monotonic() + duration) if duration else self.deadline
        pending = memoryview(send)
        while True:
            if until is not None and until in self.tail and not pending:
                self.tail = self.tail.split(until, 1)[1]
                return
            left = end - time.monotonic()
            if left <= 0:
                if duration is not None and not pending:
                    return
                raise TimeoutError('PTY benchmark exceeded timeout waiting for %r' % until)
            readable, writable, _ = select.select(
                [self.master], [self.master] if pending else [], [], min(left, 0.1))
            if writable:
                try:
                    pending = pending[os.write(self.master, pending):]
                except BlockingIOError:
                    pass
            if readable:
                try:
                    data = os.read(self.master, 65536)
                except BlockingIOError:
                    continue
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    data = b''
                if not data:
                    raise RuntimeError('session ended before expected marker %r' % until)
                self.received += len(data)
                self.payload_z_bytes += data.count(b'z')
                self.tail = (self.tail + data)[-131072:]

    def finish(self):
        self.pump(DONE, b'exit\n')
        while time.monotonic() < self.deadline:
            pid, status, usage = os.wait4(self.pid, os.WNOHANG)
            if pid:
                self.reaped = True
                if os.waitstatus_to_exitcode(status):
                    raise RuntimeError('session exited with status %s' % status)
                cpu = json.loads(self.cpu_file.read_text())
                return {'wall_seconds': time.monotonic() - self.start,
                        'cpu_user_seconds': usage.ru_utime,
                        'cpu_system_seconds': usage.ru_stime,
                        'app_cpu_seconds': cpu['user'] + cpu['system'],
                        'terminal_bytes': self.received}
            # Drain trailing terminal restoration bytes while the child exits.
            readable, _, _ = select.select([self.master], [], [], 0.02)
            if readable:
                try:
                    self.received += len(os.read(self.master, 65536))
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
        raise TimeoutError('session did not exit')

    def close(self):
        if not self.reaped:
            # HUP on the outer PTY makes the wrapper clean up its inner PTY and
            # app process group. Never kill only the wrapper and orphan its app.
            os.close(self.master)
            self.master = None
            try:
                os.kill(self.pid, signal.SIGHUP)
            except ProcessLookupError:
                pass
            end = time.monotonic() + 5
            while time.monotonic() < end:
                pid, _, _ = os.wait4(self.pid, os.WNOHANG)
                if pid:
                    self.reaped = True
                    break
                time.sleep(0.02)
            if not self.reaped:
                os.kill(self.pid, signal.SIGKILL)
                os.wait4(self.pid, 0)
        if self.master is not None:
            os.close(self.master)


def measure(args, mode, scenario):
    with tempfile.TemporaryDirectory(prefix='hb-pty-benchmark-') as directory:
        session = Session(args, mode, directory)
        try:
            session.pump(READY)
            ready = time.monotonic() - session.start
            result = {'ready_seconds': ready}
            if scenario == 'home':
                session.pump(duration=args.intro_seconds)
                before = session.received
                session.pump(duration=args.seconds)
                result['idle_terminal_bytes'] = session.received - before
                result['idle_seconds'] = args.seconds
            elif scenario in ('output', 'paste'):
                if scenario == 'paste':
                    payload = b'z' * args.bytes
                    digest = hashlib.sha256(payload).hexdigest()
                    marker = b'HB_PASTE:' + digest.encode() + b'!'
                stamp = time.monotonic()
                if scenario == 'output':
                    session.pump(b'HB_OUTPUT!', b'output\n')
                    # Workload data uses z; neither its controls nor the chosen
                    # deterministic decoration contain that ASCII character.
                    expected = args.bytes // len(OUTPUT_BLOCK) * 100 + min(
                        max(args.bytes % len(OUTPUT_BLOCK) - len(OUTPUT_PREFIX), 0), 100)
                    if session.payload_z_bytes != expected:
                        raise RuntimeError('output payload byte count mismatch')
                    result['verified_output_z_bytes'] = expected
                else:
                    session.pump(marker, b'paste\n' + payload)
                    result['paste_sha256'] = digest
                elapsed = time.monotonic() - stamp
                result.update(transfer_seconds=elapsed,
                              payload_bytes=args.bytes,
                              payload_mib_per_second=args.bytes / elapsed / 1048576)
            latencies = []
            interval = args.intro_seconds / args.pings if scenario == 'intro' else .02
            for _ in range(args.pings):
                session.pump(duration=interval)
                stamp = time.monotonic()
                # A control byte traverses the full input path without typing
                # a prompt or submitting it, so animation remains active.
                session.pump(b'HB_PING!', b'\x01')
                latencies.append((time.monotonic() - stamp) * 1000)
            ordered = sorted(latencies)
            result['roundtrip_ms'] = {
                'samples': len(latencies), 'median': statistics.median(latencies),
                'p95': ordered[math.ceil(len(ordered) * .95) - 1], 'max': max(latencies)}
            result.update(session.finish())
            result['cpu_seconds'] = result['cpu_user_seconds'] + result['cpu_system_seconds']
            result['cpu_core_percent'] = 100 * result['cpu_seconds'] / result['wall_seconds']
            return result
        finally:
            session.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', choices=('claude', 'codex'), default='claude')
    parser.add_argument('--scenario', choices=SCENARIOS, action='append')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--seconds', type=float, default=2)
    parser.add_argument('--intro-seconds', type=float, default=3.5)
    parser.add_argument('--bytes', type=int, default=2 * 1024 * 1024)
    parser.add_argument('--pings', type=int, default=30)
    parser.add_argument('--timeout', type=float, default=30)
    parser.add_argument('--workload', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--cpu-file', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if min(args.runs, args.seconds, args.intro_seconds, args.bytes, args.pings, args.timeout) <= 0:
        parser.error('counts and durations must be positive')
    if args.workload:
        workload(args)
        return
    rows = []
    for run in range(args.runs):
        for scenario in args.scenario or SCENARIOS:
            # Alternate execution order to reduce systematic warm-cache bias.
            for mode in (('direct', 'wrapped') if run % 2 == 0 else ('wrapped', 'direct')):
                result = measure(args, mode, scenario)
                rows.append(dict(run=run + 1, mode=mode, scenario=scenario, **result))
    try:
        revision = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    source_hash = hashlib.sha256()
    sources = ([ROOT / 'huawei-bloom']
               + sorted((ROOT / 'agent_theme').glob('*.py'))
               + sorted((ROOT / 'agent_theme').glob('*.json')))
    for path in sources:
        source_hash.update(path.relative_to(ROOT).as_posix().encode() + b'\0')
        source_hash.update(path.read_bytes())
    print(json.dumps({
        'git_revision': revision, 'runtime_source_sha256': source_hash.hexdigest(),
        'schema': 1, 'python': platform.python_version(), 'platform': platform.platform(),
        'app_profile': args.app, 'geometry': {'columns': 111, 'rows': 55},
        'parameters': {key: getattr(args, key) for key in (
            'runs', 'seconds', 'intro_seconds', 'bytes', 'pings', 'timeout')},
        'scope': 'Synthetic app + drained PTY; no terminal emulator, tmux or GPU. '
                 'CPU includes session startup, settling and shutdown. wait4 includes '
                 'descendants only when the OS accounts for their waited usage; '
                 'app CPU is separately recorded. CPU core percent is one core, '
                 'not whole-machine utilization. Home latency is sampled after '
                 'settling; intro pings are spread across the intro interval. Pings are '
                 'synthetic control-byte roundtrips (no prompt submission), not '
                 'a real app editor or screen-refresh latency.',
        'results': rows}, indent=2))


if __name__ == '__main__':
    main()
