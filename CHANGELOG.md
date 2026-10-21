# Changelog

## Unreleased

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
