# Agent Bloom

[简体中文](README.md) | **English**

Selectable terminal themes for **Claude Code** and **Codex CLI**: branded icons, animated entrances, home artwork and idle sweeps.
A PTY wrapper with no runtime dependencies. App config, credentials and plugins stay untouched.

| Theme | Entrances | Visual style |
| --- | --- | --- |
| **Huawei** (default) | `bloom` · unfolding petals | Eight-petal mark, HUAWEI lettering and red sweeps |
| **Apple** | `spectrum` · band assembly / `constellation` · particle convergence | Six-colour pixel Apple, APPLE lettering and a decode sweep |

Pin one entrance or randomly select from a candidate list on each launch. Themes are maintained in this repository.

<p align="center">
  <img src="docs/hero.png" alt="agent-bloom Claude Code and Codex homes" width="900">
</p>

<p align="center"><sub>Claude Code / Codex · Simplified Chinese · 95×55 / 111×55 cells · demo (session details hidden)</sub></p>

## Features

- Built-in Huawei / Apple artwork rendered with octant glyphs, with quadrant fallback
- Selected entrance on launch, then an idle sweep every 8 seconds, only in cells the app treats as blank
- Home artwork, header icons and names follow the selected theme
- Chinese follows the locale: Simplified or Traditional
- `/clear` restores the home; a non-empty submit stops ambient and clears the art
- Direct commands, non-TTY runs and `--raw` bypass the wrapper
- For Codex home, disable welcome in your config; the wrapper injects no startup arguments

## Demo

<p align="center">
  <img src="docs/intro.gif" alt="agent-bloom launch and idle sweep: Claude Code and Codex" width="900">
</p>

<p align="center"><sub>Huawei theme · Left: Claude Code · Right: Codex CLI · Simplified Chinese · the 8-second idle interval is compressed for the demo</sub></p>

## Install

Requires macOS or Linux, Python 3.9+, and a Unicode/truecolor terminal; Ghostty is recommended.  
The terminal font must cover the chosen Chinese script; the Codex header mark also needs Nerd Font glyphs.

Clone, then install with `uv` or `pipx`:

```sh
git clone https://github.com/hza2002/agent-bloom
cd agent-bloom
uv tool install .
# or
pipx install .
```

If the command is not on your PATH, run `uv tool update-shell` (or `pipx ensurepath`).

For development, link the checkout directly:

```sh
mkdir -p ~/.local/bin
ln -sf /path/to/agent-bloom/agent-bloom ~/.local/bin/agent-bloom
```

Add shell functions:

```zsh
_agent_bloom() {
  local app=$1; shift
  (( $+commands[agent-bloom] )) && { command agent-bloom "$app" "$@"; return; }
  command "$app" "$@"
}
claude() { _agent_bloom claude "$@"; }
codex() { _agent_bloom codex "$@"; }
```

`command claude` / `command codex` always bypasses the wrapper.  
Uninstall with `uv tool uninstall agent-bloom` (or `pipx uninstall agent-bloom`); for a symlink install, remove the functions and `~/.local/bin/agent-bloom`.

## Usage

```sh
agent-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]
```

| Option | Default | Purpose |
| --- | --- | --- |
| `--theme NAME` | `huawei` | Built-in theme: `huawei` / `apple` |
| `--animation SELECTION` | theme default | One name, comma-separated random candidates, or `random` |
| `--list` | | List themes and animations without launching an app |
| `--logo` / `--no-logo` | on | Selected theme’s header mark only |
| `--header` / `--no-header` | on | Selected theme’s header name |
| `--title` / `--no-title` | off | Window title; off by default to keep tmux pane search working |
| `--home` / `--no-home` | on | Intro, ambient, home; `--no-home` disables the overlay and leaves app settings unchanged |
| `--ambient` / `--no-ambient` | on | Idle sweep; `--no-ambient` keeps the intro and static home without periodic animation or tmux visibility queries |
| `--raw` | off | Run the app untouched |
| `--check` |  | Check embedded patterns, engine, binary and version |

