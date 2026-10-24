# Maintaining built-in themes

For the design-to-release workflow, independent badge design, prototype checks
and the agreed theme backlog, see [主题制作流程](theme-production.md).

Themes are Python modules maintained and shipped with this project. There is no
external manifest format, directory scan, plugin discovery, or user-supplied code.
`--theme huawei` is the default. `--list` enumerates all 12 built-in themes.
One theme and animation variant are resolved for the process and survive clear,
resize and recovery. Huawei defaults to `bloom`; Apple defaults to `random`.

## Ownership

| Location | Owns |
| --- | --- |
| `agent_theme/themes/__init__.py` | `Theme`, `Animation`, per-app `Brand` copy, candidate resolution, explicit registry |
| `themes/huawei.py`, `themes/assets/huawei.json` | Huawei copy, palettes, badge fallback and vector artwork |
| `themes/huawei_bloom.py` | Petal-specific Bloom and decoding animation |
| `themes/apple.py`, `themes/assets/apple.json` | Apple copy, variant palettes and artwork |
| `themes/apple_motion.py` | Spectrum and Constellation scenes |
| `tools/build_apple_art.py`, `themes/assets/apple.svg` | Reproducible Apple polygon source |
| `art.py`, `assets/octants.json` | Shared glyph mapping, rasterization, layout, header badge rendering |
| `scene.py` | Shared frame diff cache and ANSI encoder |
| `animation.py`, `overlay.py` | Scheduling, session permission and safe row ownership |
| `apps.py` | Claude/Codex patterns, argument classification and fixed header slots |

The `Brand` object is a theme bound to one app's copy, not another global theme.
Assets, palettes and copy on a `Theme` are treated as read-only. Rendering caches
belong to each mark or scene. Header badge caches include theme and glyph mode.
The palette roles are `ink`, `soft`, `muted`, `accent` and `bg`; background detection
selects the current theme's light/dark palette and returns a copy when overriding
the background colour.

## Add a theme

For a baked frame theme, follow “Adding or rebuilding a frame theme” below.
The steps here describe a custom vector scene such as Huawei or Apple.

1. Add a module under `agent_theme/themes/` exporting a `THEME`. Supply its name,
   two palettes, copy for both apps, a one-cell Codex badge, an artwork loader and
   scene factory. Delay imports of `art` and scene classes until the factory runs,
   after terminal capability detection. Follow `apple.py` for variant registration.
2. Supply `mark` and `word` polygon lists, nonzero `logo_bbox` and `word_bbox`,
   and a `gradient`: radial (the default), linear, or discrete bands. Coordinates
   are vector units, not terminal cells. Keep source/provenance beside the art.
   Huawei additionally has an `origin` used only by its petal animation.
3. Keep header copy within 11 cells for Claude and 12 cells for Codex. The app
   adapter pads shorter names and rejects longer names. Titles are separate
   from header copy. Theme text must not contain terminal control characters.
   Claude's badge is rasterized into its existing 8/9/9-cell rows.
4. Add the name to `THEME_NAMES` and an explicit import in `get_theme()`. Update
   CLI help and the README choice lists. No change to PTY or input code is needed.
5. Register at least one `Animation` and set `default_animation` to its ID or
   `random`. Keep IDs stable, lowercase and free of commas; `random` is reserved.
6. If artwork lives in JSON, put it under `themes/assets/`; package rules already
   include that directory. Verify the wheel outside the source checkout.

There is deliberately no generic animation configuration language. A different
movement is a small scene implementation; it can reuse the common `Scene` encoder.
Do not make the transport or layout branch on theme or app names.

## Add an animation

1. Implement a scene factory with the contract below; keep renderer imports lazy.
2. Add an `Animation(key, label, create_scene, load_art=None, slogan=None,
   tagline=None)` to the theme's `animations` tuple. Omitted fields inherit the
   theme's artwork and per-app copy. Variant copy changes the home, not the header.
3. If the final colours or geometry differ, supply a variant artwork loader.
   The scene and static renderer must receive the same selected `Theme` snapshot.
4. Add the ID to an explicit candidate list to opt in, or use `random` to include
   every registered animation. Adding an animation changes the `random` pool.
