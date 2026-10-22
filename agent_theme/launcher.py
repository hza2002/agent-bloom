"""PTY transport, terminal lifecycle and overlay scheduling."""
import errno
import fcntl
import os
import pty
import re
import select
import signal
import termios
import time
import tty

from . import __version__, diagnostics
from .replacer import Replacer
from .supervisor import supervise
from .terminal import (GONE, TerminalGone, detect_cell_ratio, detect_glyphs,
                       detect_palette, exit_code, name_tmux_window,
                       restore_tmux_autorename, winsize)


class Launcher:
    INPUT_LIMIT = 262144
    OUTPUT_LIMIT = 262144

    SIGNALS = (signal.SIGWINCH, signal.SIGCHLD, signal.SIGTERM, signal.SIGHUP,
               signal.SIGQUIT, signal.SIGINT)

    def __init__(self, profile, binary, argv, opts, strict=False, play_intro=True):
        self.profile = profile
        self.binary = binary
        self.argv = argv
        self.opts = opts
        self.strict = strict
        self.play_intro = play_intro
        self.events = []
        self.replacer = Replacer(profile, opts)
        self.cooked = None
        self.pending = bytearray()
        self.output = bytearray()
        self.stdout_flags = None
        self.status = None
        self.overlay = None
        self.art = None
        self.app_alt = False
        self.alt_buf = b''
        self.term_signal = None
        self.term_deadline = None
        self.palette_seen = False
        self.palette_buf = b''
        self.OSC11 = re.compile(
            rb'\x1b\]11;rgb:([0-9a-fA-F]{2,4})/([0-9a-fA-F]{2,4})/([0-9a-fA-F]{2,4})')

    def signal(self, signum, frame):
        self.events.append(signum)

    def _make_overlay(self, cols, rows):
        try:
            from . import art, intro
            from .animation import make_animated_overlay
            self.art = art
            base = self.profile.overlay_type()
            cls = make_animated_overlay(base, intro)
            pal = art.palette()
            ov = cls(cols, rows, art.BRANDS[self.profile.key],
                     in_alt=False, reveal=self.play_intro, pal=pal,
                     strict=self.strict, play_intro=self.play_intro)
            diagnostics.event('overlay', state='constructed',
                              intro=self.play_intro, strict=self.strict)
            return ov
        except Exception as exc:
            diagnostics.exception('_make_overlay', exc)
            return None

    def _kill_app_group(self):
        try:
            pgid = os.tcgetpgrp(self.master)
        except OSError:
            return
        if pgid > 0 and pgid != os.getpgrp():
            try:
                os.killpg(pgid, signal.SIGKILL)
            except OSError:
                pass

    def _hangup(self, code=129):
        try:
            os.kill(self.pid, signal.SIGHUP)
        except ProcessLookupError:
            self._kill_app_group()
            return code
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            try:
                pid, _ = os.waitpid(self.pid, os.WNOHANG)
            except ChildProcessError:
                self._kill_app_group()
                return code
            if pid:
                self._kill_app_group()
                return code
            time.sleep(0.05)
        # The app may ignore HUP; its foreground process group is only known
        # through the inner PTY, so kill it directly before the supervisor.
        self._kill_app_group()
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(self.pid, 0)
        except ChildProcessError:
            pass
        return code

    def _kill_child(self):
        if not hasattr(self, 'pid') or self.status is not None:
            return
        # Ask the supervisor to forward a hangup before resorting to SIGKILL, so
        # the app can restore its own terminal state and exit cleanly.
        self._hangup()

    def start(self):
        started = time.monotonic()
        # Block signals until the handlers exist. A termination signal during
        # tmux/detection setup must not bypass the terminal restore in finally.
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, self.SIGNALS)
        try:
            packed, cols, rows = winsize()
            self.cooked = termios.tcgetattr(0)
            for sig in self.SIGNALS:
                signal.signal(sig, self.signal)
        except BaseException:
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            raise
        signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
        try:
            tty.setraw(0, termios.TCSANOW)
            self.stdout_flags = fcntl.fcntl(1, fcntl.F_GETFL)
            fcntl.fcntl(1, fcntl.F_SETFL, self.stdout_flags | os.O_NONBLOCK)
            self.tmux_renamed = name_tmux_window(self.profile.key)
            self.tmux_name = self.profile.key
            detect_cell_ratio()
            detect_glyphs()
            detect_palette()
            from . import art as _art
            diagnostics.set_context(app=self.profile.key,
                                    size='%dx%d' % (cols, rows))
            diagnostics.event(
                'session', version=__version__, term=os.environ.get('TERM', ''),
                tmux=bool(os.environ.get('TMUX')),
                glyphs=_art.glyph_mode(),
                palette='light' if _art.palette() is _art.LIGHT else 'dark',
                intro=self.play_intro, strict=self.strict,
                opts=','.join(key for key in ('logo', 'header', 'title', 'home')
                              if self.opts.get(key)) or '-')
            if self.opts.get('home'):
                self.overlay = self._make_overlay(cols, rows)
            pid, master = pty.fork()
            if pid == 0:
                try:
                    supervise([self.binary] + self.argv)
                finally:
                    os._exit(127)
            self.pid, self.master = pid, master
            fcntl.ioctl(master, termios.TIOCSWINSZ, packed)
            fcntl.fcntl(master, fcntl.F_SETFL,
                        fcntl.fcntl(master, fcntl.F_GETFL) | os.O_NONBLOCK)
            wake_r, wake_w = os.pipe()
            for fd in (wake_r, wake_w):
                fcntl.fcntl(fd, fcntl.F_SETFL,
                            fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)
            signal.set_wakeup_fd(wake_w)
            return self.loop(wake_r)
        except TerminalGone:
            if hasattr(self, 'pid') and self.status is None:
                return self._hangup()
            return 129
        except BaseException as exc:
            diagnostics.exception('launcher', exc)
            self._kill_child()
            raise
        finally:
            signal.set_wakeup_fd(-1)
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            self.restore()
            if getattr(self, 'tmux_renamed', False):
                restore_tmux_autorename(getattr(self, 'tmux_name', ''))
            diagnostics.event(
                'exit', status=getattr(self, 'status', None),
                duration=round(time.monotonic() - started, 2))

    def _note_alt(self, data):
        scan = self.alt_buf + data
        self.alt_buf = scan[-32:]
        if any(seq in scan for seq in (b'\x1b[?1049h', b'\x1b[?1047h',
                                       b'\x1b[?47h')):
            self.app_alt = True

    def send(self, data, flush=False):
        self._note_alt(data)
        out = self.replacer.feed(data, flush=flush)
        if self.overlay:
            carry = getattr(self.overlay, 'carry', b'')
            try:
                out = self.overlay.feed(out)
            except Exception as exc:
                diagnostics.exception('send', exc)
                out = carry + out
                self.overlay = None
        return out

    def _queue_output(self, data):
        self.output.extend(data)

    def _disable_overlay(self):
        # A timer/input/resize failure can happen while the parser is holding
        # raw app bytes. Disabling decoration must not silently discard them.
        self._queue_output(getattr(self.overlay, 'carry', b''))
        self.overlay = None

    def _write_output(self):
        if not self.output:
            return
        try:
            n = os.write(1, self.output[:65536])
        except (BlockingIOError, InterruptedError):
            return
        except OSError as e:
            if e.errno in GONE:
                raise TerminalGone() from e
            raise
        if n:
            del self.output[:n]

    def _flush_output(self, timeout=0.2):
        deadline = time.monotonic() + timeout
        while self.output:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            try:
                _, ready, _ = select.select([], [1], [], left)
            except InterruptedError:
                continue
            if ready:
                self._write_output()

    def tick(self):
        if not self.overlay or self.output:
            return
        try:
            out = self.overlay.tick()
        except Exception as exc:
            diagnostics.exception('tick', exc)
            self._disable_overlay()
            return
        if out:
            self._queue_output(out)

    def note_input(self, data):
        if self.overlay:
            try:
                self.overlay.note_input(data)
            except Exception as exc:
                diagnostics.exception('note_input', exc)
                self._disable_overlay()

    def update_palette(self, data):
        if not self.overlay or self.palette_seen:
            return
        self.palette_buf = (self.palette_buf + data)[-512:]
        m = self.OSC11.search(self.palette_buf)
        if not m:
            return
        self.palette_seen = True
        try:
            bg = tuple(int(x[:2], 16) for x in m.groups())
            self.overlay.pal = self.art.palette_for(bg)
            scene = getattr(self.overlay, 'anim_scene', None)
            if scene is not None:
                scene.pal = self.overlay.pal
            # Repaint the static home with the corrected palette now rather
            # than waiting for the next clear or resize.
            if (getattr(self.overlay, 'alt', False)
                    and not getattr(self.overlay, 'sync', False)
                    and not getattr(self.overlay, 'carry', False)
                    and not getattr(self.overlay, 'disabled', False)):
                self.overlay.visible.clear()
                self.overlay.dirty = True
                body = self.overlay._frame_end()
                if body:
                    self._queue_output(b'\x1b[?2026h' + body + b'\x1b[?2026l')
        except Exception as exc:
            diagnostics.exception('update_palette', exc)
            self._disable_overlay()

    def loop(self, wake_r):
        while self.status is None:
            # A signal can arrive after the handlers are installed but before
            # the loop's first select. Drain that event before blocking.
            if self.events:
                self.handle_events()
                if self.status is not None:
                    break
            reads = [wake_r]
            if len(self.pending) < self.INPUT_LIMIT:
                reads.append(0)
            if len(self.output) < self.OUTPUT_LIMIT:
                reads.append(self.master)
            writes = ([self.master] if self.pending else []) + ([1] if self.output else [])
            if self.overlay and not self.output and hasattr(self.overlay, 'next_timeout'):
                try:
                    timeout = self.overlay.next_timeout()
                except Exception as exc:
                    diagnostics.exception('loop', exc)
                    self._disable_overlay()
                    timeout = None
            else:
                animating = bool(self.overlay and not self.output and self.overlay.animating())
                timeout = (1.0 / 60) if animating else None
            if self.replacer.buf:
                tail_timeout = 0.015
                timeout = tail_timeout if timeout is None else min(timeout, tail_timeout)
            if self.term_deadline is not None:
                left = max(0.0, self.term_deadline - time.monotonic())
                timeout = left if timeout is None else min(timeout, left)
            try:
                ready_r, ready_w, _ = select.select(reads, writes, [], timeout)
            except InterruptedError:
                ready_r, ready_w = [], []
            if wake_r in ready_r:
                try:
                    os.read(wake_r, 4096)
                except BlockingIOError:
                    pass
            self.handle_events()
            if self.status is not None:
                break
            if (self.term_deadline is not None
                    and time.monotonic() >= self.term_deadline):
                self.status = self._hangup(128 + self.term_signal)
                break
            if 0 in ready_r:
                try:
                    data = os.read(0, min(65536, self.INPUT_LIMIT - len(self.pending)))
                except BlockingIOError:
                    data = None
                except OSError as e:
                    if e.errno in GONE:
                        raise TerminalGone() from e
                    raise
                if data == b'':
                    # EOF on the outer terminal means the terminal/multiplexer
                    # is gone, not merely that input is paused.
                    raise TerminalGone()
                if data:
                    self.update_palette(data)
                    self.note_input(data)
                    self.pending.extend(data)
            if 1 in ready_w:
                self._write_output()
            if self.master in ready_w and self.pending:
                try:
                    n = os.write(self.master, self.pending)
                    del self.pending[:n]
                except BlockingIOError:
                    pass
                except OSError:
                    self.pending.clear()
            if self.master in ready_r:
                try:
                    data = os.read(self.master, 65536)
                except BlockingIOError:
                    data = None
                except OSError as e:
                    if e.errno != errno.EIO:
                        raise
                    data = b''
                if data == b'':
                    self.status = self.wait(block=True)
                    break
                if data:
                    self._queue_output(self.send(data))
            else:
                if not ready_r and not ready_w:
                    tail = self.send(b'', flush=True)
                else:
                    tail = b''
                if tail:
                    self._queue_output(tail)
            if self.overlay:
                try:
                    self.tick()
                except TerminalGone:
                    raise
                except Exception as exc:
                    diagnostics.exception('loop', exc)
                    self._disable_overlay()
        tail = self.send(b'', flush=True)
        if tail:
            self._queue_output(tail)
        self.drain(wake_r)
        return self.status

    def drain(self, wake_r):
        """Preserve normal exit output; only an explicit termination may time out."""
        reading = True
        finished = False
        while reading or self.output or not finished:
            if self.events:
                self.handle_events()
            if (self.term_deadline is not None
                    and time.monotonic() >= self.term_deadline):
                self.status = 128 + self.term_signal
                break
            if reading and len(self.output) < self.OUTPUT_LIMIT:
                try:
                    data = os.read(self.master, 65536)
                except InterruptedError:
                    continue
                except BlockingIOError:
                    data = b''
                except OSError as e:
                    if e.errno != errno.EIO:
                        raise
                    data = b''
                if data:
                    self._queue_output(self.send(data, flush=True))
                    continue
                reading = False
            if not reading and not finished:
                if self.overlay:
                    carry = self.overlay.carry
                    try:
                        tail = self.overlay.finish()
                    except Exception as exc:
                        diagnostics.exception('drain', exc)
                        tail = carry
                        self.overlay = None
                    self._queue_output(tail)
                finished = True
            if not self.output:
                continue
            timeout = None
            if self.term_deadline is not None:
                timeout = max(0, self.term_deadline - time.monotonic())
            try:
                ready_r, ready_w, _ = select.select([wake_r], [1], [], timeout)
            except InterruptedError:
                continue
            if wake_r in ready_r:
                try:
                    os.read(wake_r, 4096)
                except BlockingIOError:
                    pass
            if 1 in ready_w:
                self._write_output()

    def handle_events(self):
        events, self.events = self.events, []
        for sig in events:
            if sig == signal.SIGWINCH:
                packed, cols, rows = winsize()
                fcntl.ioctl(self.master, termios.TIOCSWINSZ, packed)
                if self.overlay:
                    try:
                        self.overlay.resize(cols, rows)
                    except Exception as exc:
                        diagnostics.exception('handle_events', exc)
                        self._disable_overlay()
            elif sig == signal.SIGCHLD:
                if self.status is not None:
                    continue
                status = self.wait()
                if status is not None:
                    self.status = status
            else:
                # Forward to the supervisor; it forwards to the app's process group.
                # Do not exit here: the app may need to restore its own screen, but
                # do not wait forever for an app that ignores the signal.
                self.term_signal = sig
                self.term_deadline = time.monotonic() + 2.0
                if self.status is not None:
                    continue  # The reaped supervisor's PID may have been reused.
                try:
                    os.kill(self.pid, sig)
                except ProcessLookupError:
                    pass

    def wait(self, block=False):
        try:
            pid, st = os.waitpid(self.pid, 0 if block else os.WNOHANG | os.WUNTRACED)
        except ChildProcessError:
            return 1
        if pid == 0:
            return None
        if os.WIFSTOPPED(st):
            self.suspend()
            return None
        return exit_code(st)

    def suspend(self):
        termios.tcsetattr(0, termios.TCSANOW, self.cooked)
        if self.stdout_flags is not None:
            fcntl.fcntl(1, fcntl.F_SETFL, self.stdout_flags)
        os.kill(os.getpid(), signal.SIGSTOP)
        tty.setraw(0, termios.TCSANOW)
        if self.stdout_flags is not None:
            fcntl.fcntl(1, fcntl.F_SETFL, self.stdout_flags | os.O_NONBLOCK)
        packed, cols, rows = winsize()
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, packed)
        if self.overlay:
            try:
                self.overlay.resize(cols, rows)
            except Exception as exc:
                diagnostics.exception('suspend', exc)
                self._disable_overlay()
        os.kill(self.pid, signal.SIGCONT)

    def restore(self):
        in_alt = self.app_alt or bool(self.overlay is not None
                                      and getattr(self.overlay, 'alt', False))
        if self.cooked is not None:
            try:
                termios.tcsetattr(0, termios.TCSANOW, self.cooked)
            except (OSError, termios.error):
                pass
        if in_alt:
            try:
                # A forced exit may abandon an incomplete control sequence.
                # Normal shutdown drains all queued bytes before reaching here.
                self.output.clear()
                self._queue_output(b'\x18\x1b[0m\x1b[<u\x1b[?2004l\x1b[?1004l\x1b[?2031l'
                             b'\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l'
                             b'\x1b[?2026l\x1b[?7h\x1b[?25h\x1b[?1049l')
                self._flush_output()
            except (OSError, TerminalGone):
                pass
        if self.stdout_flags is not None:
            try:
                fcntl.fcntl(1, fcntl.F_SETFL, self.stdout_flags)
            except OSError:
                pass