The Huawei theme’s Codex header mark is the Nerd Font glyph `md-flower_poppy` (U+F0D08) and requires a Nerd Font-patched terminal font. If the glyph is missing, `--no-logo` keeps the original `>_`.
Element flags, `--raw` and `--check` work before or after the app name; `--help` / `--version` after the app are passed to the app.  
Everything after `--` goes to the app.

For one intro followed by a static home, run `agent-bloom --no-ambient claude`
(or `codex`). The home stays static after `/clear`; `--no-home` disables the
entire home regardless of the ambient setting.

Select Apple (random entrance on each launch):

```sh
agent-bloom --theme apple codex
agent-bloom --theme apple --animation spectrum claude
agent-bloom --theme apple --animation spectrum,constellation codex
agent-bloom --theme apple --animation random codex
agent-bloom --list
agent-bloom --theme apple --list
```

- `spectrum` assembles six-colour bands; `constellation` converges six-colour particles. Both settle into the same rainbow Apple and home composition.
- Apple shares three unpunctuated lines across apps and animations: `Choose your superpower`, `Think different`, and `Apple silicon · macOS`.
- Huawei defaults to `bloom`; Apple defaults to `random`. A comma list selects one unique candidate with equal probability, not a playlist. `random` includes all animations in the selected theme and must be used alone.
- Selection is pinned for the launch, including resize, redraw and `/clear`. Resume and initial prompts still skip the entrance; the static home uses the selected variant.
- `--theme` and `--animation` work before or after the app name and accept `--flag=value`. Everything after `--` goes to the app. Unknown names and empty candidates are errors.
- `--list` accepts an optional `--theme` and app name, without execution options. `--check` exercises every candidate and checks the app binary.
- Apple uses a three-row six-colour pixel mark with half-block stripes and transparent edges in Claude’s header and Nerd Font’s `fa-apple` (U+F179) in Codex’s header. For Codex, use `--no-logo` if the font lacks that glyph.

Themes are maintained in this repository; external themes and plugins are not loaded.
See [theme maintenance](docs/themes.md).

### Codex home configuration

Codex's native welcome animation occupies the blank area Bloom needs. Turn it off in `~/.codex/config.toml`:

```toml
[tui.effects]
welcome = false
```

To also hide the dynamic hint below the composer (for example `← for agents`), set this in your existing `[tui]` table:

```toml
[tui]
show_tooltips = false
```

Both settings apply to the corresponding `CODEX_HOME`, including Codex windows not launched through the wrapper. The wrapper injects no config overrides, preserving Codex's daemon startup policy and the arguments you explicitly pass. `--no-home` does not re-enable welcome when your config disables it.

## Behavior

- A fresh session plays the intro; the header and prompt are usable immediately.
- `claude -c` / `--resume`, `codex resume` / `fork`, and an initial prompt skip the intro.
- Empty Enter does not interrupt the intro; a non-empty submit stops ambient.
- `/clear` restores the home and ambient when the screen remains eligible.
- Direct / non-interactive commands run without a PTY.

## Compatibility

Verified with Claude Code v2.1.305 and Codex v0.163.0. App updates can change headers or renderers; the wrapper fails open and leaves the app untouched.

## Language

Chinese follows the process locale:

- `zh_TW` / `zh_HK` / `zh_MO` → Traditional
- `zh_CN` / `zh_SG` → Simplified
- non-Chinese locale → Traditional

Override either way:

```sh
AGENT_THEME_LANG=zh-Hans agent-bloom claude
AGENT_THEME_LANG=zh-Hant agent-bloom codex
```

README screenshots use Simplified Chinese.

