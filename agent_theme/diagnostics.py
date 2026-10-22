"""Opt-in, bounded, multiprocess-safe diagnostics.

Events are structured `key=value` lines. Application output and user input must
never be passed here; callers log row numbers, flags and reasons only.

Python's standard `logging` package owns levels and formatting. The only custom
piece is a small handler because several wrapper processes may share one log
path: it appends one line under a non-blocking lock, rotates by size or age,
and never raises into the PTY proxy.
"""
import copy
import fcntl
import logging
import os
import stat
import time
import traceback
from datetime import datetime

DEBUG = os.environ.get('AGENT_THEME_DEBUG')
MAX_BYTES = 256 * 1024
MAX_AGE = 24 * 60 * 60
HEARTBEAT_SECONDS = 60.0
MAX_LINE = 4096

_CONTEXT = {}
_logger = logging.getLogger('agent_theme')
_logger.propagate = False


class _Formatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created).astimezone().isoformat(
            timespec='milliseconds')

    def format(self, record):
        context = getattr(record, 'ctx', '')
        message = record.getMessage()
        stamp = self.formatTime(record)
        return '%s %s %s' % (stamp, context, message) if context else '%s %s' % (
            stamp, message)


class _SharedFileHandler(logging.Handler):
    """Append-only handler for several processes sharing one bounded log."""

    def __init__(self, path, max_bytes=MAX_BYTES, max_age=MAX_AGE):
        super().__init__()
        self.path = path
        self.max_bytes = max_bytes
        self.max_age = max_age

    def emit(self, record):
        try:
            line = (self.format(record) + '\n').encode('utf-8')
        except Exception:
            return
        if len(line) > MAX_LINE:
            line = line[:MAX_LINE - 1] + b'\n'
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND
                         | os.O_NONBLOCK, 0o600)
        except OSError:
            return
        locked = False
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                return
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                # Another pane is writing; append without rotating rather than
                # losing the line. A single small O_APPEND write is atomic.
                pass
            st = os.fstat(fd)
            by_size = st.st_size + len(line) > self.max_bytes
            by_age = time.time() - st.st_mtime > self.max_age
            if locked and (by_size or by_age):
                os.ftruncate(fd, 0)
                reason = 'size' if by_size else 'age'
                os.write(fd, self._marker(record, reason))
            os.write(fd, line)
        except OSError:
            pass
        finally:
            if locked:
                try:
                    fcntl.flock(fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            os.close(fd)

    def _marker(self, record, reason):
        marker = copy.copy(record)
        marker.msg = 'event=log-start reason=' + reason
        marker.args = ()
        return (self.format(marker) + '\n').encode('utf-8')


class _ContextFilter(logging.Filter):
    def filter(self, record):
        record.ctx = context_string()
        return True


def context_string():
    parts = ['pid=%d' % os.getpid()]
    for key in ('app', 'size'):
        if _CONTEXT.get(key):
            parts.append('%s=%s' % (key, _CONTEXT[key]))
    for key, value in _CONTEXT.items():
        if key not in ('app', 'size'):
            parts.append('%s=%s' % (key, value))
    return ' '.join(parts)


def set_context(**fields):
    _CONTEXT.clear()
    _CONTEXT.update(fields)


def configure(path=None, max_bytes=MAX_BYTES, max_age=MAX_AGE):
    """(Re)configure from an explicit path or AGENT_THEME_DEBUG."""
    global DEBUG
    DEBUG = path if path is not None else os.environ.get('AGENT_THEME_DEBUG')
    for handler in list(_logger.handlers):
        _logger.removeHandler(handler)
        handler.close()
    if DEBUG:
        handler = _SharedFileHandler(DEBUG, max_bytes=max_bytes, max_age=max_age)
        handler.setFormatter(_Formatter())
        handler.addFilter(_ContextFilter())
        _logger.addHandler(handler)
        _logger.setLevel(logging.DEBUG)
    else:
        _logger.setLevel(logging.CRITICAL + 1)


def is_enabled():
    return bool(DEBUG)


def format_rows(rows):
    rows = sorted({int(row) for row in rows})
    if not rows:
        return '-'
    parts = []
    start = previous = rows[0]
    for row in rows[1:]:
        if row == previous + 1:
            previous = row
            continue
        parts.append(str(start) if start == previous else '%d-%d' % (start, previous))
        start = previous = row
    parts.append(str(start) if start == previous else '%d-%d' % (start, previous))
    return ','.join(parts)


def _format(value):
    if isinstance(value, bool):
        return '1' if value else '0'
    if value is None:
        return '-'
    if isinstance(value, (list, tuple, set, frozenset)):
        if all(isinstance(item, int) for item in value):
            return format_rows(value)
        return ','.join(str(item) for item in value) or '-'
    return str(value)


def event(name, **fields):
    if not DEBUG:
        return
    parts = ['event=' + name]
    for key, value in fields.items():
        parts.append('%s=%s' % (key, _format(value)))
    _logger.debug(' '.join(parts))


def exception(where, exc):
    """Log a sanitized stack: no exception message, no application data."""
    frames = traceback.extract_tb(exc.__traceback__)
    location = ';'.join('%s:%d:%s' % (os.path.basename(frame.filename),
                                      frame.lineno, frame.name)
                        for frame in frames)
    event('exception', where=where, type=type(exc).__name__, frames=location)


configure()
