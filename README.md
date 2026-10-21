# huawei-bloom

Huawei-style terminal branding for **Claude Code** and **Codex CLI**, installed as the `huawei-bloom` command.

`huawei-bloom` runs the real CLI behind a small PTY proxy. It does not modify
app config files, credentials or plugins, and writes no config, cache or daemon.
The only optional write is the `AGENT_THEME_DEBUG` log. Everything is Python
standard library.

## What it changes

- **Claude Code**: the three-row mascot becomes the Huawei flower; the header
  becomes `盤古·Claude`; the optional title becomes `✳ 盤古·Claude`.
- **Codex**: `✿ 盤古 · Codex` (or `>_ 盤古 · Codex` with `--no-logo`); the
  optional title is `✿ 盤古 · Codex`.
- **Background home**: on a fresh interactive session a one-shot Bloom plays,
  then a slow sweep repeats every 8 seconds while blank rows remain. The art is
  composited into cells the app itself considers blank, so it never covers the
  header, prompt or status line and never blocks typing.
- A prompt supplied on the command line, `claude -c`, `--resume`, and
  `codex resume`/`fork` open directly without the intro.
- `/clear` restores the home and the ambient sweep.
- Window titles are off by default so tmux pane search keeps working.

## Requirements

- macOS or Linux, Python 3.9+.
- Chinese copy follows the locale: `zh_TW`/`zh_HK`/`zh_MO` use Traditional,
  `zh_CN`/`zh_SG` use Simplified; non-Chinese locales default to Traditional.
  Set `AGENT_THEME_LANG=zh-Hant` or `zh-Hans` to force either script. The
  terminal font must include the chosen CJK glyphs.
- A Unicode terminal with truecolor. Ghostty is recommended because its
  octant glyphs give the sharpest logo; other terminals fall back to quadrants.
- tmux is supported. The proxy asks tmux which terminal is attached when it
  needs to choose glyphs.

## Install

Keep one canonical checkout. The simplest install links the launcher
directly to it:

```sh
mkdir -p ~/.local/bin
ln -sf /path/to/huawei-bloom/huawei-bloom ~/.local/bin/huawei-bloom
```

A copied install (for example into dotfiles) works too, but the copy is a
snapshot: run tests and `--check` from the checkout, then sync the runtime
after changes:

```sh
INSTALL=~/.local/lib/huawei-bloom
mkdir -p "$INSTALL" ~/.local/bin
rsync -a --exclude=__pycache__ agent_theme "$INSTALL"/
cp huawei-bloom README.md LICENSE NOTICE "$INSTALL"/
ln -sf "$INSTALL/huawei-bloom" ~/.local/bin/huawei-bloom
```

Add shell functions so normal commands use the wrapper. `command claude`
bypasses it at any time.

```zsh
claude() {
  if command -v huawei-bloom >/dev/null 2>&1; then
    huawei-bloom claude "$@"
  else
    command claude "$@"
  fi
}

codex() {
  if command -v huawei-bloom >/dev/null 2>&1; then
    huawei-bloom codex "$@"
  else
    command codex "$@"
  fi
}
```

Do not run the wrapper from a temporary checkout: updates to that checkout
would change an installed command.

To uninstall, remove the shell functions, the `~/.local/bin/huawei-bloom`
symlink, and the installed copy if you made one. Remove any
`AGENT_THEME_DEBUG` log as well. Nothing else is written.

## Usage

```sh
huawei-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--logo` / `--no-logo` | on | Header flower instead of the native mark. |
| `--header` / `--no-header` | on | Branded header name. |
| `--title` / `--no-title` | off | Branded window title. |
| `--home` / `--no-home` | on | Background Bloom, ambient sweep and home. `--no-home` disables the whole overlay and restores Codex's native welcome. |
| `--raw` | off | `exec` the app untouched. |
| `--check` | | Verify patterns, engine, binary and version. |
| `-h`, `--help` | | Help. |
| `-V`, `--version` | | Version. |

Element flags, `--raw` and `--check` may appear before or after the app name.
`--help`/`--version` are wrapper flags only before the app; after the app they
are passed to the app. Use `--` to pass any flag with the same spelling to the
app.

