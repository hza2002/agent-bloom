"""Conservative input hints; this observes bytes, not the application's line editor."""
import codecs


class InputObserver:
    """Bounded line candidate and per-feed (submitted, reset_requested) events.

    reset_requested describes the last non-empty submission in the feed.

    Unknown editing disables exact command recognition until a line boundary or an
    explicit line clear. Escape sequences and UTF-8 may span arbitrary reads.
    """

    def __init__(self, commands=('/clear', '/reset', '/new')):
        self.commands = frozenset(commands)
        self.typed = ''
        self.exact = True
        self.paste = False
        self._state = 'text'
        self._csi = ''
        self._csi_first = ''
        self._osc = False
        self._decoder = codecs.getincrementaldecoder('utf-8')('replace')

    def _clear_line(self):
        self.typed = ''
        self.exact = True

    def _is_terminal_report(self, marker):
        """Private CSI and focus/window reports are not keyboard editing.

        Cursor-position reports (CSIR) stay conservative: they are byte-identical
        to a modified F3 key. The first parameter byte is kept even when the
        parameter buffer overflows, so a long device-attributes reply is still a
        report rather than unknown editing.
        """
        return self._csi_first in ('?', '>', '=') or marker[-1] in 'IOt'

    def feed(self, data):
        submitted = reset = False
        for ch in self._decoder.decode(data):
            if self._state == 'text' and ch >= ' ' and ch != '\x7f':
                if self.exact and (len(self.typed) >= 64 or ch == '\ufffd'):
                    self.exact = False
                self.typed = (self.typed + ch)[-64:]
                continue
            byte = ord(ch)
            if self._state == 'string':
                if byte == 7 and self._osc:
                    self._state = 'text'
                elif byte == 27:
                    self._state = 'string_escape'
                continue
            if self._state == 'string_escape':
                self._state = 'text' if byte == 92 else 'string'
                continue
            if self._state == 'escape':
                if byte == 91:
                    self._state = 'csi'
                    self._csi = ''
                    self._csi_first = ''
                elif byte == 79:
                    self._state = 'ss3'
                    self.exact = False
                elif ch in ']P_^X':
                    # Control strings on stdin are terminal reports (XTVERSION,
                    # colour replies), not editing. They must not arm an empty
                    # Enter as a submission.
                    self._osc = ch == ']'
                    self._state = 'string'
                else:
                    self._state = 'text'
                    self.exact = False
                continue
            if self._state == 'ss3':
                self._state = 'text'
                continue
            if self._state == 'csi':
                if 64 <= byte <= 126:
                    marker = self._csi + chr(byte)
                    if marker == '200~':
                        self.paste = True
                        self.exact = False
                    elif marker == '201~' and self.paste:
                        self.paste = False
                    elif not self._is_terminal_report(marker):
                        self.exact = False
                    self._state = 'text'
                elif 32 <= byte <= 63:
                    # Only paste delimiters and the private-prefix test matter;
                    # discard the rest of the parameters.
                    if not self._csi_first:
                        self._csi_first = chr(byte)
                    self._csi = (self._csi + chr(byte)) if len(self._csi) < 8 else '?'
                elif byte == 27:
                    self._state = 'escape'
                    self.exact = False
                else:
                    self._state = 'text'
                    self.exact = False
                continue
            if byte == 27:
                self._state = 'escape'
            elif byte in (10, 13) and not self.paste:
                if self.typed.strip() or not self.exact:
                    submitted = True
                    reset = self.exact and self.typed.strip(' ') in self.commands
                self._clear_line()
            elif byte in (3, 21) and not self.paste:
                self._clear_line()
            elif byte in (8, 127) and not self.paste:
                if self.typed and ord(self.typed[-1]) >= 128:
                    # Editors may delete a whole grapheme rather than one codepoint.
                    self.exact = False
                self.typed = self.typed[:-1]
            else:
                # Tabs, readline commands, and pasted newlines are not exact input.
                self.exact = False
        return submitted, reset
