"""Streaming byte replacement with split-sequence carry."""


class Replacer:
    def __init__(self, profile, opts):
        self.profile = profile
        self.opts = opts
        self.buf = b''

    @staticmethod
    def _partial(data, starts):
        best = 0
        for word in starts:
            for k in range(min(len(word) - 1, len(data)), 0, -1):
                if data.endswith(word[:k]):
                    best = max(best, k)
                    break
        return best

    def feed(self, data, flush=False):
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
        if cut <= 0:
            return b''
        out = self.profile.replace(self.buf[:cut], self.opts)
        self.buf = self.buf[cut:]
        return out
