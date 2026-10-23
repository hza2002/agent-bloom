---
title: Usage and troubleshooting
order: 2
---

# Usage and troubleshooting

## Commands and themes

```sh
agent-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]
```

Run `agent-bloom --help` for current CLI options and `agent-bloom --list` for built-in themes, animations and defaults. The website command reference is generated from these code sources.

`--theme` selects a theme. `--animation` accepts one animation, a comma-separated candidate list or `random`. A candidate list selects one unique entry with equal probability. `random` includes all animations for the theme and must be used alone. Unknown names and empty candidates are errors.

Selection is fixed for the launch; resize, redraw and `/clear` do not reselect. Resume and initial prompts skip the entrance while retaining the selected static home.

`--theme`, `--animation`, element flags, `--raw` and `--check` work before or after the app name. `--help` / `--version` after the app are passed to the app. Everything after `--` is passed through. `--list` accepts an optional theme and app name, but no app runtime arguments.

For one intro followed by a static home, run `agent-bloom --no-ambient claude` (or `codex`). The home stays static after `/clear`; `--no-home` disables the entire home.

Themes are maintained in this repository; external themes and plugins are not loaded.
See [theme maintenance](../../themes.md).

[Configure the Codex home in the installation guide](get-started.md#codex).

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

The standard website preview uses Simplified Chinese.

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


## Limitations

- POSIX only; Windows is not supported.
- The home needs blank rows; narrow, short or help-heavy panes may have none.
- After application text, background drawing waits for explicit cursor positioning; text-only renderers may show no background.
- Emoji/combining sequences outside the observer's supported widths quarantine the background. Bytes pass through unchanged and header/title replacement continues. If old art cannot be erased at a safe boundary, it remains until the app repaints rather than risk erasing application content. A later full clear or an actual main-to-alternate transition via mode 1049 followed by an absolute cursor position restores decoration; a clear alone, a relative move or an unsafe terminal mode does not.
- A typed `/clear` is only a reset candidate: restoring home also requires subsequent app output and a home layout. Pasted commands cannot restore it.
- After resize, decoration waits for an application full clear; unsupported terminal modes pause decoration.
- `--check` is not a substitute for live TUI integration tests.
