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

from .replacer import Replacer
from .supervisor import supervise
from .terminal import (GONE, TerminalGone, detect_cell_ratio, detect_glyphs,
                       detect_palette, exit_code, name_tmux_window,
                       restore_tmux_autorename, winsize, write_all)


class Launcher:
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
        self.pending = b''
        self.stdin_open = True
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
            cls = make_animated_overlay(base, intro, top_hint=self.profile.home_top)
            pal = art.palette()
            ov = cls(cols, rows, art.BRANDS[self.profile.key],
                     in_alt=False, reveal=self.play_intro, pal=pal,
                     strict=self.strict, play_intro=self.play_intro)
            return ov
        except Exception:
            if os.environ.get('AGENT_THEME_DEBUG'):
                import traceback
                traceback.print_exc()
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
        if not hasattr(self, 'pid'):
            return
        # Ask the supervisor to forward a hangup before resorting to SIGKILL, so
        # the app can restore its own terminal state and exit cleanly.
        self._hangup()

    def start(self):
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
            tty.setraw(0)
            self.tmux_renamed = name_tmux_window(self.profile.key)
            self.tmux_name = self.profile.key
            detect_cell_ratio()
            detect_glyphs()
            detect_palette()
            if self.opts.get('home'):
                self.overlay = self._make_overlay(cols, rows)
                if self.overlay and self.profile.startup_args:
                    self.argv = list(self.profile.startup_args) + self.argv
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
            if hasattr(self, 'pid'):
                return self._hangup()
            return 129
        except BaseException:
            self._kill_child()
            raise
        finally:
            signal.set_wakeup_fd(-1)
            signal.pthread_sigmask(signal.SIG_SETMASK, old_mask)
            self.restore()
            if getattr(self, 'tmux_renamed', False):
                restore_tmux_autorename(getattr(self, 'tmux_name', ''))

    def _note_alt(self, data):
        scan = (self.alt_buf + data)[-32:]
        self.alt_buf = scan
        if any(seq in scan for seq in (b'\x1b[?1049h', b'\x1b[?1047h',
                                       b'\x1b[?47h')):
            self.app_alt = True

    def send(self, data, flush=False):
        self._note_alt(data)
        out = self.replacer.feed(data, flush=flush)
        if self.overlay:
            try:
                out = self.overlay.feed(out)
            except Exception:
                if os.environ.get('AGENT_THEME_DEBUG'):
                    import traceback
                    traceback.print_exc()
                self.overlay = None
        return out

    def tick(self):
        if not self.overlay:
            return
        try:
            out = self.overlay.tick()
        except Exception:
            if os.environ.get('AGENT_THEME_DEBUG'):
                import traceback
                traceback.print_exc()
            self.overlay = None
            return
        if out:
            try:
                write_all(1, out)
            except OSError as e:
                if e.errno not in GONE:
                    raise
                raise TerminalGone() from e

    def note_input(self, data):
        if self.overlay:
            try:
                self.overlay.note_input(data)
            except Exception:
                self.overlay = None

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
                    write_all(1, b'\x1b[?2026h' + body + b'\x1b[?2026l')
        except Exception:
            self.overlay = None

    def loop(self, wake_r):
        while self.status is None:
            reads = [self.master, wake_r] + ([0] if self.stdin_open else [])
            writes = [self.master] if self.pending else []
            if self.overlay and hasattr(self.overlay, 'next_timeout'):
                try:
                    timeout = self.overlay.next_timeout()
                except Exception:
                    self.overlay = None
                    timeout = None
            else:
                animating = bool(self.overlay and self.overlay.animating())
                timeout = (1.0 / 40) if animating else None
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
                    data = os.read(0, 65536)
                except OSError as e:
                    if e.errno in GONE:
                        raise TerminalGone() from e
                    raise
                if not data:
                    # EOF on the outer terminal means the terminal/multiplexer
                    # is gone, not merely that input is paused.
                    raise TerminalGone()
                self.update_palette(data)
                self.note_input(data)
                self.pending += data
            if self.master in ready_w and self.pending:
                try:
                    n = os.write(self.master, self.pending)
                    self.pending = self.pending[n:]
                except BlockingIOError:
                    pass
                except OSError:
                    self.pending = b''
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
                    try:
                        write_all(1, self.send(data))
                    except OSError as e:
                        if e.errno not in GONE:
                            raise
                        raise TerminalGone() from e
            else:
                if not ready_r and not ready_w:
                    tail = self.send(b'', flush=True)
                else:
                    tail = b''
                if tail:
                    try:
                        write_all(1, tail)
                    except OSError as e:
                        if e.errno not in GONE:
                            raise
                        raise TerminalGone() from e
            if self.overlay:
                try:
                    self.tick()
                except TerminalGone:
                    raise
                except Exception:
                    self.overlay = None
        tail = self.send(b'', flush=True)
        if tail:
            try:
                write_all(1, tail)
            except OSError:
                pass
        self.drain()
        return self.status

    def drain(self):
        deadline = time.monotonic() + 0.2
        while time.monotonic() < deadline:
            try:
                data = os.read(self.master, 65536)
            except (BlockingIOError, OSError):
                break
            if not data:
                break
            try:
                write_all(1, self.send(data, flush=True))
            except (OSError, TerminalGone):
                break

    def handle_events(self):
        events, self.events = self.events, []
        for sig in events:
            if sig == signal.SIGWINCH:
                packed, cols, rows = winsize()
                fcntl.ioctl(self.master, termios.TIOCSWINSZ, packed)
                if self.overlay:
                    try:
                        self.overlay.resize(cols, rows)
                    except Exception:
                        self.overlay = None
            elif sig == signal.SIGCHLD:
                status = self.wait()
                if status is not None:
                    self.status = status
            else:
                # Forward to the supervisor; it forwards to the app's process group.
                # Do not exit here: the app may need to restore its own screen, but
                # do not wait forever for an app that ignores the signal.
                self.term_signal = sig
                self.term_deadline = time.monotonic() + 2.0
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
        termios.tcsetattr(0, termios.TCSADRAIN, self.cooked)
        os.kill(os.getpid(), signal.SIGSTOP)
        tty.setraw(0)
        packed, cols, rows = winsize()
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, packed)
        if self.overlay:
            try:
                self.overlay.resize(cols, rows)
            except Exception:
                self.overlay = None
        os.kill(self.pid, signal.SIGCONT)

    def restore(self):
        in_alt = self.app_alt or bool(self.overlay is not None
                                      and getattr(self.overlay, 'alt', False))
        if self.cooked is not None:
            try:
                termios.tcsetattr(0, termios.TCSADRAIN, self.cooked)
            except (OSError, termios.error):
                pass
        if in_alt:
            try:
                write_all(1, b'\x1b[0m\x1b[<u\x1b[?2004l\x1b[?1004l\x1b[?2031l'
                             b'\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l'
                             b'\x1b[?2026l\x1b[?7h\x1b[?25h\x1b[?1049l')
            except (OSError, TerminalGone):
                pass
