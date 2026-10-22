"""Home page drawn into the blank middle of a full-screen (alternate-screen) TUI.

Codex (ratatui) and Claude Code's fullscreen renderer only repaint cells they believe changed,
so cells they think are blank keep whatever we draw there. The overlay follows the app's
output to know which rows it uses, draws the lockup only on rows that are blank to it, and
wipes an art row right before the app writes into it. Inserted sequences are wrapped in
DECSC/DECRC so the app's cursor and colours are untouched, and placed inside its own
synchronized-update frames.

Unmodelled transient changes (scrolling, insert/delete line) wipe the art and pause the
overlay until a full clear. Unsupported persistent modes and app-owned cursor saves remain
isolated across clears. Apps that stay on the main screen (inline renderers) only get the
header branding.

The home is the best blank row band between the app's used rows. The mark,
wordmark and small text are selected as complete groups. App-specific overlay
subclasses remain only as extension points.
"""
import re
import time
import unicodedata
from functools import lru_cache

from . import art, diagnostics
from .input import InputObserver

TEXT = re.compile(rb'[^\x00-\x1f\x7f]+')
REVEAL_SECONDS = 1.1
ASCII_CONTENT = bytes(0 if b == 0x20 else 1 for b in range(256))
ASCII_FILLED = bytes(1 for _ in range(256))
# Bound undecoded OSC/DCS/CSI data, including streams that never send a terminator.
MAX_CARRY = 65536

# CSI selectors are (private prefix, intermediate bytes, final byte).
# Observe effects we understand; syntax alone says nothing about their safety.
# Unhandled extensions pass through to the terminal without acquiring modes.
CSI_CELL_EDITS = frozenset((b'', b'$', final) for final in b'rtvxz{')
CSI_MODE_EDITS = frozenset({
    (b'', b'!', ord('p')),  # DECSTR: soft reset (includes saved state)
    (b'', b'"', ord('p')),  # DECSCL: terminal conformance/reset
    (b'', b'"', ord('q')),  # DECSCA: character protection
    (b'', b'$', ord('|')),  # DECSCPP: columns per page
    (b'', b'*', ord('|')),  # DECSNLS: lines per page
    (b'', b'$', ord('}')),  # DECSASD: active display
    (b'', b'$', ord('~')),  # DECSSDT: status display
    (b'', b'#', ord('{')),  # XTPUSHSGR: shared rendition stack
    (b'', b'#', ord('}')),  # XTPOPSGR
})


@lru_cache(maxsize=4096)
def cwidth(ch):
    o = ord(ch)
    if o < 0x300:
        return 1
    if unicodedata.combining(ch) or 0x200b <= o <= 0x200f or 0xfe00 <= o <= 0xfe0f or 0xe0100 <= o <= 0xe01ef:
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1


