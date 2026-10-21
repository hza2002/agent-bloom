"""Streaming byte replacement with split-sequence carry."""


class Replacer:
    # A continuous stream of coloured output can keep the first start marker
    # at offset zero forever. Flush a bounded prefix instead of holding an
    # unbounded buffer; a split replacement at this point is a fail-open case.
    MAX_HOLD = 65536
    HOLD_TAIL = 4096
    CUT_WINDOW = 4096

    def __init__(self, profile, opts):
        self.profile = profile
        self.opts = opts
        self.buf = b''
        self.failed = False

    @staticmethod
    def _partial(data, starts):
        best = 0
        for word in starts:
            for k in range(min(len(word) - 1, len(data)), 0, -1):
                if data.endswith(word[:k]):
                    best = max(best, k)
                    break
        return best

    def _bounded_cut(self, target):
        """A safe boundary near target, or target itself, for the buffer cap."""
        floor = max(0, target - self.CUT_WINDOW)
        best = -1
        for marker in self.profile.starts:
            at = self.buf.rfind(marker, floor, target)
            if at > best:
                best = at
        for byte in (b'\n', b'\x1b'):
            at = self.buf.rfind(byte, floor, target)
            if at > best:
                best = at
        return best if best >= 0 else target

    def feed(self, data, flush=False):
        if self.failed:
            return data
        self.buf += data
        if flush:
            cut = len(self.buf)
        else:
            # Overlapping start markers must be located from the beginning:
            # a shorter marker inside a longer one must not split the context
            # the header pattern needs.
            cut = len(self.buf)
            for marker in self.profile.starts:
                at = self.buf.find(marker)
                if at != -1:
                    cut = min(cut, at)
            hold = self._partial(self.buf, self.profile.starts)
            if hold:
                cut = min(cut, len(self.buf) - hold)
            if len(self.buf) - cut > self.MAX_HOLD:
                target = len(self.buf) - self.HOLD_TAIL
                cut = max(cut, self._bounded_cut(target))
        if cut <= 0:
            return b''
        try:
            out = self.profile.replace(self.buf[:cut], self.opts)
        except Exception:
            # No transformed bytes have been emitted yet. Release the whole
            # buffer once and bypass this decoration for the rest of the run.
            out, self.buf = self.buf, b''
            self.failed = True
            return out
        self.buf = self.buf[cut:]
        return out