5. Test final-frame equivalence, row/column bounds, palette changes, both glyph
   modes, narrow layouts, and the real wrapper for both apps.

`Theme.candidates()` validates and deduplicates the entire comma list before
launch. Whitespace around IDs is ignored; empty items and unknown IDs fail with
exit status 2. `random` must stand alone. Multiple unique candidates have equal
probability; a single candidate does not call the random generator. Repeated
CLI selection options use the final value, matching existing theme options.

`Launcher` calls `select_animation()` once and retains the result. Do not choose
inside a scene factory: resize and surface recovery recreate scenes. The chosen
ID is included in the diagnostic session event. `--check` resolves every
candidate explicitly instead of drawing a random sample. `--list` does not
choose, load renderer modules, probe a terminal, or require app binaries.

Apple artwork can be regenerated offline with `python3 tools/build_apple_art.py`.
The source SVG, baked Inter lettering, sampled polygons and provenance are shipped
together. Apple uses the same solid octant/quadrant rasterization as Huawei:
coverage is thresholded into solid blocks; word vertices snap to the sub-pixel
lattice. Do not blend edge colours with the background or add antialiasing.
`word_fill=nonzero` preserves overlapping font strokes. The large mark's bounds
are calculated from all sampled SVG points, rounded outward; do not hand-tighten
them. The former horizontal box (2.8–21.4) clipped the source outline
(2.22504–21.775), causing flat sides in both animations.

`mini_grid` is a dedicated 18×12 solid pixel drawing for Claude's three-row
header, optically centred on the body, with a detached leaf and right bite.
`mini_grid_quadrant` adapts the silhouette to six vertical samples so fallback
rendering does not merge the leaf into the shoulder. It uses the existing
8/9/9-cell footprint and the same block glyphs as Huawei. The approved source is
`assets/apple-header.json`, embedded into `apple.json` by the artwork builder.
`header_cells` stores each block's bit pattern, foreground RGB and optional
background RGB for both glyph modes. Interior cells use two solid stripe colours;
edge cells keep the default terminal background. Both colours reset at each row
end. The six-colour header is shared by both animations and both palettes.
`mini_grid` remains a monochrome silhouette for geometry helpers; the live header
uses `header_cells`. Codex retains its one-cell Nerd Font badge.

Silver and monochrome alternatives remain in `prototypes/apple-pixels/` only.
There is no additional CLI option or runtime conversion dependency.
The source silhouette comes from Simple Icons, not directly from Apple;
Apple's [identity guidelines](https://www.apple.com/legal/sales-support/certification/docs/logo_guidelines.pdf)
serve as a visual reference. The pixel badge is a small-size adaptation.

To regenerate the lettering, obtain Inter 4.1's `InterVariable.ttf` from
https://github.com/rsms/inter/blob/v4.1/docs/font-files/InterVariable.ttf and run
`uv run --with fonttools --no-project python tools/build_apple_word.py /path/to/InterVariable.ttf`,
then `python3 tools/build_apple_art.py`. The baked asset records the source font
hash. FontTools is a regeneration tool only; the installed package remains
standard-library-only. The glyphs are typography, not an official Apple wordmark.

Apple scenes use full-strength artwork colours. Palette changes refresh word
colours; animation fades and sweeps do not introduce static edge opacity.
Constellation settles without a bright rim; do not reintroduce a cell-wide outline
flash. Tiny layouts omit the vector wordmark below three rows rather than rendering
broken letter counters.

## Scene contract

The factory receives `cols`, `rows`, `pal`, `brand`, `lock` and `top`. A scene
reports `ok=False` when its required component is absent; the scheduler then
uses the static home. Otherwise it provides:

- `lock`, `top`, positive `duration`, and bounds `x0`, `x1`, `y0`, `y1`.
- `frame(seconds)` and `ambient_frame(progress)` returning maps of
  `(row, column)` to `(one-cell glyph, RGB)`. Ambient progress is in `[0, 1]`.