## Environment

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENT_THEME_GLYPHS` | auto | `octant` / `quadrant`; detects Ghostty, including inside tmux |
| `AGENT_THEME_PALETTE` | auto | `light` / `dark`; from `COLORFGBG` or macOS appearance |
| `AGENT_THEME_CELL_RATIO` | auto, `2.12` fallback | Terminal cell height/width ratio |
| `AGENT_THEME_LANG` | auto, Traditional fallback | `zh-Hant` / `zh-Hans` |
| `AGENT_THEME_DEBUG` | unset | Structured diagnostic log path; off by default, one file capped at 256 KiB or 24 hours, cleared and rewritten when exceeded, no backups |

For investigation, launch with `AGENT_THEME_DEBUG=/tmp/agent-bloom.log agent-bloom claude` (or `codex`). The log uses `key=value` events with time, `pid`, `app`, terminal size and tmux pane. Core events include `session`, `band`, `frame`, `state`, `touch`, `input`, `unsupported` and `exception`, plus a `heartbeat` every 60 seconds. It records row numbers, flags, reasons and durations only; application output and input text are never logged. Panes may share the path; records interleave in time without dropping bytes. Unset the variable to stop logging.

With tmux `automatic-rename` on, the window is named `claude` / `codex`; manually named windows are untouched.  
Ambient pauses while detached, in a background window, or hidden behind another zoomed pane. Unfocused split panes in a visible window still animate. It re-checks every 8 seconds and normally resumes within one period plus query time. Queries run asynchronously while input continues to flow. Without tmux, the animation runs as before and incurs no visibility query.
`#{pane_current_command}` remains Python; use `#{window_name}` / `#W` in status formats.

## Verify

```sh
python3 -m unittest discover -s tests -v
./agent-bloom --check claude
./agent-bloom --check codex
```

`--check` validates embedded fixtures, engine, binary and version; it does not run a live TUI or detect future renderer changes. Renderer changes fail open.

See [the benchmark](docs/benchmark.md) for fixed-input renderer comparisons:

```sh
python3 tools/benchmark.py v0.4.1 8bd48b7 worktree
```

## Project layout

```text
agent-bloom               executable entry point
agent_theme/              CLI, PTY, overlay, animation, i18n, art
docs/                     README images, animation and architecture
CHANGELOG.md              release history
tests/                    stdlib unittest
tools/                    reproducible renderer benchmark
```

## Provenance and license

The Bloom engine, overlay model and Huawei-style artwork are adapted from
[pangu-cli-theme](https://github.com/Lightly20110815/pangu-cli-theme) (MIT, commit
`cefaa53080dd625be9bcc8060051fbbf2dc89723`).

The HUAWEI wordmark is not typeset from a font: `agent_theme/themes/assets/huawei.json`
stores the `huawei-mark.svg` outlines as polygons, rasterised at 2×4 octant
sub-pixels per character cell (2×2 quadrants on terminals without octants).

The Apple silhouette comes from Simple Icons; APPLE lettering uses Inter 4.1 Medium outlines, not an official Apple wordmark. See [NOTICE](NOTICE) for asset provenance and licenses.

Code and layout are MIT-licensed. HUAWEI, the Huawei flower logo and the HUAWEI
wordmark are trademarks of Huawei Technologies Co., Ltd. and are not covered by
that license. Apple and the Apple logo are trademarks of Apple Inc. This project is not affiliated with Huawei, Apple, Anthropic or OpenAI.

## Limitations

- POSIX only; Windows is not supported.
- The home needs blank rows; narrow, short or help-heavy panes may have none.
- After application text, background drawing waits for explicit cursor positioning; text-only renderers may show no background.
- Emoji/combining sequences outside the observer's supported widths quarantine the background. Bytes pass through unchanged and header/title replacement continues. If old art cannot be erased at a safe boundary, it remains until the app repaints rather than risk erasing application content. A later full clear or an actual main-to-alternate transition via mode 1049 followed by an absolute cursor position restores decoration; a clear alone, a relative move or an unsafe terminal mode does not.
- A typed `/clear` is only a reset candidate: restoring home also requires subsequent app output and a home layout. Pasted commands cannot restore it.
- After resize, decoration waits for an application full clear; unsupported terminal modes pause decoration.
- `--check` is not a substitute for live TUI integration tests.
