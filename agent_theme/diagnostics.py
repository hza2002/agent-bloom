"""Opt-in, bounded diagnostics. Never pass application text to this module."""
import fcntl
import os
import stat
import time

DEBUG = os.environ.get('AGENT_THEME_DEBUG')
MAX_BYTES = 256 * 1024


def debug(*parts):
    if not DEBUG:
        return
    line = ('%.3f pid=%d %s\n' %
            (time.time(), os.getpid(), ' '.join(map(str, parts)))).encode('utf-8')
    line = line[:2047] + b'\n' if len(line) > 2048 else line
    try:
        # Multiple panes may share a path. Do not wait for another writer.
        fd = os.open(DEBUG, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NONBLOCK, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if os.fstat(fd).st_size + len(line) > MAX_BYTES:
                os.ftruncate(fd, 0)
            os.write(fd, line)
        finally:
            os.close(fd)
    except OSError:
        pass  # Diagnostics must not interrupt the PTY proxy.