- A settled `frame(duration)` matching the mark/word part of `art.home_rows`.
- A `pal` attribute that may be replaced after background detection.
- An initially empty `prev_cells` cache for the inherited `ansi()` and
  `invalidate()` methods.

Scenes never write to stdout, read input, sleep, query tmux or switch screens.
The scheduler chooses time; the overlay supplies eligible rows to the encoder.
The small-text reveal and sheen remain shared. `--no-ambient` stops periodic
animation for every theme. Theme failures use the existing decoration fail-open
path and must not change app bytes or input handling.

## Verification

```sh
python3 -B -m unittest discover -s tests -v
./agent-bloom --theme apple --check claude
./agent-bloom --theme apple --check codex
```

`test_themes.py` checks both profiles, fragmented headers, separate theme/palette
instances, scene bounds, settled/static equivalence, session/resize safety and
real startup recording replay. The PTY integration suite exercises both Apple variants through
the actual wrapper. `test_render_equivalence.py` retains pre-refactor Huawei
digests for both apps, palettes and glyph modes, including 1,904 animation frames.
Do not regenerate those digests merely to make a refactor pass.

Inspect opening, settled home and ambient in a real terminal at normal and small
sizes, with both palettes and glyph modes. A green replay does not judge visual
appearance. The benchmark's historical adapter continues to measure Huawei so
comparisons with older Git revisions use the same scene.

Apple and Huawei share the footer typography: a bold primary line, a tracked
secondary line and an accent-coloured platform line with rules. Both Apple
entrances inherit the same art loader and copy. Apple's idle effect uses a
stronger diagonal light pass and a brief left-to-right code decode of APPLE,
then returns exactly to its static artwork. The shared 8-second idle period,
2-second sweep and submit/visibility safeguards remain unchanged.

Apple's `logo_notch_fill_box` bounds the optical correction around the bite.
Only a single missing edge pixel with filled vertical neighbours is restored;
the SVG source, other contours and the approved header badge stay unchanged.

## Offline frame themes

Ten finalized designs are registered explicitly alongside Huawei and Apple:
`playstation`, `xbox`, `nintendo`, `mario`, `google`, `android`, `microsoft`,
`nvidia`, `intel`, `amd`. Windows is merged into Microsoft. Each uses only its
selected entrance; prototype comparison variants are not installed.

`builtin.py` owns lightweight metadata and factories; `raster.py` adapts baked
frames to the shared layout, glyph modes and Scene encoder. Renderer imports stay
lazy. Header badges are independent 18×12 drawings with palette-specific two-colour
cells and the existing 8/9/9 footprint. Opaque hero cells may use two solid colours;
transparent edges reserve the terminal background and every run restores it.
The runtime requires no browser, Node, Pillow, fonts, network or other package.

To rebuild: serve `prototypes/`, import `exportTheme` from `theme-lab/export.js`
in the local page and save each result as `<theme>.json`. Run
`uv run --no-project --with fonttools python tools/build_theme_art.py /path/to/<theme>.json agent_theme/themes/assets/<theme>.json /path/to/InterVariable.ttf` to pack its RLE frames
with zlib. Sources, attribution and original SVG references are shipped alongside
the result. The export uses 30 fps at 192×128, both palettes, a normalized idle
cycle, and separate title/header masks. The drawing modules remain the source of
truth for hero motion. English titles use the same Inter 4.1 Medium outline extraction and grid fitting
as Apple; pass the font path as the third builder argument. The Chinese Nintendo
title uses Noto Sans SC Medium vector outlines (use `--with brotli` when building
from its WOFF2 subset). Its OFL license is shipped beside the assets. These titles are typography, not vendor wordmarks.

`catalog.json` stores only names, copy, colours and selected animation IDs, so
listing/argument validation never loads frames. Generate it from validated assets
with `python3 tools/build_theme_art.py --catalog`; do not maintain another copy of
theme metadata by hand. Raster scenes share the Apple title timeline and the existing
small-text reveal/sheen, input handling, resume/clear rules and idle scheduler.

Validation includes `tests/test_builtin_themes.py`, the full transport suite,
recorded Claude/Codex startup replay, installed-wheel checks and website export.
Automated PTY tests use a synthetic TUI; they do not claim live vendor-app visual
acceptance. Check terminal font rendering before release.