class Overlay:
    CLEAR_COMMANDS = ('/clear', '/reset', '/new')

    def __init__(self, cols, rows, brand, in_alt=False, reveal=False, pal=None, strict=False):
        self.brand = brand
        self.pal = pal or art.palette()
        self.carry = b''
        self.pending_wrap = False
        # Input gives conservative session hints; screen clears only reset occupancy.
        self.input = InputObserver(self.CLEAR_COMMANDS)
        self.typed = ''
        self._in_output = False
        self.submitted = strict
        self.intro_owns_home = False
        self.fresh_pending = None
        self.alt = in_alt
        self.entered_alt = in_alt
        self.sync = False
        self.dirty = False
        self.disabled = False
        self.passthrough = False
        # Unsupported text can only be retired at the next explicit cursor
        # boundary; erasing inside an open grapheme would split the app text.
        self.retire_all = False
        # A wrong width model quarantines decoration until a fresh surface and
        # an absolute cursor position make occupancy trustworthy again.
        self.quarantine = False
        self.quarantine_cleared = False
        self.last_quarantine = None
        # These modes outlive ED2, resize and alternate-screen switches.
        self.unsafe_modes = set()
        self.bg = False
        self.reverse = False
        self.saved = (0, 0)
        self.reveal_from = None
        self.want_reveal = reveal
        # While the intro is still on screen nothing we paint is seen yet: hold the fade-in.
        self.reveal_hold = reveal
        self.dynamic_rows = set()
        self.rows_used = set()
        self.band_run = None
        self.last_band_log = None
        self.last_frame_log = None
        self.last_touch = None
        self.last_surface = None
        self.resize(cols, rows)

    # ------------------------------------------------------------- per-app hooks
    def note_input(self, data):
        """Observe input without interpreting pasted text as editor commands."""
        submitted, reset = self.input.feed(data)
        self.typed = self.input.typed
        if submitted:
            self.submitted = True
            self.fresh_pending = time.monotonic() if reset else None
            diagnostics.event('input',
                              kind='reset-candidate' if reset else 'submit')

    def is_fresh(self):
        """An unconfirmed reset candidate, never permission to draw by itself."""
        return (self.fresh_pending is not None
                and time.monotonic() - self.fresh_pending < 10)

    def _band(self):
        """Best blank run and its top row, or None when no complete group fits."""
        result = art.analyze_band(self.brand, self.cols, self.rows, self.count)
        lock = result.lock
        self.band_run = ((result.start, result.end) if lock is not None else None)
        if diagnostics.DEBUG:
            signature = (result.reason, result.start, result.end,
                         len(result.used), result.runs, result.candidates,
                         None if lock is None else
                         (lock.show_mark, lock.show_word, lock.show_small,
                          lock.word_rows, lock.height, lock.width))
            if signature != self.last_band_log:
                self.last_band_log = signature
                flags = '-' if lock is None else ','.join(
                    name for name, shown in (('mark', lock.show_mark),
                                             ('word', lock.show_word),
                                             ('small', lock.show_small)) if shown)
                diagnostics.event(
                    'band', decision=result.reason,
                    band=('%d-%d' % (result.start, result.end)) if lock else '-',
                    used=tuple(result.used), runs=result.runs,
                    candidates=result.candidates, lock=flags,
                    word_rows=None if lock is None else lock.word_rows)
        if lock is None:
            return None
        return lock, art.place(lock, result.start, result.end), (
            result.start, result.end)

    def _new_screen(self):
        """The app cleared the whole screen."""
        self._log_surface('clear')
        self.disabled = False
        if self.quarantine:
            self.quarantine_cleared = True
            # Stay unknown until an absolute cursor re-establishes position.
            self.known = False
            self._log_quarantine('cleared', 'clear')
        self._invalidate_frame()

    def _session_reset(self):
        """A reset candidate now has an application update with a home layout."""
        self._log_surface('session-reset')
        self.submitted = False
        self.fresh_pending = None

    def _saw_text(self, run):
        """A run of printable bytes is about to be drawn at (cy, cx)."""

    # ----------------------------------------------------------------- geometry
    def _invalidate_frame(self):
        """Hook for renderers caching the terminal's last painted frame."""

    def _reset_surface(self):
        """Forget decoration ownership when the terminal surface changes."""
        self.visible = set()
        self.anchor = None
        self.rows_used.clear()
        self.dynamic_rows.clear()
        self._invalidate_frame()

    def resize(self, cols, rows):
        self._log_surface('resize', size='%dx%d' % (cols, rows))
        self.pending_wrap = False
        # Terminal graphemes can continue across reads and SGR/sync controls.
        # Only explicit cursor movement establishes a new insertion boundary.
        self.text_tail = False
        self.cols, self.rows = cols, rows
        self.grid = [bytearray(cols) for _ in range(rows)]
        self.count = [0] * rows
        self.cx = self.cy = 0
        self.known = False
        self.disabled = False
        self._reset_surface()

    def _clear_rows(self, start, stop, filled=False):
        for r in range(max(0, start), min(self.rows, stop)):
            self.grid[r][:] = (b'\x01' * self.cols if filled else bytes(self.cols))
            self.count[r] = self.cols if filled else 0

    def _set_span(self, r, c0, c1, filled):
        if not 0 <= r < self.rows:
            return
        c0, c1 = max(0, c0), min(self.cols, c1)
        if c1 <= c0:
            return
        row = self.grid[r]
        before = row.count(1, c0, c1)
        row[c0:c1] = (b'\x01' if filled else b'\x00') * (c1 - c0)
        self.count[r] += (c1 - c0 if filled else 0) - before

    # ------------------------------------------------------------------ painting
    def _wrap(self, body):
        if self.pending_wrap or self.text_tail:
            return b''
        return ('\x1b7\x1b[0m' + body + '\x1b[0m\x1b8').encode('utf-8') if body else b''

    def _erase(self, rows):
        if self.pending_wrap or self.text_tail:
            return b''
        rows = sorted(r for r in rows if r in self.visible)
        if not rows:
            return b''
        self.visible.difference_update(rows)
        self._invalidate_frame()
        return self._wrap(''.join('\x1b[%d;1H\x1b[2K' % (r + 1) for r in rows))

    def _erase_all(self):
        # Never erase a row the app already owns: forget those rows without
        # emitting a clear, and erase only the still-blank owned rows.
        used = [r for r in self.visible if self.count[r]]
        if used:
            self.visible.difference_update(used)
            self._invalidate_frame()
        return self._erase(list(self.visible))

    def _reveal(self):
        if not self.want_reveal:
            return 1.0
        if self.reveal_from is None:
            return 0.0
        return min(1.0, (time.monotonic() - self.reveal_from) / REVEAL_SECONDS)

    def release(self):
        """The intro has handed over: start the slogan fade-in if the home is up."""
        self.reveal_hold = False
        if self.want_reveal and self.visible and self.reveal_from is None:
            self.reveal_from = time.monotonic()

    def _paint(self, rows):
        if self.pending_wrap or self.text_tail or not rows or not self.anchor:
            return b''
        lock, top, _ = self.anchor
        content = art.home_rows(lock, top, self._reveal(), self.pal)
        self._invalidate_frame()
        parts = []
        for r in sorted(rows):
            parts.append('\x1b[%d;1H\x1b[2K' % (r + 1))
            for col, cells in content.get(r, []):
                parts.append('\x1b[%d;%dH' % (r + 1, col + 1))
                parts.append(art.render_run(cells))
            self.visible.add(r)
        return self._wrap(''.join(parts))

    def _set_anchor(self, lock, top, run=None):
        self.anchor = (lock, top, (self.cols, self.rows))
        if run is not None:
            self.band_run = run
        self.rows_used = set(art.home_rows(lock, top, 1.0, self.pal))
        self.dynamic_rows = ({r for r in self.rows_used
                              if r >= top + lock.slogan_top}
                             if lock.show_small else set())

    def _band_label(self):
        return '%d-%d' % self.band_run if self.band_run else '-'

    def _quarantine_boundary(self, seq):
        """Recover only after a fresh surface followed by a known cursor."""
        if seq == b'\x1bc':
            self._clear_rows(0, self.rows)
            self.cx = self.cy = 0
            self.disabled = False
            self.unsafe_modes.clear()
            self.alt = False
            self.entered_alt = False
            self.quarantine_cleared = True
            self._log_quarantine('cleared', 'hard-reset')
        if not self.quarantine_cleared:
            return
        absolute = re.fullmatch(rb'\x1b\[[0-9;]*[Hf]', seq) is not None
        if not (absolute or seq == b'\x1bc'):
            return
        if self.unsafe_modes or self.disabled:
            self._log_quarantine('waiting', 'unsafe-mode')
            return
        self.quarantine = False
        self.quarantine_cleared = False
        self.passthrough = False
        self.retire_all = False
        self.known = True
        self._log_quarantine('recovered',
                             'hard-reset' if seq == b'\x1bc' else 'clear+cursor')

    def _log_quarantine(self, state, reason, **fields):
        if not diagnostics.DEBUG:
            return
        signature = (state, reason,
                     tuple(sorted((key, str(value))
                                  for key, value in fields.items())))
        if signature == self.last_quarantine:
            return
        self.last_quarantine = signature
        diagnostics.event('quarantine', state=state, reason=reason, **fields)

    def _log_surface(self, kind, **fields):
        if not diagnostics.DEBUG:
            return
        signature = (kind, tuple(sorted((key, str(value))
                                       for key, value in fields.items())))
        if signature == self.last_surface:
            return
        self.last_surface = signature
        diagnostics.event('surface', kind=kind, **fields)

    def _log_frame(self, action, reason, **fields):
        if not diagnostics.DEBUG:
            return
        signature = (action, reason, fields.get('anchor'), fields.get('band'),
                     fields.get('visible'), fields.get('used'),
                     fields.get('old'), fields.get('new'))
        if signature == self.last_frame_log:
            return
        self.last_frame_log = signature
        diagnostics.event('frame', action=action, reason=reason, **fields)

    def _frame_end(self):
        """Bring the art in line with the screen the app just finished drawing."""
        if self.pending_wrap or self.text_tail or self.passthrough or self.disabled or not self.alt or self.unsafe_modes:
            return b''
        if not self.known:
            self._log_frame('erase', 'unknown-screen')
            return self._erase_all()
        if self.submitted and not self.is_fresh():
            self._log_frame('erase', 'submitted')
            return self._erase_all()

        band = None
        if self.submitted:
            # A timer tick cannot confirm a /clear; only an output update plus a
            # usable home band can.
            if not self._in_output:
                self._log_frame('erase', 'timer-reset-unconfirmed')
                return self._erase_all()
            band = self._band()
            if band is None:
                self._log_frame('erase', 'no-band')
                return self._erase_all()
            self._session_reset()

        # Minimum movement: keep the art while every row it owns is still blank.
        if (self.anchor is not None and self.rows_used
                and self.anchor[2] == (self.cols, self.rows)
                and all(self.count[r] == 0 for r in self.rows_used)):
            anchor_top = self.anchor[1]
            if self.intro_owns_home:
                self._log_frame('defer', 'intro', anchor=anchor_top,
                                band=self._band_label(),
                                visible=len(self.visible),
                                used=len(self.rows_used))
                return b''
            self._log_frame('keep', 'art-blank', anchor=anchor_top,
                            band=self._band_label(),
                            visible=len(self.visible),
                            used=len(self.rows_used))
            want = set(self.rows_used)
            out = self._erase(self.visible - want)
            missing = want - self.visible
            if missing and self.want_reveal and self.reveal_from is None and not self.reveal_hold:
                self.reveal_from = time.monotonic()
            return out + self._paint(missing)

        if band is None:
            band = self._band()
        if band is None:
            self._log_frame('erase', 'no-band', band='-',
                            used=tuple(r for r in range(self.rows)
                                       if self.count[r]))
            self.anchor = None
            return self._erase_all()
        lock, top, (start, end) = band

        out = b''
        old_top = self.anchor[1] if self.anchor is not None else None
        if self.anchor is not None:
            # The app reclaimed one of our rows, or the surface changed.
            self.anchor = None
            out += self._erase_all()
        self._set_anchor(lock, top, (start, end))
        if self.intro_owns_home:
            # The Bloom owns the home area until its one-shot finishes. The next
            # tick moves it to the new anchor at the same elapsed time.
            self._log_frame('reanchor', 'intro', old=old_top, new=top,
                            band=self._band_label(), visible=len(self.visible))
            return out
        self._log_frame('paint', 'home', old=old_top, new=top,
                        band=self._band_label(), visible=len(self.visible),
                        used=len(self.rows_used))
        want = set(self.rows_used)
        out += self._erase(self.visible - want)
        missing = want - self.visible
        if missing and self.want_reveal and self.reveal_from is None and not self.reveal_hold:
            self.reveal_from = time.monotonic()
        return out + self._paint(missing)

    def tick(self):
        """Timer-driven repaint for the slogan fade-in. Returns bytes to write (may be empty)."""
        if (self.pending_wrap or self.text_tail or self.passthrough or self.disabled or not self.known or not self.alt
                or self.unsafe_modes or self.reveal_from is None
                or self.sync or self.carry or not self.visible):
            return b''
        reveal = self._reveal()
        rows = self.visible & self.dynamic_rows
        out = self._paint(rows)
        if reveal >= 1.0:
            self.reveal_from = None
            self.want_reveal = False
        return b'\x1b[?2026h' + out + b'\x1b[?2026l' if out else b''

    def animating(self):
        return self.reveal_from is not None and bool(self.visible)

    # ------------------------------------------------------------------- parsing
    def finish(self):
        """End decoration and release raw bytes still waiting for a terminator."""
        if self.retire_all:
            # The app is exiting; there is no open boundary to protect.
            self.pending_wrap = self.text_tail = False
            self.retire_all = False
        out = self._erase_all() if self.alt and not self.unsafe_modes else b''
        out += self.carry
        self.carry = b''
        self.passthrough = True
        self.known = False
        return out

    def feed(self, chunk):
        """App output in, terminal output out (with the overlay woven in)."""
        if self.passthrough and not self.retire_all and not self.quarantine:
            # Flush a sequence carried before passthrough began; never drop it.
            out = self.carry + chunk
            self.carry = b''
            return out
        data = self.carry + chunk
        self.carry = b''
        self._in_output = True
        try:
            out = self._parse(data)
            if not self.sync and self.dirty:
                extra = self._frame_end()
                self.dirty = False
                if extra:
                    out += b'\x1b[?2026h' + extra + b'\x1b[?2026l'
            return out
        finally:
            self._in_output = False

    def _parse(self, data):
        out = []
        emit = 0
        i = 0
        n = len(data)
        while i < n:
            b = data[i]
            if b == 0x1b:
                j = self._seq_end(data, i)
                if j < 0:
                    out.append(data[emit:i])
                    if n - i > MAX_CARRY:
                        # Nothing from the incomplete sequence has reached the
                        # terminal yet, so erase before releasing its raw bytes.
                        out.append(self._erase_all())
                        out.append(data[i:])
                        self.passthrough = True
                        diagnostics.event('unsupported',
                                          kind='control-sequence-too-long')
                        self.known = False
                    else:
                        self.carry = data[i:]
                    return b''.join(out)
                seq = data[i:j]
                pre = self._escape(seq)
                # Explicit cursor positioning resolves delayed autowrap; SGR,
                # erase and sync controls do not. Never insert a save/restore
                # between the final column and the app resolving that state.
                if re.fullmatch(rb'\x1b\[[0-9;]*[HfABCDEFG`ade]', seq) or seq == b'\x1bc':
                    self.pending_wrap = False
                    self.dirty |= self.text_tail
                    self.text_tail = False
                    if self.retire_all:
                        # The boundary is closed; safe to retire now.
                        self.retire_all = False
                        self.passthrough = True
                        pre = self._erase_all() + pre
                    if self.quarantine:
                        self._quarantine_boundary(seq)
                    self.cx = min(self.cx, self.cols - 1)
                elif self.retire_all or self.quarantine:
                    # Observation has stopped; pass the control through.
                    pre = b''
                if pre:
                    out.append(data[emit:i])
                    out.append(pre)
                    emit = i
                i = j
            elif b < 0x20 or b == 0x7f:
                pre = self._control(b)
                if b in (0x0d, 0x08):
                    self.pending_wrap = False
                    self.dirty |= self.text_tail
                    self.text_tail = False
                if pre:
                    out.append(data[emit:i])
                    out.append(pre)
                    emit = i
                i += 1
            else:
                m = TEXT.match(data, i)
                j = m.end()
                run = data[i:j]
                if j == n and run[-1] >= 0x80:
                    # Possibly a split UTF-8 sequence: keep the incomplete tail for next time.
                    k = len(run)
                    back = 0
                    while back < 4 and k - back - 1 >= 0 and 0x80 <= run[k - back - 1] < 0xc0:
                        back += 1
                    lead = run[k - back - 1] if k - back - 1 >= 0 else 0
                    need = 2 if lead >= 0xc0 else 0
                    need = 3 if lead >= 0xe0 else need
                    need = 4 if lead >= 0xf0 else need
                    if need and back + 1 < need:
                        cut = k - back - 1
                        self.carry = run[cut:]
                        run = run[:cut]
                        j = i + cut
                        n = j
                # _text retires only the rows this run touches; art elsewhere
                # stays put. A later read can extend the final grapheme or
                # trigger delayed autowrap, so never insert cleanup or
                # animation into that open text boundary.
                was_quarantined = self.quarantine
                pre = self._text(run)
                if self.retire_all or (was_quarantined and self.quarantine):
                    # Observation has stopped; forward bytes, never decoration.
                    # Keep the one erase produced by the guard that just entered
                    # quarantine.
                    pre = b''
                if self.quarantine and self.quarantine_cleared:
                    self.quarantine_cleared = False
                    self._log_quarantine('waiting', 'text-before-cursor')
                self.pending_wrap = self.cx >= self.cols
                self.text_tail = bool(run) or self.text_tail
                if pre:
                    out.append(data[emit:i])
                    out.append(pre)
                    emit = i
                if (self.passthrough and not self.retire_all
                        and not self.quarantine):
                    # Unsupported text ends observation permanently.
                    out.append(data[emit:])
                    self.carry = b''
                    return b''.join(out)
                i = j
        out.append(data[emit:n])
        return b''.join(out)

    @staticmethod
    def _seq_end(data, i):
        n = len(data)
        if i + 1 >= n:
            return -1
        c = data[i + 1]
        if c == 0x5b:  # CSI
            j = i + 2
            while j < n and 0x20 <= data[j] <= 0x3f:
                j += 1
            if j >= n:
                return -1
            return j + 1
        if c in (0x5d, 0x50, 0x5f, 0x5e, 0x58):  # OSC DCS APC PM SOS
            st = data.find(b'\x1b\\', i + 2)
            if c == 0x5d:
                bel = data.find(b'\x07', i + 2)
                if bel >= 0 and (st < 0 or bel < st):
                    return bel + 1
            return st + 2 if st >= 0 else -1
        if c in b'()*+-./# %':
            return i + 3 if i + 2 < n else -1
        return i + 2

    # ------------------------------------------------------------------ handlers
    def _touch(self, rows):
        hit = [r for r in rows if r in self.visible]
        if hit:
            signature = (tuple(hit), self.cy, self.cx)
            if signature != self.last_touch:
                self.last_touch = signature
                diagnostics.event('touch', rows=hit,
                                  cursor='%d,%d' % (self.cy, self.cx))
        self.dirty = True
        return self._erase(hit) if hit else b''

    def _uncertain(self):
        self._log_surface('uncertain', cursor='%d,%d' % (self.cy, self.cx))
        self.known = False
        self.dirty = True
        return self._erase_all()

    def _mode(self, name, unsafe):
        # Erase using the old coordinates, before forwarding a mode change.
        pre = self._uncertain()
        if unsafe:
            self.unsafe_modes.add(name)
        else:
            self.unsafe_modes.discard(name)
        self._log_surface('mode', mode=name, unsafe=unsafe)
        return pre

    def _text(self, run):
        if not run:
            return b''
        self._saw_text(run)
        if run.isascii():
            if self.cx >= self.cols:
                self.cx = 0
                self.cy += 1
            width = len(run)
            first, last = self.cy, self.cy + (self.cx + width - 1) // self.cols
            pre = self._touch(range(first, last + 1))
            if last >= self.rows:
                pre += self._uncertain()
            table = ASCII_FILLED if (self.bg or self.reverse) else ASCII_CONTENT
            pos = 0
            while pos < width and self.cy < self.rows:
                take = min(width - pos, self.cols - self.cx)
                piece = run[pos:pos + take].translate(table)
                row = self.grid[self.cy]
                before = row.count(1, self.cx, self.cx + take)
                row[self.cx:self.cx + take] = piece
                self.count[self.cy] += piece.count(1) - before
                pos += take
                self.cx += take
                if pos < width:
                    self.cx = 0
                    self.cy += 1
            self.cy = min(self.cy, self.rows - 1)
            return pre
        text = run.decode('utf-8', 'replace')
        # Widths of presentation selectors, joined emoji and regional flags
        # differ across terminals. Stop decoration for this process rather
        # than recover a guessed cursor after ED2 (which does not move it).
        kinds = set()
        for ch in text:
            value = ord(ch)
            if value == 0x200d:
                kinds.add('zwj')
            elif 0xfe00 <= value <= 0xfe0f:
                kinds.add('vs16')
            elif 0x1f000 <= value <= 0x1ffff:
                kinds.add('emoji')
            elif value == 0x20e3:
                kinds.add('keycap')
        if kinds:
            # The width model is no longer trustworthy. Retire every owned row
            # now if the text boundary is closed; otherwise defer until the
            # next explicit cursor position so a glyph cluster is not split.
            blocked = self.pending_wrap or self.text_tail
            pre = self._erase_all()
            self.known = False
            self.passthrough = True
            self.retire_all = blocked
            self.quarantine = True
            self.quarantine_cleared = False
            kind = '+'.join(sorted(kinds))
            diagnostics.event('unsupported', kind=kind, row=self.cy,
                              deferred=blocked)
            self._log_quarantine('entered', 'unsupported-width', kind=kind,
                                 row=self.cy)
            return pre
        first = self.cy
        filled = self.bg or self.reverse
        for ch in text:
            w = cwidth(ch)
            if w == 0:
                continue
            if self.cx + w > self.cols:
                self.cx = 0
                self.cy += 1
            if self.cy >= self.rows:
                break
            self._set_span(self.cy, self.cx, self.cx + w, filled or ch != ' ')
            self.cx += w
        # Wide glyphs can leave an unused cell before wrapping. Derive touched
        # rows from the same walk as occupancy, not total width / columns.
        # _parse inserts this cleanup before forwarding the entire text run.
        pre = self._touch(range(first, self.cy + 1))
        if self.cy >= self.rows:
            pre += self._uncertain()
            self.cy = self.rows - 1
        return pre

    def _control(self, b):
        if b in (0x0a, 0x0b, 0x0c):
            if self.cy + 1 >= self.rows:
                return self._uncertain()
            self.cy += 1
        elif b == 0x0d:
            self.cx = 0
        elif b == 0x08:
            self.cx = max(0, self.cx - 1)
        elif b == 0x09 and not self.pending_wrap:
            self.cx = min(self.cols - 1, (self.cx // 8 + 1) * 8)
        return b''

    def _sgr(self, raw):
        params = raw.split(b';') if raw else [b'0']
        i = 0
        while i < len(params):
            token = params[i]
            colon = b':' in token
            try:
                v = int(token.split(b':')[0] or b'0')
            except ValueError:
                v = -1
            if v == 0:
                self.bg = self.reverse = False
            elif v == 7:
                self.reverse = True
            elif v == 27:
                self.reverse = False
            elif 40 <= v <= 47 or 100 <= v <= 107:
                self.bg = True
            elif v == 49:
                self.bg = False
            if v in (38, 48, 58) and not colon:
                mode = params[i + 1] if i + 1 < len(params) else b''
                skip = 2 if mode == b'5' else 4 if mode == b'2' else 0
                if v == 48:
                    self.bg = True
                i += skip
            elif v == 48:
                self.bg = True
            i += 1

    def _save_cursor(self):
        if not (self.alt and self.entered_alt):
            self.saved = (self.cx, self.cy)
            return b''
        # A cursor save by the app inside the alternate screen would collide with ours.
        # ED2 does not release its saved cursor/attributes. Stay isolated until
        # a hard reset rather than overwrite the app's slot after a clear.
        self.disabled = True
        return self._mode('cursor-save', True)

    def _escape(self, seq):
        """Observe an app sequence; return only decoration to insert before it."""
        if self.retire_all:
            # Observation has stopped; only an explicit cursor boundary matters.
            return b''
        kind = seq[1]
        if seq == b'\x1b#8':  # DECALN fills the screen; ED2 can recover occupancy.
            return self._uncertain()
        if seq in (b'\x1b#3', b'\x1b#4', b'\x1b#5', b'\x1b#6'):
            return self._mode('line-geometry', True)
        if kind == 0x5b:
            return self._csi(seq)
        if kind == 0x37:  # DECSC
            return self._save_cursor()
        if kind == 0x38:  # DECRC
            self.cx, self.cy = self.saved
            return b''
        if kind == 0x4d:  # RI
            if self.cy == 0:
                return self._uncertain()
            self.cy -= 1
        elif kind in (0x44, 0x45):  # IND, NEL
            if self.cy + 1 >= self.rows:
                return self._uncertain()
            self.cy += 1
            if kind == 0x45:
                self.cx = 0
        elif kind == 0x63:  # RIS
            pre = self._erase_all()
            self.alt = False
            self.known = False
            self.unsafe_modes.clear()
            self.bg = self.reverse = self.sync = False
            self._reset_surface()
            return pre
        return b''

    def _csi(self, seq):
        body = seq[2:-1]
        final = seq[-1]
        priv = body[:1] if body[:1] in (b'?', b'<', b'>', b'=') else b''
        if priv:
            body = body[1:]
        inter = b''
        while body and 0x20 <= body[-1] <= 0x2f:
            inter = body[-1:] + inter
            body = body[:-1]
        selector = (priv, inter, final)
        if selector in CSI_CELL_EDITS:
            return self._uncertain()
        if selector in CSI_MODE_EDITS:
            return self._mode('terminal-state', True)
        if inter:
            return b''
        if final == 0x6d and not priv:  # SGR
            self._sgr(body)
            return b''
        try:
            nums = [int(x.split(b':')[0]) if x else 0 for x in body.split(b';')] if body else []
        except ValueError:
            return (self._uncertain() if not priv else b'')
        a = nums[0] if nums else 0
        if priv == b'?':
            if final in (0x68, 0x6c):
                return self._modes(nums, final == 0x68)
            return b''
        if priv:
            return b''
        if final in (0x68, 0x6c) and 4 in nums:  # IRM
            return self._mode('insert', final == 0x68)
        n1 = max(1, a)
        rows, cols = self.rows, self.cols
        if final in (0x48, 0x66):  # CUP
            self.cy = min(rows - 1, max(0, (a or 1) - 1))
            self.cx = min(cols - 1, max(0, ((nums[1] if len(nums) > 1 else 0) or 1) - 1))
        elif final == 0x41:
            self.cy = max(0, self.cy - n1)
        elif final in (0x42, 0x65):
            self.cy = min(rows - 1, self.cy + n1)
        elif final in (0x43, 0x61):
            self.cx = min(cols - 1, self.cx + n1)
        elif final == 0x44:
            self.cx = max(0, self.cx - n1)
        elif final == 0x45:
            self.cy, self.cx = min(rows - 1, self.cy + n1), 0
        elif final == 0x46:
            self.cy, self.cx = max(0, self.cy - n1), 0
        elif final in (0x47, 0x60):
            self.cx = min(cols - 1, n1 - 1)
        elif final == 0x64:
            self.cy = min(rows - 1, n1 - 1)
        elif final == 0x4a:  # ED
            filled = self.bg or self.reverse
            if a == 0:
                pre = self._touch(range(self.cy, rows))
                self._set_span(self.cy, self.cx, cols, filled)
                self._clear_rows(self.cy + 1, rows, filled)
                if self.cy == 0 and self.cx == 0 and self.alt:
                    self.known = not self.unsafe_modes
                    self._new_screen()
            elif a == 1:
                pre = self._touch(range(0, self.cy + 1))
                self._clear_rows(0, self.cy, filled)
                self._set_span(self.cy, 0, self.cx + 1, filled)
            elif a == 2:
                pre = self._touch(range(rows))
                self._clear_rows(0, rows, filled)
                if self.alt:
                    self.known = not self.unsafe_modes
                    self._new_screen()
            else:
                return b''
            return pre
        elif final == 0x4b:  # EL
            pre = self._touch([self.cy])
            filled = self.bg or self.reverse
            if a == 0:
                self._set_span(self.cy, self.cx, cols, filled)
            elif a == 1:
                self._set_span(self.cy, 0, self.cx + 1, filled)
            else:
                self._set_span(self.cy, 0, cols, filled)
            return pre
        elif final == 0x58:  # ECH
            pre = self._touch([self.cy])
            self._set_span(self.cy, self.cx, self.cx + n1, self.bg or self.reverse)
            return pre
        elif final == 0x72:  # DECSTBM: only a full-screen region is harmless
            top = a or 1
            bottom = (nums[1] if len(nums) > 1 else 0) or rows
            self.cx = self.cy = 0
            return self._mode('margins', top != 1 or bottom != rows)
        elif final == 0x73 and not body:
            return self._save_cursor()
        elif final == 0x75 and not body:
            self.cx, self.cy = self.saved
        elif final in (0x40, 0x50, 0x4c, 0x4d, 0x53, 0x54, 0x62):  # ICH DCH IL DL SU SD REP
            return self._uncertain()
        return b''

    def _modes(self, nums, on):
        pre = b''
        for mode in nums:
            if mode in (1049, 1047, 47):
                self._log_surface('alt-enter' if on else 'alt-leave',
                                  mode=mode)
                self.alt = on
                self.entered_alt |= on
                self.known = False
                self.disabled = False
                if on and self.quarantine:
                    self._clear_rows(0, self.rows)
                    self.quarantine_cleared = True
                    self._log_quarantine('cleared', 'alt-enter')
                self._reset_surface()
                self.dirty = True
            elif mode in (6, 7, 69):
                # DECOM, DECAWM and DECLRMM affect both app and overlay CUP/text.
                pre += self._mode('private-%d' % mode, not on if mode == 7 else on)
                if mode == 6:
                    self.cx = self.cy = 0
            elif mode == 2026:
                if on:
                    self.sync = True
                else:
                    self.sync = False
                    if self.dirty:
                        self.dirty = False
                        pre += self._frame_end()
        return pre


class ClaudeOverlay(Overlay):
    """Claude Code home layout. The blank-band policy is shared."""


class CodexOverlay(Overlay):
    """Codex home layout. The blank-band policy is shared."""
