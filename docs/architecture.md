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

## Home band

The home is the best maximal run of blank rows between two used rows. Candidates
are scored by the largest complete component group they can hold (mark,
wordmark, small text) and then by scale; two equally good runs are ambiguous and
left undecorated. Startup notices, help lists and model lines are ordinary used
rows, not special cases. An existing art block is kept while every row it owns
stays blank; otherwise it is erased and re-anchored in the new band. Application
text retires only the rows it actually touches. Unsupported widths revoke
all decoration ownership. Cleanup is emitted only before the unknown text and
only at a safe insertion boundary; otherwise old art remains until the app
repaints. A later cursor move cannot prove that old rows are still ours.

## Diagnostics

`AGENT_THEME_DEBUG` enables one structured log. Standard-library `logging` owns
formatting; a small handler adds multiprocess append, size/age rotation
(256 KiB / 24 h) and one-line atomic writes. Events use stable `event=` and
`reason=` names, with `app`, terminal size, tmux pane and `pid` on every line. A heartbeat
is written every minute. Application output, input text and exception messages
are never logged; exceptions record only type and `file:line:function` frames.

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
| `apps.py` | **The only app-specific layer.** `Profile` owns the binary, argument policy, header/title patterns, overlay class and self-check. |
| `launcher.py` | PTY transport, raw mode, resize, signals, process lifecycle, terminal restore. App-neutral. |
| `replacer.py` | Streaming replacement of startup header/title bytes, with split-sequence carry. App-neutral engine; patterns come from `Profile`. |
| `overlay.py` | Terminal screen model, ANSI parsing, blank-band selection and painting. `ClaudeOverlay`/`CodexOverlay` remain app-specific extension points. |
| `input.py` | Bounded incremental input hints, including UTF-8, control sequences and bracketed paste. |
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
- **`/clear`:** an exactly recognized typed command creates a short-lived candidate.
  Only subsequent application output with an eligible home layout restores home
  and ambient. Layout queries and animation ticks cannot confirm a candidate.
  This remains a heuristic, not an acknowledgement from the application.
- **Screen clear:** restores occupancy tracking, never session permission. A
  submitted session stays submitted across ED2, resize and surface switches.
- **Input hints:** pasted newlines never count as Enter; pasted commands cannot
  restore home. Unknown editing, navigation and truncated input disable exact
  command recognition. UTF-8 and escape sequences survive read boundaries.
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
emitted before that application's text. Before any printable run, owned
rows touched by that run are retired. Drawing and erasure remain suspended while delayed
autowrap is pending: DECSC/DECRC does not preserve that state in tmux. SGR, LF
and HT do not release this guard; supported explicit cursor movement does.

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

Frame invalidation and surface retirement have different lifetimes. Erases and
home paints invalidate the cell diff cache. Surface switches, full clears,
unknown cell edits, quarantine and resize revoke row ownership, the anchor and
the animation scene together. A new scene requires a newly eligible band. The
one-shot timeline and session permission survive retirement; the old geometry
does not. If cleanup cannot be inserted safely before an unmodelled operation,
retirement forgets ownership without issuing a delayed erase.

Observation has three mutually exclusive states: TRACKING, QUARANTINED and
BYPASS. Quarantine suppresses drawing and text-width accounting but continues
observing controls, especially screen switches and persistent modes. Only a
proven fresh surface plus an absolute cursor position can restore tracking.
BYPASS is terminal for the observer: no clear, resize or screen switch recovers
it. The read-only `passthrough` diagnostic means either suppressed state; it is
not an independent flag that can conflict with quarantine.

Incomplete control sequences are held for parsing, up to 64 KiB. Exceeding the
limit releases all held bytes and permanently bypasses the overlay for that
run, so later output cannot insert decoration inside the unfinished sequence.
Normal exit also releases shorter incomplete tails. Replacement exceptions
release the replacer's buffer and disable further replacement. Overlay parser
exceptions preserve its previously held bytes and bypass decoration; existing
paint may remain until the app repaints or exits.

## Text boundaries and deliberate fallback

