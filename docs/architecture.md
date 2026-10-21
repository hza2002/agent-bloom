# Architecture

`huawei-bloom` is a PTY proxy that adds branding at the edges of known TUI
renderers. Its occupancy tracker supports a conservative subset of terminal
operations; it is not a general terminal emulator. The app is never modified,
and the wrapper must never be required for the app to work.

## Invariants

These are product requirements, not implementation suggestions:

- The app's config, credentials, plugins and binary are untouched.
- Every decoration path is best-effort. Any overlay/replacer failure drops the
  decoration and lets the original bytes through.
- Animation never waits for terminal output in the input/signal event loop.
  The app remains usable while the intro runs, including during output backpressure.
- The overlay only draws into entire rows the app currently leaves blank, while
  the tracker has a known screen and supported terminal modes.
- The terminal is restored on exit, signal or hangup.
- The wrapper is POSIX-only and standard-library-only at runtime.

## Data flow

```text
stdin ──────────────────────────────┐
                                    ▼
                            Launcher (raw mode, signals, PTY)
                                    │
                                    ├── supervisor ── app process
                                    │
app PTY ── bytes ── Replacer ── Overlay.feed ── bytes ── stdout
                         │            │
                         │            └── screen model, layout, paint
                         └── header/title byte replacement
                                    │
                              Art / Layout
```

`Launcher.send()` applies the streaming `Replacer` first, then gives the same
bytes to the overlay's screen model. The overlay's output is composited after
the app's output. A timer (`Launcher.tick`) drives the intro and ambient sweep.

Replacer is the only layer allowed to replace application bytes. Overlay
handlers return decoration to insert before an operation; the parser always
forwards that operation verbatim. Entering or leaving the alternate screen
belongs to the application, not the animation. Removing inserted decoration
from the resulting stream must recover the original input, regardless of chunk
boundaries.

The launcher forwards user-supplied app arguments unchanged; it never injects
startup configuration overrides. Codex users disable its welcome effect in their
own config so that home decoration does not change daemon startup policy.

All output shares a nonblocking FIFO. At its 256 KiB high-water mark the launcher
pauses PTY reads, while continuing to forward input and handle signals. One read
and its decorations can exceed that mark; it is a backpressure threshold, not a
hard byte cap. Animation frames are generated only after the FIFO drains. Once
generated, a frame must stay in order, including every partially written ANSI
sequence: the screen model and diff cache have already advanced to that frame.
Normal exit drains application output; explicit termination has a bounded wait.

Input has its own 256 KiB queue limit. Once full, the launcher pauses stdin
reads until the app accepts more bytes; output and signal handling continue.
Reads are limited to the remaining capacity, so large pastes cannot grow the
proxy's input queue without bound.

## Modules

| Module | Responsibility |
| --- | --- |
| `huawei-bloom` | Executable entry point; makes the checkout importable. |
| `cli.py` | Flag parsing, help, `--check`, exit statuses. |
| `apps.py` | **The only app-specific layer.** `Profile` owns the binary, argument policy, header/title patterns, overlay class, home top and self-check. |
| `launcher.py` | PTY transport, raw mode, resize, signals, process lifecycle, terminal restore. App-neutral. |
| `replacer.py` | Streaming replacement of startup header/title bytes, with split-sequence carry. App-neutral engine; patterns come from `Profile`. |
| `overlay.py` | Terminal screen model, ANSI parsing, blank-cell detection and painting. `ClaudeOverlay`/`CodexOverlay` are layout policies selected by `Profile`. |
| `animation.py` | Intro/ambient state machine layered over an overlay. App-neutral. |
| `intro.py` | The Bloom scene and its timeline. App-neutral. |
| `art.py`, `assets/art.json` | Glyph tables, vector mark, lockup composition, palette and ANSI run rendering. |
| `terminal.py` | Capability detection, tmux naming, exit-code mapping and PTY I/O helpers. |
| `supervisor.py` | Foreground process group, stop/hangup mirroring. |

The core modules (`launcher`, `replacer`, `overlay` base, `animation`, `intro`,
`art`) must not branch on app names. Adding an app means adding a `Profile`, its
overlay policy, its art brand and tests.

## Session state

- **Fresh session:** the wrapper creates an overlay, the app enters the
  alternate screen, and the one-shot Bloom paints into blank cells.
