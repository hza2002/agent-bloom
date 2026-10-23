---
title: Install and uninstall
order: 1
---

# Install and uninstall

This guide serves both people and installation agents. Verify explicit launches before adding optional shell integration. Users do not need the website's Node or npm tooling.

## Check the environment

- macOS or Linux is required. Native Windows is unsupported.
- Python 3.9+ and a working installation of Claude Code or Codex CLI are required.
- Use a Unicode/truecolor terminal. Ghostty supports the finer octant graphics. Chinese copy needs matching font coverage; Codex header icons need a Nerd Font. Use `--no-logo` if the icon is missing.

Run read-only checks for the tools you intend to use:

```sh
uname -s
python3 --version
command -v uv
command -v pipx
command -v agent-bloom
command -v claude
command -v codex
```

A nonzero result from `command -v` is expected for absent optional tools. If Agent Bloom is already installed, identify its installation method before proceeding. Do not layer another installation over it. Claude / Codex installation and login belong to those tools; do not read or copy credentials.

## Install

For an environment without a checkout, use the commands below. If the directory already exists, inspect it first; do not overwrite or delete it. Prefer an existing `uv` installation:

<!-- quickstart:start -->
```sh
git clone https://github.com/hza2002/agent-bloom
cd agent-bloom
uv tool install .
agent-bloom --list
```
<!-- quickstart:end -->

With `pipx`, substitute `pipx install .` for `uv tool install .` in the same checkout. Choose one method. If neither tool is available, install one using the user's preferred package management method. Do not use system-wide `sudo pip`.

If the command is missing from PATH, run `uv tool update-shell` or `pipx ensurepath`, then open a new shell. Do not reinstall to fix PATH.

## Verify and launch

```sh
agent-bloom --version
agent-bloom --list
agent-bloom --check claude
```

For Codex, replace the final command with `agent-bloom --check codex`. Resolve failed checks before editing shell configuration. `--check` validates embedded patterns, the engine, the app binary and its version. It does not start a real TUI or verify appearance or login state.

In a real interactive terminal, run:

```sh
agent-bloom claude
# or
agent-bloom codex
```

Verify input, exit, the home and `/clear`. Initial prompts, resumed sessions and non-TTY runs skip the intro, so they cannot validate it. An agent without a real interactive terminal must report automated results separately from pending visual checks.

## Codex

Disable the native welcome before using the Codex home. The config file is `${CODEX_HOME:-$HOME/.codex}/config.toml`. Read the existing file and merge the key into its existing table. Create the table only if absent; never append duplicate TOML tables:

```toml
[tui.effects]
welcome = false
```

If the user also wants to hide dynamic input-area hints, optionally merge `show_tooltips = false` into the existing `[tui]` table.

These settings also affect Codex outside the wrapper. Record the previous values and your changes before editing; do not overwrite the entire file. `--no-home` does not restore a disabled welcome.

## Optional shell integration

Do this only when the user wants ordinary `claude` / `codex` commands to enable themes. Identify the current shell and its startup file, then check for existing aliases or functions with these names. Preserve and reconcile existing custom behavior instead of overwriting it.

These functions work in both bash and zsh. For zsh, use `~/.zshrc`. For bash, use the file actually loaded by the interactive shell, usually `~/.bashrc`; on macOS, check whether the login shell's `~/.bash_profile` loads it. This syntax does not work in fish; explicit launches remain available.

```sh
# BEGIN agent-bloom
_agent_bloom() {
  local app="$1"
  shift
  if command -v agent-bloom >/dev/null 2>&1; then
    command agent-bloom "$app" "$@"
  else
    command "$app" "$@"
  fi
}
claude() { _agent_bloom claude "$@"; }
codex() { _agent_bloom codex "$@"; }
# END agent-bloom
```

Add the block only once; update the marked block if it exists. Verify in a new shell. `command claude` / `command codex` always bypass these functions.

## Update

Return to the original checkout and check for uncommitted changes before running `git pull --ff-only`. Then use the original tool: `uv tool install --reinstall .` or `pipx install --force .`. Repeat verification. Never discard local changes automatically.

## Uninstall

Use the original tool: `uv tool uninstall agent-bloom` or `pipx uninstall agent-bloom`. If you added the shell block, remove only that block and open a new shell. In the current shell, `unset -f claude codex _agent_bloom` removes the functions, provided they are still the ones added by this project.

Restore only Codex keys changed by this installation that the user has not subsequently edited. Preserve other settings and credentials. Deleting the checkout is not required for uninstallation.

Installation agents should report the method and version, files changed, automated check results, pending user checks and the uninstall procedure.
