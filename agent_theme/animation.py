"""Background Bloom and ambient sweep composited into the app's blank cells."""
import os
import time

AMBIENT_LOOP = True
AMBIENT_PERIOD = 8.0
AMBIENT_SWEEP = 2.0


def make_animated_overlay(base, intro, top_hint=3):
    class AnimatedOverlay(base):
        def __init__(self, *args, play_intro=True, **kwargs):
            self.anim_scene = None
            self.anim_start = None
            self.play_intro = play_intro
            self.anim_done = not play_intro
            self.ambient_start = None
            self.ambient_next = None
            self.ambient_stopped = False
            self.scene_failed = False
            self.failed_anchor = None
            self.last_dbg = 0.0
            self.home_top = top_hint
            super().__init__(*args, **kwargs)
            self.intro_owns_home = play_intro

        def _dbg(self, *parts):
            path = os.environ.get('AGENT_THEME_DEBUG')
            if path:
                try:
                    with open(path, 'a') as f:
                        f.write('%.3f %s\n'
                                % (time.monotonic(), ' '.join(map(str, parts))))
                except OSError:
                    pass

        def resize(self, cols, rows):
            t = None
            if self.anim_scene is not None and self.anim_start is not None:
                t = time.monotonic() - self.anim_start
            done = self.anim_done
            super().resize(cols, rows)
            # The app receives SIGWINCH and repaints; let the next frame re-anchor
            # instead of waiting for a full clear that may never come.
            self.known = True
            self.dirty = True
            self.anim_scene = None
            self.anim_done = done
            self.scene_failed = False
            self.anim_start = None if t is None else time.monotonic() - t
            self.ambient_start = None

        def animating(self):
            if not self.anim_done:
                return True
            return super().animating()

        def next_timeout(self):
            if self.disabled or self.sync or self.carry:
                return None
            if not self.anim_done:
                # An inline app never enters the alternate screen; do not spin a
                # 40 Hz timer for a background it cannot show.
                return None if not self.alt else 1.0 / 40
            if self.submitted and not self.is_fresh():
                return None
            if super().animating():
                return 1.0 / 40
            now0 = time.monotonic()
            if now0 - self.last_dbg > 1.0:
                self.last_dbg = now0
                self._dbg('done alt', self.alt, 'anchor', bool(self.anchor),
                          'visible', len(self.visible), 'scene', bool(self.anim_scene),
                          'next', self.ambient_next, 'start', self.ambient_start)
            if self.scene_failed and (
                    self.is_fresh()
                    or (self.anchor is not None
                        and self.failed_anchor != (self.anchor[0], self.anchor[1]))):
                self.scene_failed = False
                self.failed_anchor = None
            if self.anim_scene is None and self.scene_failed:
                return None
            if (AMBIENT_LOOP and self.alt and self.anchor and self.visible):
                if self.anim_scene is None:
                    return 1.0 / 40
                if self.ambient_start is not None:
                    return 1.0 / 40
                if self.ambient_next is None:
                    return 1.0 / 40
                return max(0.0, self.ambient_next - time.monotonic())
            return None

        def _start_scene(self, lock, top):
            scene = intro.Bloom(
                self.cols, self.rows, self.pal, self.brand,
                bloom_length=2.95, lock=lock, top=top)
            if not scene.ok:
                self.anim_scene = None
                self.anim_done = True
                self.intro_owns_home = False
                self.scene_failed = True
                self.failed_anchor = (lock, top)
                self.release()
                return False
            self.anim_scene = scene
            self.scene_failed = False
            self.failed_anchor = None
            if self.anim_start is None:
                self.anim_start = time.monotonic()
            return True

        def _rows(self):
            if not self.anchor:
                return [r for r in range(self.anim_scene.y0, self.anim_scene.y1)
                        if not self.count[r]]
            layout = self._layout()
            if layout is None:
                return None
            top_end, bottom_start = layout
            return [r for r in range(self.anim_scene.y0, self.anim_scene.y1)
                    if top_end < r < bottom_start - 1 and not self.count[r]]

        def _finish(self, paint=False):
            self.anim_done = True
            self.intro_owns_home = False
            self.release()
            if self.ambient_next is None:
                self.ambient_next = time.monotonic() + AMBIENT_PERIOD
            self._dbg('finish ambient_next', self.ambient_next)
            out = b''
            if paint and not self.submitted:
                # Drop every animation frame, then paint the whole static home. The
                # last Bloom frame may not have locked every wordmark row yet, and
                # _frame_end only repaints rows it believes are missing.
                pre = self._erase_all()
                body = self._frame_end()
                if pre or body:
                    out = b'\x1b[?2026h' + pre + body + b'\x1b[?2026l'
            return out

        def _new_screen(self):
            super()._new_screen()
            # A full clear creates a new home; the previous submit must not
            # leave ambient_stopped latched over the next conversation.
            self.ambient_stopped = False
            self.ambient_start = None
            self.ambient_next = None

        def tick(self):
            if self.disabled or self.sync or self.carry:
                return b''
            if not self.anim_done:
                if not self.alt:
                    return super().tick()
                if self.submitted:
                    rows = [r for r in self.visible if not self.count[r]]
                    out = self._erase(rows)
                    self._finish()
                    return out + super().tick()
                if self.anim_scene is None:
                    if self.anchor:
                        lock, top = self.anchor[0], self.anchor[1]
                    else:
                        lock, top = intro.home_anchor(self.brand, self.cols, self.rows,
                                                       self.home_top)
                    if not self._start_scene(lock, top):
                        return self._finish(paint=True) + super().tick()
                if self.anchor:
                    lock, top = self.anchor[0], self.anchor[1]
                    if (self.anim_scene.lock, self.anim_scene.top) != (lock, top):
                        t = time.monotonic() - self.anim_start
                        self.anim_scene = None
                        self.anim_start = time.monotonic() - t
                        if not self._start_scene(lock, top):
                            return self._finish(paint=True) + super().tick()
                rows = self._rows()
                if rows is None:
                    self._finish()
                    return super().tick()
                if not rows:
                    return super().tick()
                now_dbg = time.monotonic()
                if now_dbg - getattr(self, 'last_anim_dbg', 0) > 0.5:
                    self.last_anim_dbg = now_dbg
                    self._dbg('anim', 'alt', self.alt, 'anchor', bool(self.anchor),
                              'top', getattr(self.anim_scene, 'top', None),
                              'y', getattr(self.anim_scene, 'y0', None),
                              getattr(self.anim_scene, 'y1', None),
                              'rows', rows[:5], len(rows))
                t = time.monotonic() - self.anim_start
                if t >= self.anim_scene.duration:
                    return self._finish(paint=True) + super().tick()
                cells = self.anim_scene.frame(t)
                self.visible.update(rows)
                return self._wrap(self.anim_scene.ansi(cells, rows))
            # One-shot Bloom has finished. A slow sweep keeps the home alive while
            # there is blank space; nothing is painted once the session submits.
            now0 = time.monotonic()
            if now0 - self.last_dbg > 1.0:
                self.last_dbg = now0
                self._dbg('done alt', self.alt, 'anchor', bool(self.anchor),
                          'visible', len(self.visible), 'scene', bool(self.anim_scene),
                          'next', self.ambient_next, 'start', self.ambient_start)
            fresh = self.is_fresh()
            if self.submitted and not fresh:
                rows = [r for r in self.visible if not self.count[r]]
                out = self._erase(rows)
                self.ambient_stopped = True
                self.ambient_start = None
                self.ambient_next = None
                return out + super().tick()
            if fresh:
                if self.ambient_stopped:
                    # /clear returns to an empty session: let the sweep start again.
                    self.ambient_stopped = False
                    self.ambient_next = now0
                self.scene_failed = False
                self.failed_anchor = None
            if (AMBIENT_LOOP and self.alt and self.anchor and self.visible):
                lock, top = self.anchor[0], self.anchor[1]
                if (self.anim_scene is not None
                        and (self.anim_scene.lock, self.anim_scene.top) != (lock, top)):
                    # The app moved its home (resize, notices): drop the stale scene.
                    self.anim_scene = None
                    self.ambient_start = None
                    self.scene_failed = False
                    self.failed_anchor = None
                if self.anim_scene is None:
                    if not self._start_scene(lock, top):
                        return super().tick()
                now = time.monotonic()
                if self.ambient_next is None:
                    self.ambient_next = now + AMBIENT_PERIOD
                if self.ambient_start is None:
                    if now < self.ambient_next:
                        return super().tick()
                    self.ambient_start = now
                u = (now - self.ambient_start) / AMBIENT_SWEEP
                if u >= 1.0:
                    self._dbg('sweep end')
                    start = self.ambient_start
                    self.ambient_start = None
                    # Keep the cadence start-to-start, not end-to-start.
                    self.ambient_next = max(now + 0.1, start + AMBIENT_PERIOD)
                    return super().tick()
                rows = self._rows()
                if rows:
                    self._dbg('sweep', round(u, 2), 'rows', len(rows))
                    cells = self.anim_scene.frame(2.02 + min(1.0, u) * 0.7)
                    self.visible.update(rows)
                    return self._wrap(self.anim_scene.ansi(cells, rows))
            return super().tick()
    return AnimatedOverlay