Non-interactive and direct commands (`--print`, `doctor`, `exec`, `--version`,
`--no-alt-screen`, and the other subcommands listed in `agent_theme/apps.py`)
are passed through without the PTY. `TERM=dumb` and a non-TTY stdin or stdout
do the same.

`--no-home` keeps the byte-level header/logo branding but disables the overlay
and home art; Codex's native welcome returns. When home is on, Codex is started
with `tui.effects.welcome=false` and `tui.show_tooltips=false`.

## Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `AGENT_THEME_GLYPHS` | auto | `octant` or `quadrant`. Auto-detects Ghostty, including inside tmux. |
| `AGENT_THEME_PALETTE` | auto | `light` or `dark`. Auto-detects from `COLORFGBG`, then macOS appearance. |
| `AGENT_THEME_CELL_RATIO` | auto, `2.12` fallback | Terminal cell height/width ratio. Detected from TIOCGWINSZ when the terminal reports pixels. |
| `AGENT_THEME_LANG` | auto (`zh-Hant` fallback) | `zh-Hant` or `zh-Hans`; auto-detects from `LC_ALL`, `LC_MESSAGES`, then `LANG`. |
| `AGENT_THEME_DEBUG` | unset | Append overlay timing diagnostics to this file. Opt-in; no log is written otherwise. |

In tmux with `automatic-rename` on, the window is named `claude` or `codex`
instead of a Python process name; a manually named window is left alone. The
original setting is restored on a clean exit if the window still has the name
the wrapper gave it. The underlying `#{pane_current_command}` remains a Python
process because the proxy really is Python; use `#{window_name}` (or `#W`) in
status formats instead.

`COLORFGBG` is advisory; macOS appearance is the fallback. An OSC 11 background
reply from the terminal also updates the palette while the app is running.

## Verification

```sh
./huawei-bloom --check claude
./huawei-bloom --check codex
python3 -m unittest discover -s tests -v
```

`--check` applies the embedded fixtures, constructs the overlay and Bloom
engine, and confirms the wrapped binary's `--version`. It does not inspect a
live TUI or read credentials; a changed renderer can still render unbranded and
fail open. Run the tests from the canonical checkout, not from a runtime copy
that does not include `tests/`.

## Architecture

```
huawei-bloom                 thin executable entry point
agent_theme/
  cli.py                    argument parsing, help, --check, process entry
  apps.py                   Claude/Codex profiles, patterns and arg policy
  replacer.py               streaming byte replacement with split carry
  launcher.py               PTY loop, signals, terminal restore, scheduling
  supervisor.py             foreground process group + stop/hangup mirroring
  terminal.py               winsize, writes, glyph/palette detection
  animation.py              Bloom/ambient compositor
  overlay.py                screen model and home painting
  intro.py                  vendored Bloom scene
  art.py                    vector mark, wordmark, lockup and palettes
  assets/art.json           vector data
```

The app profiles hold CLI patterns and policies; the launcher has two explicit
app-specific branches (overlay class selection and Codex welcome flags). The
overlay fails open: if the optional engine cannot import or draw, the app still
runs with byte-level branding.

## Provenance and license

The Bloom engine, overlay model and Huawei artwork are adapted from
[pangu-cli-theme](https://github.com/Lightly20110815/pangu-cli-theme), whose
code is MIT, upstream commit
`cefaa53080dd625be9bcc8060051fbbf2dc89723`.

See `LICENSE` and `NOTICE`. The MIT license covers the code and layout only;
HUAWEI, the Huawei flower logo and the HUAWEI wordmark are trademarks of Huawei
Technologies Co., Ltd. and are not licensed. This project is not affiliated
with Huawei, Anthropic or OpenAI.

## Limitations

- Byte-level branding matches the current Claude Code (2.1.x) and Codex
  (0.163.x) renderers. `--check` catches local fixture regressions and binary
  availability; it cannot detect a live renderer change. Such a change fails
  open rather than corrupting output.
- The home art needs blank rows. When a text-only lockup fits it is used;
  extremely narrow, short, or help-heavy panes draw no home.
- The wrapper is POSIX-only; Windows is not supported.