The observer is not a grapheme engine. A read boundary can fall between a base
character and a later selector or combining character. Before forwarding any
printable run, retire the owned rows it touches. Keep that text boundary open
across reads, SGR, synchronized-update markers and non-positioning controls; paint
and cleanup wait until the application explicitly positions or moves its cursor.
A timer tick cannot close the boundary. Real Claude/Codex startup recordings
finish with cursor positioning, and still allow the intro to animate. A renderer
that ends on text may intentionally show no background until it positions again.

Presentation selectors U+FE00–FE0F, ZWJ, keycap combining marks and supplementary
emoji U+1F000–1FFFF quarantine background decoration. This range is deliberately
conservative; it is not an emoji-width table. All remaining bytes, including an
incomplete UTF-8 tail, pass through unchanged and header/title replacement
continues. A full clear or actual main-to-alternate transition via mode 1049
followed by an absolute cursor
position re-establishes occupancy. A clear alone, a relative move, an unsafe
mode or an app-owned cursor save does not. Repeated alternate-screen entry
and modes 47/1047 cannot prove a fresh screen; they require a full clear. Ordinary CJK and box drawing remain
supported. The tmux regressions compare actual application cells and cursor
state for VS16, ZWJ, keycaps, combining accents, flags and right-margin controls
across chunks. This bounded policy does not claim support for every Unicode or
terminal extension.

## Native integration decision

Traditional lifecycle hooks provide session semantics but not safe terminal
insertion points. Do not add a hook-to-wrapper channel: it would add ordering,
session routing and installation work while retaining the terminal observer.

A small isolated Claude 2.1.304 [Mods](https://code.claude.com/docs/en/plugins/mods/overview)
prototype successfully rendered a 24×3 colored Raster in `AbovePrompt` at 5 Hz.
Two captures 600 ms apart advanced three frames. A synthetic `prompt.submit`
event hid the band and cancelled its timer. The test deliberately dropped that
input before downstream handling, so it made no model request; production
pass-through, full artwork, clear/resume and resizing were not tested. Loading
used a session-only `--plugin-dir`; no plugin was installed or app config edited.

The [UI API](https://code.claude.com/docs/en/plugins/mods/interface) owns layout
and terminal rendering, but the tested placement is a separate band above the
prompt, not the existing centered home or header replacement. Defer migration:
consider an optional Claude-native design only if that placement change is wanted.
It would require a JS plugin and a minimum Claude version, while the current
shared Python path still serves Codex. No prototype code ships in this package.

Codex [lifecycle hooks](https://learn.chatgpt.com/docs/hooks) distinguish session
sources and prompt submission. That documentation does not establish an equivalent
public TUI cell-rendering API. Do not build a common native backend speculatively.

## Animation scheduling

Intro and slogan fade use 60 Hz deadlines; ambient sweeps use 30 Hz. App output
cannot request an early frame. A missed deadline skips catch-up frames, and the
animation clock still advances when no rows can be painted. A sweep crosses the
mark and small text, and briefly re-settles the wordmark from code; it always
restores its settled frame at completion, even after output backpressure skips
the final transient frames. Inside tmux, an ambient sweep starts only while the
pane is attached, in the current window and active; hidden panes re-check once
per period. Launcher owns one nonblocking tmux query at a time, with a 300 ms
deadline and bounded pipe reads. The animation callback returns visible, hidden,
or pending; pending schedules a short retry while transport keeps running.
Launcher polls and reaps the query even after animation stops and closes it on
exit. No tmux, a missing pane id or a failed query means visible (fail open). See [the renderer benchmark](benchmark.md) for fixed inputs and
measurement boundaries.

## Testing

- Unit tests cover parsing, replacement, layout, art, i18n and terminal helpers.
- `tests/test_integration.py` runs the real wrapper against a fake TUI inside a
  PTY: header replacement, home paint, input, resize, exit status and fail-open.
- `tests/test_replay.py` replays reviewed real application streams from
  `tests/fixtures/terminal`, including resize boundaries and independent state
  checkpoints. Recordings supplement the synthetic PTY tests; they do not
  emulate a display or guarantee compatibility with unrecorded app versions.
- `tests/test_terminal_oracle.py` optionally uses an isolated tmux server to
  compare original and decorated application cells and cursor state. It skips
  when tmux is unavailable; tmux is not a runtime dependency.
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