- **Intro:** starts only for a fresh session. Resuming, continuing or an initial
  prompt skips it. Empty Enter does not stop it.
- **Submit:** a non-empty prompt stops ambient and erases the decoration. The
  app's own conversation is never covered.
- **`/clear`:** a new empty screen gets the home and ambient again.
- **Resize:** the PTY is resized and decoration ownership is forgotten. The
  overlay waits for an application full clear before painting again. Removal of
  old decorations relies on the application's repaint; resize alone does not
  establish a blank screen.
- **No alternate screen / unexpected output:** the overlay stays off; bytes pass
  through. This is the fail-open path.

## Terminal state and cache ownership

A full clear establishes cell occupancy; it does not reset terminal modes.
Non-default scrolling margins, origin mode, disabled autowrap, insert mode and
left/right margin mode suppress decoration across clears, resizes and alternate
screen switches. Explicitly restoring the supported modes followed by a full
clear can re-enable it. Unsupported transient operations invalidate occupancy
until a full clear. An application cursor save inside the alternate screen
keeps decoration isolated until a hard reset: a clear does not release the
application's saved cursor/attributes slot. This policy does not imply support
for every terminal extension.

Wide-character wrapping and row cleanup use the same cell walk: an unused cell
at the right edge must not hide a row touched by the application. Cleanup is
emitted before that application's text.

Control dispatch uses the complete selector (private prefix, intermediate,
final byte), not the presence of intermediate bytes as a safety heuristic.
Known cell edits, including DECALN and rectangle operations, invalidate
occupancy until a clear. Known unmodelled persistent controls, such as line
geometry, page size and character protection, isolate decoration until a hard
reset. Queries and other unhandled extensions pass through without changing
the model. The actual terminal answers queries; the proxy neither emulates
capabilities nor adds an application-specific query whitelist.

This is a deliberately bounded observer of Claude/Codex output, not a general
terminal emulator: an unhandled extension that changes cells or modes can
invalidate its assumptions. Universal compatibility would require a complete
terminal model or cooperation from the application. Unknown syntax alone is
not evidence of a persistent mode change.

Surface changes, clears, erases and home paints share a frame invalidation hook.
Alternate-screen switches reset ownership and invalidate the previous scene's
diff cache even when no erase bytes are necessary. Resize rebuilds the scene.

Incomplete control sequences are held for parsing, up to 64 KiB. Exceeding the
limit releases all held bytes and permanently bypasses the overlay for that
run, so later output cannot insert decoration inside the unfinished sequence.
Normal exit also releases shorter incomplete tails. Replacement exceptions
release the replacer's buffer and disable further replacement. Overlay parser
exceptions preserve its previously held bytes and bypass decoration; existing
paint may remain until the app repaints or exits.

## Animation scheduling

Intro and slogan fade use 60 Hz deadlines; ambient sweeps use 30 Hz. App output
cannot request an early frame. A missed deadline skips catch-up frames, and the
animation clock still advances when no rows can be painted. A sweep always
restores its settled frame at completion, even after output backpressure skips
the final transient frames. See [the renderer benchmark](benchmark.md) for fixed
inputs and measurement boundaries.

## Testing

- Unit tests cover parsing, replacement, layout, art, i18n and terminal helpers.
- `tests/test_integration.py` runs the real wrapper against a fake TUI inside a
  PTY: header replacement, home paint, input, resize, exit status and fail-open.
- `tests/test_replay.py` replays reviewed real application streams from
  `tests/fixtures/terminal`, including resize boundaries and independent state
  checkpoints. Recordings supplement the synthetic PTY tests; they do not
  emulate a display or guarantee compatibility with unrecorded app versions.
- `--check` validates embedded samples, the engine and the installed binary; it
  is intentionally not a live TUI test. Known unsupported states suppress
  decoration; unrecognized state-changing extensions remain a compatibility risk.

## Deliberate non-goals

- No config file or daemon; flags and a few environment variables are enough.
- No app config/credential/plugin mutation.
- No dependency on a terminal-emulator library at runtime.
- No rewrite of the art renderer or terminal screen model for line-count
  reasons. Those modules carry the hard-won visual and ANSI behavior.
- Windows is out of scope.