## Raster regression safeguards

Header rows share the same left origin; the first row is cropped only on the
right to eight cells. Source badges must leave that last top cell transparent.
Every two-colour ANSI run restores default background before the next write.
The 60 Hz scheduler selects the current 30 fps source frame with floor sampling,
not rounding. `test_raster_regressions.py` checks these contracts plus persisted
terminal colours across entrances, handoffs and idle for all ten raster themes.
The unfixed isolated fixture fails these tests; tmux confirms the colour-state
regression independently. Final-frame dictionary equality alone is insufficient.

## Shared theme architecture

```text
Theme drawing + copy + source records
              ↓ export.js
Build tool → validated baked asset → generated catalog
                       ↓                 ↓
              shared renderer     registry / CLI listing
                       ↓
       shared layout + title effects + footer effects
                       ↓
                Scene / Overlay / PTY
```

`text_motion.py` owns title placement, reveal, decode and diagonal light passes.
New frame themes inherit the approved Apple title timing. Huawei uses the same
effects with its existing lock times and glyph source; Huawei/Apple frame
snapshots protect their approved appearance. Footer reveal and sheen remain in
the existing shared `art.py` / `animation.py` path. A theme only animates its hero.

`asset_spec.py` defines the internal baked-asset contract. The runtime reads
`width`, `height`, `word_width`, `word_height` and `intro_seconds`; these are no
longer renderer constants. Higher-resolution assets need no layout changes, but
their source drawings must also support the new resolution. Enlarging an old
bitmap alone adds no detail. Header dimensions remain fixed by the app slot.

Optional `layout` fields live beside each theme drawing and pass through export:

| Field | Default | Meaning |
| --- | --- | --- |
| `view_box` | Full canvas `[0, 0, width, height]` | Common crop for **every** static/intro/idle frame, in source pixels; right/bottom exclusive |
| `logo_scale` | `1.04` | Large-graphic width relative to the title's allocated width |
| `min_word_rows` | `3` | Smallest readable title height in terminal rows |

The builder measures `visual_bbox` from both static palettes and `motion_bbox`
from every baked frame. It rejects any `view_box` that clips the motion bounds.
The optional source `wordBox` similarly sets the title's `word_bbox`; it uses
title-canvas coordinates and must contain all rendered title outlines. Both
title and hero framing feed the same adaptive layout.

A static-only tight crop is unsafe: moving particles or limbs can extend farther.
There is no per-frame auto-crop, so artwork cannot shift or resize at handoff.
Existing themes retain full-canvas framing until their larger composition is
visually accepted. The shared layout still chooses the largest complete group
that fits the app's actual blank area, and recalculates after terminal resize.

### Adding or rebuilding a frame theme

1. Keep drawing, copy, `headerIcon`, animation definitions and any `layout`
   overrides in `prototypes/theme-lab/themes/<id>.js`. Use `productionVariants`
   only when the lab contains additional comparison animations. Its order is
   the installed order and the first variant is the default. New definitions
   need no theme-name condition inside `export.js` or the renderer.
2. Register a new ID explicitly in the lab catalogue and `THEME_NAMES`. Save
   source/provenance/license files beside its production asset.
3. Export with `exportTheme(id)`. Pack with the builder command above, passing
   a font that covers the **entire** title. Missing glyphs fail the build rather
   than silently retaining a system-font bitmap. FontTools is build-only.
4. Run `python3 tools/build_theme_art.py --catalog`, then `make themes-check`.
   The check validates dimensions, colours, every compressed frame, timing,
   exact intro/idle endpoints, safe framing and catalog consistency. It runs
   in package CI without installing font or browser dependencies.
5. Run `make test` and `npm --prefix website run build`. Inspect both palettes,
   small/medium/large available areas, intro handoff, idle and window resize in
   the terminal. `tests/test_theme_architecture.py` includes a nonstandard
   canvas fixture, so resolution and framing stay independent of theme names.

This is an internal asset format. Theme discovery remains explicit; installed
themes execute no downloaded code. The CLI and end-user setup are unchanged.
