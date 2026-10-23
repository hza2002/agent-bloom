"""Opening scene and ambient animation composited into the app's blank cells."""
import time

from . import art, diagnostics
from .scene import ease_in_out

AMBIENT_PERIOD = 8.0
AMBIENT_SWEEP = 2.0
VISIBILITY_POLL_INTERVAL = 0.05
# 60 Hz keeps the bloom, the decode and the fade smooth without flooding the PTY.
FRAME_HZ = 60
FRAME_INTERVAL = 1.0 / FRAME_HZ
# The ambient sweep is a slow 2 s glow; 30 Hz is visually identical and halves
# its output and terminal work.
AMBIENT_INTERVAL = 1.0 / 30
# The sheen crossing the small text is this fraction of the text width, with a
# floor so short lines still show a readable highlight. The peak mix is a little
# softer than the mark's sweep so the copy stays readable while it flashes.
AMBIENT_TEXT_BAND_DIVISOR = 8
AMBIENT_TEXT_MIN_BAND = 2
AMBIENT_TEXT_HIGHLIGHT = 0.65


def make_animated_overlay(base, create_scene):
    class AnimatedOverlay(base):
        def __init__(self, *args, play_intro=True, ambient=True, visibility=None, **kwargs):
            self.anim_scene = None
            self.anim_start = None
            self.play_intro = play_intro
            self.ambient_enabled = ambient
            self.anim_done = not play_intro
            self.ambient_start = None
            self.ambient_next = None
            self.ambient_stopped = False
            self.visibility = visibility or (lambda: True)
            self.pane_hidden = False
            self.scene_failed = False
            self.failed_anchor = None
            self.next_frame = None
            self.last_diagnostic = None
            self.last_diagnostic_at = 0.0
            super().__init__(*args, **kwargs)
            self.intro_owns_home = play_intro

        def _diagnose(self):
            if not diagnostics.DEBUG:
                return
            if self.quarantine:
                reason = 'quarantine'
            elif self.passthrough:
                reason = 'passthrough'
            elif self.disabled:
                reason = 'disabled'
            elif self.unsafe_modes:
                reason = 'unsafe-terminal-mode'
            elif not self.known:
                reason = 'unknown-screen'
            elif not self.alt:
                reason = 'main-screen'
            elif self.submitted:
                reason = 'submitted'
            elif self.sync:
                reason = 'synchronized-update-open'
            elif self.carry:
                reason = 'incomplete-sequence'
            elif self.pending_wrap:
                reason = 'pending-wrap'
            elif self.text_tail:
                reason = 'waiting-for-cursor-boundary'
            elif self.scene_failed:
                reason = 'scene-does-not-fit'
            elif not self.anim_done:
                reason = 'intro-eligible'
            elif not self.anchor or not self.visible:
                reason = 'no-visible-home'
            else:
                reason = 'home-eligible'
            shown = bool(self.visible) and reason in ('intro-eligible',
                                                      'home-eligible')
            anchor = self.anchor[1] if self.anchor is not None else None
            ambient = ('sweep' if self.ambient_start is not None else
                       ('pending' if self.ambient_next is not None else 'idle'))
            fields = dict(reason=reason, band=self._band_label(),
                          anchor=anchor, visible=len(self.visible),
                          used=len(self.rows_used),
                          intro=('playing' if not self.anim_done else 'done'),
                          ambient=ambient)
            state = (reason, self.cols, self.rows, fields['band'], anchor,
                     fields['visible'], fields['intro'], ambient)
            now = time.monotonic()
            if state != self.last_diagnostic:
                self.last_diagnostic = state
                self.last_diagnostic_at = now
                diagnostics.event('state',
                                  state='shown' if shown else 'hidden',
                                  **fields)
            elif now - self.last_diagnostic_at >= diagnostics.HEARTBEAT_SECONDS:
                self.last_diagnostic_at = now
                diagnostics.event('heartbeat',
                                  state='shown' if shown else 'hidden',
                                  **fields)

        def _pane_visible(self):
            """Fail open: an unavailable or broken check must not hide the art."""
            try:
                return self.visibility()
            except Exception:
                return True

        def _invalidate_frame(self):
            if self.anim_scene is not None:
                self.anim_scene.invalidate()

        def _reset_surface(self):
            super()._reset_surface()
            # A scene borrows geometry from this surface. Keep the one-shot
            # clock, but acquire a new band before constructing another scene.
            self.anim_scene = None
            self.scene_failed = False
            self.failed_anchor = None
            self.next_frame = None
            self.ambient_start = None

        def resize(self, cols, rows):
            t = None
            if self.anim_scene is not None and self.anim_start is not None:
                t = time.monotonic() - self.anim_start
            done = self.anim_done
            super().resize(cols, rows)
            # Resize does not prove which cells survived or where the app will
            # repaint. Wait for a full clear before borrowing blank rows again.
            self.dirty = True
            self.anim_scene = None
            self.anim_done = done
            self.scene_failed = False
            self.anim_start = None if t is None else time.monotonic() - t
            self.next_frame = None
            self.ambient_start = None

        def animating(self):
            if not self.anim_done:
                return True
            return super().animating()

        def _frame_wait(self, interval=FRAME_INTERVAL):
            """Seconds until the next animation frame is due."""
            if self.next_frame is None:
                # Nothing has been rendered yet; do not spin select while the
                # tick path is waiting for a layout or a scene.
                return interval
            return max(0.0, self.next_frame - time.monotonic())

        def _frame_ready(self, now, interval=FRAME_INTERVAL):
            """False on an early wake (app output), so frames keep a steady cadence."""
            due = self.next_frame
            if due is not None and now < due:
                return False
            # Keep the cadence anchored to the deadline instead of adding the
            # render cost and select jitter to every interval. Skip a whole
            # missed frame rather than bursting to catch up.
            if due is None or now >= due + interval:
                self.next_frame = now + interval
            else:
                self.next_frame = due + interval
            return True

        def next_timeout(self):
            self._diagnose()
            if (self.pending_wrap or self.text_tail or self.passthrough or self.disabled or self.sync or self.carry
                    or not self.known or self.unsafe_modes):
                return None
            if not self.anim_done:
                # An inline app never enters the alternate screen; do not spin a
                # frame timer for a background it cannot show. Likewise, wait for
                # app output when there is no complete band to start in yet.
                if not self.alt:
                    return None
                if self.anchor is None and self._band() is None:
                    return None
                return self._frame_wait()
            if self.submitted:
                return None
            if super().animating():
                return self._frame_wait()
            if (self.scene_failed and self.anchor is not None
                    and self.failed_anchor != (self.anchor[0], self.anchor[1])):
                self.scene_failed = False
                self.failed_anchor = None
            if self.anim_scene is None and self.scene_failed:
                return None
            if (self.ambient_enabled and self.alt and self.anchor and self.visible):
                if self.ambient_start is not None:
                    return self._frame_wait(AMBIENT_INTERVAL)
                if self.ambient_next is not None:
                    return max(0.0, self.ambient_next - time.monotonic())
                return self._frame_wait(AMBIENT_INTERVAL)
            return None

        def _start_scene(self, lock, top):
            scene = create_scene(
                self.cols, self.rows, self.pal, self.brand,
                lock=lock, top=top)
            if not scene.ok:
                self.anim_scene = None
                self.anim_done = True
                self.intro_owns_home = False
                self.scene_failed = True
                self.failed_anchor = (lock, top)
                self.next_frame = None
                self.release()
                diagnostics.event('intro', phase='skip', reason='scene-failed',
                                  top=top)
                return False
            self.anim_scene = scene
            self.scene_failed = False
            self.failed_anchor = None
            self.next_frame = None
            if self.anim_start is None:
                self.anim_start = time.monotonic()
            diagnostics.event('intro', phase='start', top=top,
                              word_rows=lock.word_rows,
                              lock=','.join(
                                  name for name, shown in
                                  (('mark', lock.show_mark),
                                   ('word', lock.show_word),
                                   ('small', lock.show_small)) if shown) or '-')
            return True

        def _rows(self):
            if self.anim_scene is None:
                return []
            return [r for r in range(self.anim_scene.y0, self.anim_scene.y1)
                    if not self.count[r]]

        def _text_tint(self, u):
            """One left-to-right sheen over the small text during the sweep."""
            lock, _, _ = self.anchor
            brand = lock.brand
            tag = ' '.join(brand.tagline)
            width = max(1, lock.slogan_cols, art.text_width(tag),
                        art.text_width(art.platform_line(brand)))
            left = lock.centre(width)
            band = max(AMBIENT_TEXT_MIN_BAND,
                       width // AMBIENT_TEXT_BAND_DIVISOR)
            centre = -band + (width + 2 * band) * ease_in_out(
                min(1.0, max(0.0, u)))

            def tint(_row, col, rgb):
                glow = 1.0 - abs(col - left - centre) / band
                if glow <= 0.0:
                    return rgb
                # Neutral copy lifts to the theme accent; the accented platform line
                # lifts to ink so the same pass reads on both palettes.
                target = (self.pal['ink'] if rgb == self.pal['accent']
                          else self.pal['accent'])
                return art.mix(rgb, target,
                               AMBIENT_TEXT_HIGHLIGHT * glow * glow)
            return tint

        def _ambient_text(self, u):
            """Repaint the small text rows with the ambient sheen."""
            if self.anchor is None:
                return b''
            lock, top, _ = self.anchor
            if not lock.show_small:
                return b''
            rows = [r for r in range(top + lock.slogan_top,
                                     min(self.rows, top + lock.height))
                    if not self.count[r]]
            if not rows:
                return b''
            content = art.small_text_rows(lock, top, 1.0, self.pal,
                                          tint=self._text_tint(u))
            parts = []
            for row in rows:
                entries = content.get(row)
                if not entries:
                    continue
                parts.append('\x1b[%d;1H\x1b[2K' % (row + 1))
                for col, cells in entries:
                    parts.append('\x1b[%d;%dH' % (row + 1, col + 1))
                    parts.append(art.render_run(cells))
                self.visible.add(row)
            body = self._wrap(''.join(parts))
            if not body:
                return b''
            return b'\x1b[?2026h' + body + b'\x1b[?2026l'

        def _finish(self, paint=False):
            self.anim_done = True
            self.intro_owns_home = False
            self.next_frame = None
            self.release()
            if self.ambient_enabled and self.ambient_next is None:
                self.ambient_next = time.monotonic() + AMBIENT_PERIOD
            diagnostics.event('intro', phase='finish',
                              ambient_next=(round(self.ambient_next, 2)
                                            if self.ambient_next is not None else None))
            out = b''
            if paint and not self.submitted:
                # Drop every animation frame, then paint the whole static home. The
                # last opening frame may not have locked every wordmark row yet, and
                # _frame_end only repaints rows it believes are missing.
                pre = self._erase_all()
                body = self._frame_end()
                if pre or body:
                    out = b'\x1b[?2026h' + pre + body + b'\x1b[?2026l'
            return out

        def _session_reset(self):
            super()._session_reset()
            # Only a confirmed reset candidate restores ambient permission.
            self.ambient_stopped = False
            self.ambient_start = None
            self.ambient_next = None
            self.scene_failed = False
            self.failed_anchor = None

        def tick(self):
            if (self.pending_wrap or self.text_tail or self.passthrough or self.disabled or self.sync or self.carry
                    or not self.known or self.unsafe_modes):
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
                        band = self._band()
                        if band is None:
                            # No blank band yet; app output will wake the loop.
                            return super().tick()
                        lock, top, run = band
                        self._set_anchor(lock, top, run)
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
                now = time.monotonic()
                t = now - self.anim_start
                if t >= self.anim_scene.duration:
                    return self._finish(paint=True) + super().tick()
                if not self._frame_ready(now):
                    return b''
                if not rows:
                    return b''
                cells = self.anim_scene.frame(t)
                self.visible.update(rows)
                return self._wrap(self.anim_scene.ansi(cells, rows))
            # The opening scene has finished. A slow sweep keeps the home alive while
            # there is blank space; nothing is painted once the session submits.
            now0 = time.monotonic()
            if self.submitted:
                rows = [r for r in self.visible if not self.count[r]]
                out = self._erase(rows)
                self.ambient_stopped = True
                self.ambient_start = None
                self.ambient_next = None
                return out + super().tick()
            # Submit cleanup takes priority over the fade and its deadline.
            # Otherwise app output must not trigger extra fade frames.
            if super().animating():
                if not self._frame_ready(now0):
                    return b''
                out = super().tick()
                if not super().animating():
                    self.next_frame = None
                return out
            if (self.ambient_enabled and self.alt and self.anchor and self.visible):
                lock, top = self.anchor[0], self.anchor[1]
                if (self.anim_scene is not None
                        and (self.anim_scene.lock, self.anim_scene.top) != (lock, top)):
                    # The app moved its home (resize, notices): drop the stale scene.
                    self.anim_scene = None
                    self.ambient_start = None
                    self.scene_failed = False
                    self.failed_anchor = None
                now = time.monotonic()
                if self.ambient_next is None:
                    self.ambient_next = now + AMBIENT_PERIOD
                if self.ambient_start is None:
                    if now < self.ambient_next:
                        return super().tick()
                    visible = self._pane_visible()
                    if visible is None:
                        self.ambient_next = now + VISIBILITY_POLL_INTERVAL
                        return super().tick()
                    if not visible:
                        if not self.pane_hidden:
                            self.pane_hidden = True
                            diagnostics.event('ambient', phase='hidden')
                        self.ambient_next = now + AMBIENT_PERIOD
                        return super().tick()
                    if self.pane_hidden:
                        self.pane_hidden = False
                        diagnostics.event('ambient', phase='visible')
                    self.ambient_start = now
                    diagnostics.event('ambient', phase='sweep-start')
                if self.anim_scene is None:
                    if not self._start_scene(lock, top):
                        return super().tick()
                u = (now - self.ambient_start) / AMBIENT_SWEEP
                if u >= 1.0:
                    diagnostics.event('ambient', phase='sweep-end')
                    start = self.ambient_start
                    self.ambient_start = None
                    self.next_frame = None
                    # Keep the cadence start-to-start, not end-to-start.
                    self.ambient_next = max(now + 0.1, start + AMBIENT_PERIOD)
                    # Backpressure may skip the last sweep frames. Do not leave
                    # a transient highlight on screen until the next sweep.
                    out = self._ambient_text(1.0)
                    rows = self._rows()
                    if rows:
                        cells = self.anim_scene.frame(self.anim_scene.duration)
                        out += self._wrap(self.anim_scene.ansi(cells, rows))
                    return out
                if not self._frame_ready(now, AMBIENT_INTERVAL):
                    return super().tick()
                out = self._ambient_text(min(1.0, u))
                rows = self._rows()
                if rows:
                    cells = self.anim_scene.ambient_frame(min(1.0, u))
                    self.visible.update(rows)
                    out += self._wrap(self.anim_scene.ansi(cells, rows))
                return out
            return super().tick()
    return AnimatedOverlay
