"""Terminal I/O helpers, capability detection and hangup exceptions."""
import errno
import fcntl
import os
import struct
import subprocess
import sys
import termios
import time


def winsize(fd=1):
    try:
        packed = fcntl.ioctl(fd, termios.TIOCGWINSZ, b'\0' * 8)
        rows, cols, _, _ = struct.unpack('HHHH', packed)
        return packed, cols or 80, rows or 24
    except OSError:
        return struct.pack('HHHH', 24, 80, 0, 0), 80, 24


def name_tmux_window(name):
    """Give an auto-renamed tmux window the app name instead of python3.

    Tmux sees the PTY proxy, not the app inside it.  Respect a window the user
    named manually; only act while automatic-rename is on.
    """
    pane = os.environ.get('TMUX_PANE')
    if not pane:
        return
    try:
        state = subprocess.check_output(
            ['tmux', 'display-message', '-p', '-t', pane,
             '#{automatic-rename}'],
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=0.3, text=True).strip()
        if state != '1':
            return False
        subprocess.run(
            ['tmux', 'rename-window', '-t', pane, name],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=0.3, check=False)
        return True
    except Exception:
        return False


def restore_tmux_autorename(expected):
    """Put automatic-rename back only if the user did not rename the window."""
    pane = os.environ.get('TMUX_PANE')
    if not pane:
        return
    try:
        state = subprocess.check_output(
            ['tmux', 'display-message', '-p', '-t', pane,
             '#{automatic-rename}\t#{window_name}'],
            stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=0.3, text=True).strip()
        auto, _, name = state.partition('\t')
        if auto != '0' or name != expected:
            return
        subprocess.run(
            ['tmux', 'set-window-option', '-t', pane,
             'automatic-rename', 'on'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=0.3, check=False)
    except Exception:
        pass


class TmuxVisibility:
    """One bounded query at a time: True/False when complete, None while pending.

    Launcher owns this resource. Rendering never waits for the external process;
    close() is only called during launcher teardown, outside the transport loop.
    """
    TIMEOUT = 0.3

    def __init__(self):
        self.process = None
        self.deadline = None
        self.expired = False
        self.result = None

    def __call__(self):
        self.poll()
        if self.result is not None:
            result, self.result = self.result, None
            return result
        if self.process is None:
            pane = os.environ.get('TMUX_PANE')
            if not pane or not os.environ.get('TMUX'):
                return True
            self.deadline = time.monotonic() + self.TIMEOUT
            try:
                self.process = subprocess.Popen(
                    ['tmux', 'display-message', '-p', '-t', pane,
                     '#{session_attached} #{window_active} #{pane_active}'],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL)
                os.set_blocking(self.process.stdout.fileno(), False)
            except OSError:
                # If setup failed after spawn, keep polling/reaping that child.
                if self.process is not None:
                    self.process.kill()
                    self.expired = True
                return True
            self.expired = False
        return None

    def poll(self):
        """Launcher also polls when animation stops, so the child is always reaped."""
        proc = self.process
        if proc is None:
            return
        status = proc.poll()
        if status is None:
            if not self.expired and time.monotonic() >= self.deadline:
                proc.kill()
                self.expired = True
            return
        self.result = True
        try:
            if status or self.expired:
                return
            # Bounded/nonblocking even if a descendant inherited the pipe.
            state = os.read(proc.stdout.fileno(), 128).split()
            if len(state) != 3:
                return
            attached, window, active = map(int, state)
            self.result = attached > 0 and window == 1 and active == 1
        except (OSError, ValueError):
            pass
        finally:
            proc.stdout.close()
            self.process = None

    def close(self):
        proc, self.process = self.process, None
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            proc.stdout.close()


def detect_cell_ratio():
    """Use the terminal's pixel cell size when it reports one.

    The mark is rasterised in physical units; assuming a cell ratio makes it
    slightly wide or tall on fonts whose geometry differs.  TIOCGWINSZ is
    advisory and often zero (notably under tmux), so this never fails.
    """
    if os.environ.get('AGENT_THEME_CELL_RATIO'):
        return
    for fd in (1, 0):
        try:
            packed = fcntl.ioctl(fd, termios.TIOCGWINSZ, b'\0' * 8)
            rows, cols, xpix, ypix = struct.unpack('HHHH', packed)
        except OSError:
            continue
        if rows and cols and xpix and ypix:
            ratio = (ypix / rows) / (xpix / cols)
            if 1.2 <= ratio <= 4.0:
                os.environ['AGENT_THEME_CELL_RATIO'] = '%.4f' % ratio
                return


def _set_glyph_mode(mode):
    os.environ['AGENT_THEME_GLYPHS'] = mode
    try:
        from . import art
        art.reset_glyphs()
    except Exception:
        pass


def detect_glyphs():
    """Use octants when the real terminal is Ghostty; quadrants otherwise.

    Inside tmux, TERM_PROGRAM is 'tmux', so ask tmux which terminal is attached.
    Detection runs before the first art use; the art table is lazy and can be
    reset if the environment changes after an earlier import.
    """
    if os.environ.get('AGENT_THEME_GLYPHS'):
        return
    term = (os.environ.get('TERM_PROGRAM', '') + ' '
            + os.environ.get('TERM', '')).lower()
    if 'ghostty' in term:
        _set_glyph_mode('octant')
        return
    if os.environ.get('TMUX'):
        try:
            name = subprocess.check_output(
                ['tmux', 'display-message', '-p', '#{client_termname}'],
                stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=0.2, text=True).strip().lower()
            if 'ghostty' in name:
                _set_glyph_mode('octant')
        except Exception:
            pass


def detect_palette():
    if os.environ.get('AGENT_THEME_PALETTE'):
        return
    cfg = os.environ.get('COLORFGBG')
    if cfg:
        try:
            bg = int(cfg.split(';')[-1])
            # ANSI 0-6 and 8 are the dark backgrounds; 7 and the bright 9-15 are light.
            dark = 0 <= bg <= 6 or bg == 8
            light = bg == 7 or 9 <= bg <= 15
            if dark or light:
                os.environ['AGENT_THEME_PALETTE'] = 'light' if light else 'dark'
                return
        except Exception:
            pass
    if sys.platform == 'darwin':
        try:
            import plistlib
            path = os.path.expanduser('~/Library/Preferences/.GlobalPreferences.plist')
            with open(path, 'rb') as f:
                prefs = plistlib.load(f)
            style = prefs.get('AppleInterfaceStyle', 'Light')
            os.environ['AGENT_THEME_PALETTE'] = 'dark' if style == 'Dark' else 'light'
        except Exception:
            pass


class TerminalGone(Exception):
    pass


GONE = (errno.EIO, errno.ENXIO, errno.EBADF, errno.EPIPE)


def exit_code(status):
    """Shell exit status for a waitpid status, including 128+signal."""
    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)
    if os.WIFSIGNALED(status):
        return 128 + os.WTERMSIG(status)
    return 1
