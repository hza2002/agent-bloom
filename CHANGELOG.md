# Changelog

## 0.6.1 - 2026-10-25

- Give brand artwork more room, remove duplicate titles where the artwork already
  includes the name, and bring footer copy closer without flickering during idle sweeps.
- Replace letter placeholders with Nerd Font icons for PlayStation, Xbox,
  Nintendo, Mario, Google, NVIDIA and AMD, and use Microsoft's four-square mark.
- Refine Claude badges with equal Nintendo dots, a better-aligned Mario mushroom,
  an Intel processor package with gold contacts, and a Founders Edition-inspired NVIDIA card.
- Transform NVIDIA's idle eye into flowing binary digits before rebuilding the
  solid logo, with the original silhouette and pupil preserved.
- Restore Intel's classic oval lettering from an official vector publication and
  sharpen small lettering without changing its original proportions.

## 0.6.0 - 2026-10-24

- Share title placement, reveal, decoding and light passes across vector and
  frame themes, preserving the approved Huawei/Apple timing.
- Make raster canvas dimensions, safe framing and graphic/title scale explicit
  asset data; validate motion bounds and endpoints before packaging. Generate
  the lightweight theme catalog from those validated assets.

- Fix raster-theme header row alignment, overflowing PlayStation/NVIDIA badge
  tops, and two-colour background leakage across incremental ANSI row writes.
  Restore 30 fps source cadence with floor frame selection. Use Inter vector
  title outlines, matching Apple's grid-fitting approach, instead of resizing
  system-font bitmaps. Add persisted-terminal-colour regression coverage.


- Integrate ten finalized themes: PlayStation, Xbox, Nintendo, Mario, Google,
  Android, Microsoft, NVIDIA, Intel and AMD. Merge Windows into Microsoft.
  Share title/footer rendering and retain each theme's selected hero entrance
  and idle motion. Ship offline frames, independent Claude badges, both palettes
  and solid two-colour octant/quadrant cells without runtime dependencies.
- Add complete-frame, scene-boundary, header-colour and startup replay checks;
  support two-colour production cells in website posters and playback.


- Rename the project, package and sole command to Agent Bloom (`agent-bloom`);
  remove the old `huawei-bloom` entry point. Present Huawei and Apple as built-in
  themes and update installation, maintenance docs and package checks.

- Keep ambient animation running in visible, unfocused tmux splits; pause only
  when detached, in a background window or occluded by another zoomed pane.
- Fill the isolated orange-band pixel notch in Apple's large bite contour.

- Unify Apple entrances around the same six-colour artwork and three lines:
  `Choose your superpower`, `Think different`, `Apple silicon · macOS`. Match Huawei’s three-line typography. Strengthen the idle sweep and briefly
  decode the APPLE wordmark before restoring its exact static frame.

- Fix Claude Apple intros being quarantined by our own U+1FB85 header block.
  Recognize only the renderer's known block glyphs as one-cell characters;
  retain isolation for emoji. Use the approved three-row six-colour pixel Apple mark
  in Claude’s header. Calculate large artwork bounds from the source outline
  to prevent clipped sides in both Apple animations.

- Render Apple with the same solid octant/quadrant blocks as Huawei, without
  edge antialiasing; use Inter outlines and preserve overlapping
  font strokes. Fit a monochrome header mark without clipping its leaf, and use
  the Apple Nerd Font badge in Codex. Remove Constellation's coarse rim flash.

- Separate built-in theme artwork, copy, palettes and scene factories from app
  adapters and the terminal engine. Huawei remains the default, with its frames
  checked against a pre-refactor rendering snapshot.
- Add the Apple theme with Spectrum and Constellation entrances, matching static
  artwork and brand copy. Replace the unreleased Orbit prototype.
- Add `--animation NAME[,NAME...]`, `--animation random` and standalone `--list`.
  Candidate lists choose one variant per launch; resize and clear preserve it.
  `--check` exercises every candidate. No external themes or plugins are loaded.

