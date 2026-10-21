"""Terminal I/O helpers, capability detection and hangup exceptions."""
import errno
import fcntl
import os
import struct
import subprocess
import sys
import termios


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
