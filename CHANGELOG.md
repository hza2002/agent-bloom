# Changelog

## Unreleased

- Split the home lockup into atomic mark, wordmark and small-text groups. A
  tight area now shows complete groups instead of clipping one, and the Bloom
  can run with a mark-only lockup.
- Keep a single Codex startup notice (for example a usage-limit warning) in the
  header band and re-anchor the Bloom when that band grows, so the notice no
  longer aborts the intro.
- Replace Codex's one-cell `✿` header mark with the Nerd Font
  `md-flower_poppy` glyph (U+F0D08), which reads at terminal size; the row
  keeps the original `>_ ` width. The mark requires a Nerd Font-patched font.
- Bound opt-in diagnostics to 256 KiB without backups; report decoration state
  transitions and overlay exception types without recording application text.

- Preserve delayed autowrap and split text clusters: retire decoration before
  application text and wait for explicit cursor positioning before drawing again.
  Unsupported emoji/combining sequences disable the background for the rest of
  the process; header/title replacement continues. Add real tmux regressions for
  application content, cursor state and stream boundaries.
- Parse input incrementally across UTF-8 and control-sequence boundaries;
  distinguish bracketed paste from typed reset commands. Screen clears no longer
  restore home permission after submission; reset candidates need app output.
- Verify a small Claude Mods prototype and defer migration because its native
  placement differs from the existing home/header design.

- Stop repainting Claude home decoration on application output after submission;
  `/clear` still restores the home.
- Reuse settled wordmark cells and static gradient colors during animation,
  keeping the same frames and updating cached text color after palette detection.

- Add a repeatable direct-versus-wrapper PTY benchmark for animation, home,
  output throughput and paste, with CPU and roundtrip measurements.
- Replay sanitized real Claude/Codex terminal recordings across multiple stream
  chunk sizes, checking byte preservation, occupancy, cursor and safety state.
  Include fixtures in source distributions and document capture limitations.

## 0.4.2 - 2026-10-21

- Erase decoration before wide-character text wraps onto its rows, including
  odd-width terminals; stop tracking occupancy when text scrolls at the bottom.
- Bound pending input to 256 KiB and keep output and signals responsive while
  the app is not reading input.
- Classify terminal controls by their effects instead of blocking intermediate
  CSI syntax. Queries pass through, cell edits wait for a clear, and known
  persistent mode changes isolate decoration.
- Make the overlay insertion-only; remove obsolete intro-owned screen switches
  and preserve application control sequences across all stream split points.
- Stop injecting `-c tui.effects.welcome=false` and `-c tui.show_tooltips=false`
  into Codex. Preserve its daemon startup policy and user-supplied arguments;
  document the equivalent `~/.codex/config.toml` settings instead.
- Snap the HUAWEI wordmark outlines to the octant sub-pixel lattice before
  filling, so straight edges land on whole sub-pixels and the E, H and I
  corners are no longer chipped by half-covered samples.
- Render the opening petals from transformed polygons instead of pre-sampled
  points: edges stay solid and steady while the flower opens, and a frame now
  costs roughly half as much.
- Run the Bloom, the wordmark decode and the fade-in at 60 fps with
  deadline-based pacing; app output can no longer trigger extra frames between
  deadlines.
- Cache the settled mark's glyph/colour pairs and diff each frame at cell
  granularity; identical frames emit nothing at all. Add a fixed-input benchmark
  for comparing Git refs and the worktree, with layout and cell ratio reported
  explicitly (see `docs/benchmark.md`).
- Erasing art rows invalidates the frame cache, so a row the app overwrote is
  always resent.
- Run the ambient sweep at 30 fps, halving its scheduled frame count compared
  with 60 fps.
- Refresh the decode's code glyphs at a fixed 20 Hz while the colours keep
  animating every frame, so the effect reads as decoding instead of strobing.
- Sample one sub-pixel row per petal scanline instead of three; the edge
  matches on all but a handful of cells and the growth phase costs ~25% less.
- Keep intro deadlines advancing when no blank rows remain; do not busy-loop
  or leave the intro unfinished. Apply deadline pacing to the slogan fade too.
- Invalidate frame caches on alternate-screen switches and wait for a known
  screen after resize. Keep unsupported persistent terminal modes isolated
  across clears until explicitly restored.
- Bound incomplete control-sequence buffering and preserve held bytes when
  decoration fails or the application exits.
- Use a nonblocking output FIFO so slow terminals do not stall input or signal
  handling; preserve partial writes and normal exit output in order. Restore
  the settled ambient frame when backpressure skips the end of a sweep.

## 0.4.1 - 2026-10-21

- Add standard Python packaging with a `huawei-bloom` console script for
  `uv tool install` and `pipx install`; keep the checkout symlink for development.
- Move the trademark notice out of `LICENSE` so the code is detected as MIT;
  the notice remains in `NOTICE`.
- Sanitize the demo screenshots and embedded app fixtures; no session-specific
  header details remain in the source or install package.
- Include docs and the fake TUI in the sdist so it is self-contained.
- Document clone-based installation, PATH setup and tested app versions.
- Use non-affiliated wording for the Huawei-style mark.
- Bound the replacer buffer so continuous coloured output cannot stall.
- Block signals during startup setup and drain pre-select events so a
  termination signal cannot leave the terminal raw.
- Fix filled clears wider than 256 columns and make the narrow-header check
  assert the replacement actually happened.
- Exercise input during the intro, wide overlays and large streams in tests.

## 0.4.0 - 2026-10-21

- Use one Bloom timeline for Claude and Codex; remove the Claude-only prelude.
- Keep platform-line spacing attached to the tagline and preserve centering.
- Move app-specific engine policy into `Profile`; add `docs/architecture.md`.
- Add PTY integration tests for headers, home paint, input, resize, signals,
  exit status and fail-open.
- Bump the package to 0.4.0 and simplify installation to the checkout symlink.

## 0.3.0

- Initial theme release with the Huawei mark, wordmark, Bloom,
  ambient sweep, branded headers and locale-aware Chinese copy.
