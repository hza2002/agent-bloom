---
title: 安装与卸载
order: 1
---

# 安装与卸载

这份指南供用户和安装 agent 共同使用。先验证显式启动，再按用户需要接入 shell。无需安装网站使用的 Node 或 npm。

## 检查环境

- 支持 macOS 和 Linux，不支持 Windows 原生环境。
- 需要 Python 3.9+，以及已安装、可独立运行的 Claude Code 或 Codex CLI。
- 终端需要 Unicode 和 truecolor；Ghostty 支持更细的 octant 图形。中文文案需要对应中文字形，Codex header 图标需要 Nerd Font；缺字时可使用 `--no-logo`。

先执行只读检查，仅检查要使用的应用：

```sh
uname -s
python3 --version
command -v uv
command -v pipx
command -v agent-bloom
command -v claude
command -v codex
```

`command -v` 对未安装的可选工具返回非零是正常的。如果已有 Agent Bloom，先确认安装方式，不要叠加另一套安装。Claude / Codex 的安装与登录由各自工具负责；不要读取或复制凭证。

## 安装程序

以下命令用于尚无 checkout 的环境。若目录已存在，先检查内容，不覆盖、不删除。推荐使用已有的 `uv`：

<!-- quickstart:start -->
```sh
git clone https://github.com/hza2002/agent-bloom
cd agent-bloom
uv tool install .
agent-bloom --list
```
<!-- quickstart:end -->

如果使用 `pipx`，在同一个 checkout 内以 `pipx install .` 替代 `uv tool install .`，只选一种。两者都没有时，先按用户的软件管理习惯安装其中一种，不使用系统级 `sudo pip`。

如果命令不在 PATH，使用 `uv tool update-shell` 或 `pipx ensurepath`，然后新开一个 shell。不要重复安装来修复 PATH。

## 验证与首次启动

```sh
agent-bloom --version
agent-bloom --list
agent-bloom --check claude
```

如果使用 Codex，将最后一条换为 `agent-bloom --check codex`。检查失败时先解决报告的问题，不继续改 shell。`--check` 检查内置 pattern、引擎、应用 binary 和版本，不启动真实 TUI，也不验证视觉效果或登录状态。

在真实交互终端中运行：

```sh
agent-bloom claude
# 或
agent-bloom codex
```

确认输入、退出、首页和 `/clear` 正常。初始提示词、恢复会话或非 TTY 不播放开场，不能用这些方式验收动画。无真实交互终端的 agent 应报告“自动检查通过，视觉待用户验收”，不要声称已完成视觉验证。

## Codex

使用 Codex 首页前，需要关闭原生 welcome。配置位置是 `${CODEX_HOME:-$HOME/.codex}/config.toml`。读取已有配置，只在现有表中合并对应键；没有该表时才新增，不能重复追加 TOML 表：

```toml
[tui.effects]
welcome = false
```

如用户还希望隐藏输入区动态提示，可在现有 `[tui]` 表中合并 `show_tooltips = false`。这是可选项。

这些设置也影响不经过 wrapper 的 Codex。修改前记录原值和本次改动；不要覆盖整个文件。`--no-home` 不会恢复被关闭的 welcome。

## 可选：接入 shell

只有用户希望平时输入 `claude` / `codex` 就启用主题时才执行。先确认当前 shell 和目标启动文件，并检查是否已有同名 alias 或 function。若有自定义行为，先保留并协调，不能直接覆盖。

以下函数同时适用于 bash 和 zsh。zsh 放入 `~/.zshrc`；bash 放入实际被交互 shell 加载的文件，通常是 `~/.bashrc`，macOS 登录 shell 需要检查 `~/.bash_profile` 是否加载它。fish 不适用这段语法，可继续使用显式命令。

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

只写入一次；已有该标记块时更新该块。新开 shell 后验证。`command claude` / `command codex` 始终可以绕过函数。

## 更新

回到安装时的 checkout，先确认没有未提交修改，再执行 `git pull --ff-only`。随后使用原来的工具执行 `uv tool install --reinstall .` 或 `pipx install --force .`，重新运行验证命令。不要自动丢弃工作区改动。

## 卸载

使用原安装工具执行 `uv tool uninstall agent-bloom` 或 `pipx uninstall agent-bloom`。如果添加过 shell 标记块，仅删除该块，新开 shell；当前 shell 可执行 `unset -f claude codex _agent_bloom`，前提是这些仍是本项目添加的函数。

若修改过 Codex 配置，只恢复本次安装改动且此后未被用户修改的键。保留其他配置和凭证。删除 checkout 不是卸载所必需的。

安装 agent 最后报告：安装方式与版本、改动的文件、自动检查结果、尚待用户验证的项目，以及卸载方式。
