# Architecture

`huawei-bloom` is a transparent PTY proxy that adds branding at the edges of the
wrapped TUI. The app is never modified, and the wrapper must never be required
for the app to work.

## Invariants

These are product requirements, not implementation suggestions:

- The app's config, credentials, plugins and binary are untouched.
- Every decoration path is best-effort. Any overlay/replacer failure drops the
  decoration and lets the original bytes through.
- Input is never blocked by animation. The app remains usable while the intro
  runs.
- The overlay only draws into cells the app currently leaves blank.
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

## Modules

| Module | Responsibility |
| --- | --- |
| `huawei-bloom` | Executable entry point; makes the checkout importable. |
| `cli.py` | Flag parsing, help, `--check`, exit statuses. |
| `apps.py` | **The only app-specific layer.** `Profile` owns the binary, argument policy, header/title patterns, overlay class, home top, startup args and self-check. |
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
- **Resize:** the PTY is resized, the overlay re-lays out, and stale decorations
  are erased.
- **No alternate screen / unexpected output:** the overlay stays off; bytes pass
  through. This is the fail-open path.

## Testing

- Unit tests cover parsing, replacement, layout, art, i18n and terminal helpers.
- `tests/test_integration.py` runs the real wrapper against a fake TUI inside a
  PTY: header replacement, home paint, input, resize, exit status and fail-open.
- `--check` validates embedded samples, the engine and the installed binary; it
  is intentionally not a live TUI test. Real TUI changes fail open.

## Deliberate non-goals

- No config file or daemon; flags and a few environment variables are enough.
- No app config/credential/plugin mutation.
- No dependency on a terminal-emulator library at runtime.
- No rewrite of the art renderer or terminal screen model for line-count
  reasons. Those modules carry the hard-won visual and ANSI behavior.
- Windows is out of scope.