- Add `--ambient` / `--no-ambient` to control the idle sweep independently of
  the opening Bloom and static home. Disabling ambient also stops its timer
  and tmux visibility queries, including after `/clear`.
- Isolate decoration after custom tab-stop controls or unmodelled tab movement,
  preventing wrapped application text from being mistaken for blank rows.
  Add a real tmux regression for the previously overwritten character.
- Test real shell Ctrl-Z/fg and terminal closure with an app ignoring SIGHUP;
  exercise resume, streaming, cancellation, clear and resubmission using the
  synthetic TUI through the actual wrapper and PTY.
- Install tmux explicitly in the test matrix and validate wheel imports and
  rendering outside the source checkout.

## 0.5.2 - 2026-10-22

- Preserve application and main-screen text when unsupported Unicode, screen
  switches or unmodelled terminal edits invalidate decoration ownership; if
  cleanup cannot be inserted safely, old art remains until the app repaints.
- Recover decoration only after a proven fresh surface and absolute cursor
  position; repeated alternate-screen entry no longer counts as a clear, and
  oversized incomplete control sequences permanently disable the overlay.
- Discard the old animation scene when its screen or layout becomes invalid,
  requiring a new eligible blank band before drawing again.
- Query tmux visibility asynchronously so a slow query does not pause input or
  output forwarding, with bounded reads, a deadline and child-process cleanup.
- Restore the home-layout benchmark and measure the current ambient wordmark
  decode, retaining support for comparisons with historical revisions.

## 0.5.1 - 2026-10-22

- Skip ambient frames while tmux reports that the pane is detached, in a
  background window or not the active pane. Check once per ambient period;
  without tmux, without a pane id or after a failed query, keep the animation
  (fail open).
- Refresh the README hero and demo GIF for the idle wordmark decode, small-text
  sheen and unified platform rules.

## 0.5.0 - 2026-10-22

- Carry the ambient sweep across the whole home lockup, not just the mark:
  HUAWEI briefly re-settles from code at the start of each sweep, while the
  slogan/tagline/platform block gets a visible sheen. Neutral copy lifts to the
  brand red and the red rules to ink. The pass is synchronized with the
  existing 2-second sweep and leaves the settled palette at its end.
- Render the platform line's flanking rules at the same red as its text; the
  separate dim rule colour is gone.
- Replace ad-hoc debug writes with standard-library logging: structured
  `key=value` events, session context, a 60-second heartbeat, row ranges,
  size/age rotation (256 KiB / 24 h) and sanitized exception frames. Application
  output and input text are never logged.
- Quarantine background decoration after an unsupported character width and
  recover on a full clear or alternate-screen entry followed by an absolute
  cursor position. Never erase a row the app already owns; blank owned rows are
  cleared and app-owned rows are forgotten.
- Retire only the rows an application text run touches; a notice above the art
  no longer clears and redraws the whole animation. Unsupported-width text
  keeps its final erase until the next explicit cursor boundary so a split
  glyph cluster is never cut, and passthrough flushes any carried sequence.
- Split the home lockup into atomic mark, wordmark and small-text groups. A
  tight area now shows complete groups instead of clipping one, and the Bloom
  can run with a mark-only lockup.
- Choose the home from the largest complete blank row band between the app's
  used rows. Startup notices, help lists and model lines are ordinary used
  rows, so a one-line warning no longer aborts the intro or needs per-app row
  limits. Keep an existing art block while every row it owns is still blank.
- Replace Codex's one-cell `✿` header mark with the Nerd Font
  `md-flower_poppy` glyph (U+F0D08), which reads at terminal size; the row
  keeps the original `>_ ` width. The mark requires a Nerd Font-patched font.

- Preserve delayed autowrap and split text clusters: retire only touched rows
  before application text and wait for explicit cursor positioning before
  drawing again. Unsupported emoji/combining sequences quarantine the
  background; header/title replacement continues. Add real tmux regressions for
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
