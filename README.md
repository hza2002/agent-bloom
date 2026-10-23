# Agent Bloom

[English](README.en.md) | **简体中文**

给 **Claude Code** 和 **Codex CLI** 添加可选择的终端主题：品牌图标、开场动画、静态首页与待机扫光。
通过 PTY 包装原应用，不修改应用的配置文件、凭证或插件。零运行时依赖。

| 主题 | 开场动画 | 视觉风格 |
| --- | --- | --- |
| **Huawei**（默认） | `bloom` · 花瓣绽放 | 八瓣花、HUAWEI 字标与红色扫光 |
| **Apple** | `spectrum` · 色带重组 / `constellation` · 光点聚合 | 六色像素苹果、APPLE 字标与解码扫光 |

每次启动可固定一套动画，也可从指定候选中随机选择。主题由项目内部维护。

<p align="center">
  <img src="docs/hero.png" alt="agent-bloom 的 Claude Code 与 Codex 首页" width="900">
</p>

<p align="center"><sub>Claude Code / Codex · 简体中文 · 95×55 / 111×55 字符格 · 演示（已隐藏会话信息）</sub></p>

## 特性

- 内置 Huawei / Apple 主题，图稿使用 octant 字形渲染，不支持时回退 quadrant
- 启动时播放所选开场，之后每 8 秒播放待机扫光；只绘制应用认为空白的区域
- 首页、header 图标与名称随所选主题一起切换
- 中文根据 locale 自动切换简体 / 繁体
- `/clear` 恢复首页；非空提交停止 ambient 并清除背景 art
- 直接命令、非 TTY、`--raw` 完全绕过 wrapper
- Codex 首页由用户在配置中关闭 welcome；wrapper 不注入启动参数

## 演示

<p align="center">
  <img src="docs/intro.gif" alt="agent-bloom 启动与闲置扫光：Claude Code 与 Codex" width="900">
</p>

<p align="center"><sub>Huawei 主题 · 左：Claude Code · 右：Codex CLI · 简体中文 · 8 秒闲置间隔在演示中已压缩</sub></p>

## 安装

需要 macOS 或 Linux、Python 3.9+、支持 Unicode / truecolor 的终端；Ghostty 推荐。  
终端字体需要覆盖所选中文字形；Codex header 花标还需要 Nerd Font 字形。

克隆后用 `uv` 或 `pipx` 安装：

```sh
git clone https://github.com/hza2002/agent-bloom
cd agent-bloom
uv tool install .
# 或
pipx install .
```

如果命令不在 PATH，运行 `uv tool update-shell`（pipx 使用 `pipx ensurepath`）。

开发时也可以直接链接 checkout：

```sh
mkdir -p ~/.local/bin
ln -sf /path/to/agent-bloom/agent-bloom ~/.local/bin/agent-bloom
```

加入 shell function：

```zsh
_agent_bloom() {
  local app=$1; shift
  (( $+commands[agent-bloom] )) && { command agent-bloom "$app" "$@"; return; }
  command "$app" "$@"
}
claude() { _agent_bloom claude "$@"; }
codex() { _agent_bloom codex "$@"; }
```

`command claude` / `command codex` 可以随时绕过 wrapper。  
卸载：`uv tool uninstall agent-bloom`（或 `pipx uninstall agent-bloom`）；如果使用 symlink，移除 function 和 `~/.local/bin/agent-bloom` 即可。

## 使用

```sh
agent-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]
```

| 选项 | 默认 | 用途 |
| --- | --- | --- |
| `--theme NAME` | `huawei` | 内置主题：`huawei` / `apple` |
| `--animation SELECTION` | 由主题决定 | 固定名称、逗号分隔的随机候选列表，或 `random` |
| `--list` | | 列出主题与动画，无需启动应用 |
| `--logo` / `--no-logo` | 开 | 只切换所选主题的 header 图标 |
| `--header` / `--no-header` | 开 | 所选主题的 Header 名称 |
| `--title` / `--no-title` | 关 | 窗口标题；默认关闭以保留 tmux pane 搜索 |
| `--home` / `--no-home` | 开 | 开场、ambient、首页；`--no-home` 关闭整个 overlay，应用配置保持不变 |
| `--ambient` / `--no-ambient` | 开 | 闲置扫光；`--no-ambient` 保留开场和静态首页，停止周期动画与 tmux 可见性查询 |
| `--raw` | 关 | 完全绕过 wrapper |
| `--check` |  | 检查内置 pattern、引擎、binary 和版本 |

华为主题的 Codex header 花标使用 Nerd Font 字形 `md-flower_poppy`（U+F0D08），需要 Nerd Font 补丁字体；缺字时用 `--no-logo` 保留原来的 `>_`。
element flags、`--raw`、`--check` 可以放在 app 名称前后；`--help` / `--version` 放在 app 名称后时会传给 app。  
`--` 后的参数全部传给 app。

只看一次开场，之后保留静态首页：`agent-bloom --no-ambient claude`（或 `codex`）。`/clear` 恢复首页时仍保持静态；`--no-home` 优先关闭整个首页。

选择 Apple 主题（每次启动随机选一套）：

```sh
agent-bloom --theme apple codex
agent-bloom --theme apple --animation spectrum claude
agent-bloom --theme apple --animation spectrum,constellation codex
agent-bloom --theme apple --animation random codex
agent-bloom --list
agent-bloom --theme apple --list
```

- `spectrum`：六色色带重组；`constellation`：六色光点聚合。两种入场共享同一六色苹果和最终画面。
- Apple 底部统一三行：`Choose your superpower`、`Think different`、`Apple silicon · macOS`，不带句号，不随应用或动画变化。
- 华为默认动画为 `bloom`，Apple 默认为 `random`。逗号列表去重后等概率选一套，不连续播放；`random` 表示当前主题的全部动画，必须单独使用。
- 选择在每次启动时固定，缩放、重绘与 `/clear` 不重新选择。恢复会话或传入初始提示词仍跳过开场，但静态首页使用选定方案。
- `--theme` 和 `--animation` 可放在 app 名称前后，支持 `--flag=value`；`--` 后全部透传。无效名称或空候选项会报错，不静默回退。
- `--list` 支持可选的 `--theme` 和 app 名称，不接受运行参数。`--check` 检查候选范围内的每套动画，并检查应用 binary。
- Apple 的 Claude header 使用定稿的三行六色像素苹果（半高色带，边缘保持透明）；Codex header 使用 Nerd Font 的 `fa-apple`（U+F179）。Codex 缺字时可用 `--no-logo` 保留原徽标。

主题由项目内部维护，不加载外部主题或插件。添加主题和动画见 [主题维护说明](docs/themes.md)。

### Codex 首页配置

Codex 原生的 welcome 动画会占据 Bloom 需要绘制的空白区域。请在 `~/.codex/config.toml` 中关闭它：

```toml
[tui.effects]
welcome = false
```

想同时隐藏输入框下方的动态提示（例如 `← for agents`），可在已有的 `[tui]` 表中设置：

```toml
[tui]
show_tooltips = false
```

这两项作用于对应的 `CODEX_HOME`，包括不经过 wrapper 的 Codex 窗口。wrapper 不注入配置覆盖，避免影响 Codex 原有的 daemon 启动行为；用户显式传入的参数保持不变。`--no-home` 不会重新启用配置中已关闭的 welcome。

## 行为

- 全新 session 播放入场动画；header 和输入区立即可用，不阻塞输入。
- `claude -c`、`--resume`、`codex resume` / `fork` 或命令行初始 prompt 不播放入场动画。
- 空 Enter 不打断动画；非空提交停止 ambient。
- `/clear` 在屏幕仍符合绘制条件时恢复首页和 ambient。
- 直接 / 非交互命令直接执行原程序，不建立 PTY。

## 兼容性

已在 Claude Code v2.1.305 和 Codex v0.163.0 上验证。应用更新可能改变 header 或 renderer；替换失败时 wrapper 自动放行，不会阻塞应用。

## 语言

主题文案随终端 locale 切换：

- `zh_TW` / `zh_HK` / `zh_MO` → 繁体
- `zh_CN` / `zh_SG` → 简体
- 非中文 locale → 繁体

可强制指定：

```sh
AGENT_THEME_LANG=zh-Hans agent-bloom claude
AGENT_THEME_LANG=zh-Hant agent-bloom codex
```

README 里的截图使用简体中文。

## 环境变量

| 变量 | 默认 | 用途 |
| --- | --- | --- |
| `AGENT_THEME_GLYPHS` | 自动 | `octant` / `quadrant`，自动检测 Ghostty（包括 tmux） |
| `AGENT_THEME_PALETTE` | 自动 | `light` / `dark`，读取 `COLORFGBG`、macOS 外观 |
| `AGENT_THEME_CELL_RATIO` | 自动，回退 `2.12` | 终端字符格高宽比 |
| `AGENT_THEME_LANG` | 自动，回退繁体 | `zh-Hant` / `zh-Hans` |
| `AGENT_THEME_DEBUG` | 未设置 | 结构化诊断日志路径；默认不写，单文件最多 256 KiB 或 24 小时，超限后清空重写，不留副本 |

排查时可用 `AGENT_THEME_DEBUG=/tmp/agent-bloom.log agent-bloom claude`（或 `codex`）启动。日志是 `key=value` 事件，带时间、`pid`、`app`、终端尺寸和 tmux pane；核心事件包括 `session`、`band`、`frame`、`state`、`touch`、`input`、`unsupported`、`exception`，每 60 秒一次 `heartbeat`。日志只记录行号、标志、原因和耗时，不记录应用输出或输入内容。多 pane 可共用同一路径，记录按时间交错但不会丢失字节。关闭环境变量即停止记录。

在 tmux 中，`automatic-rename` 开启时窗口名会是 `claude` / `codex`；手动命名的窗口不会被覆盖。  
pane 不在当前 window、被另一个放大的 pane 遮住或客户端已 detach 时，ambient 暂停；同一可见 window 内未获得焦点的分屏仍播放。每 8 秒重新检查一次，切回后通常在一个周期加查询时间内恢复；查询异步执行，不等待它完成再转发输入。没有 tmux 时保持原有的持续动画，不做额外查询。
`#{pane_current_command}` 仍是 Python，状态栏请使用 `#{window_name}` / `#W`。

## 验证

```sh
python3 -m unittest discover -s tests -v
./agent-bloom --check claude
./agent-bloom --check codex
```

`--check` 检查内置 fixture、引擎、binary 和版本；不会启动真实 TUI，也不能检测未来的 renderer 改版。渲染变化会 fail-open。

固定输入的渲染性能对比见 [benchmark](docs/benchmark.md)：

```sh
python3 tools/benchmark.py v0.4.1 8bd48b7 worktree
```

## 项目结构

```text
agent-bloom               executable entry point
agent_theme/              CLI、PTY、overlay、动画、i18n、art
docs/                     README 图片、动画和架构说明
CHANGELOG.md              版本记录
tests/                    stdlib unittest
tools/                    可复现的渲染性能基准
```

## 来源与许可

Bloom 引擎、overlay 模型和华为风格图稿改作自
[pangu-cli-theme](https://github.com/Lightly20110815/pangu-cli-theme)（MIT，commit
`cefaa53080dd625be9bcc8060051fbbf2dc89723`）。

HUAWEI 字标不是字体排出来的：`agent_theme/themes/assets/huawei.json` 保存的是
`huawei-mark.svg` 的矢量轮廓，渲染时栅格化为每个字符格 2×4 个 octant 子像素
（不支持 octant 的终端回退为 2×2 quadrant）。

Apple 轮廓来自 Simple Icons，APPLE 文字使用 Inter 4.1 Medium 的轮廓；它不是 Apple 官方字标。资源来源与许可见 [NOTICE](NOTICE)。

代码和版面按 MIT 授权；HUAWEI、华为花瓣标志与 HUAWEI 字标是华为技术有限公司的商标，不在此授权范围内。Apple 与 Apple 标志是 Apple Inc. 的商标。本项目与 Huawei、Apple、Anthropic、OpenAI 无隶属关系。

## 限制

- 仅支持 POSIX；Windows 不支持。
- 首页需要空白行；窄、矮或被帮助列表占满的 pane 可能没有首页。
- 应用输出文字后，背景绘制等待明确的光标定位；仅输出文字的 renderer 可能不显示背景。
- 遇到当前观察器不能可靠处理的 emoji／组合序列，会隔离背景装饰，继续原样透传；header／title 替换继续工作。如果无法在安全边界清除旧装饰，会保留残影直到应用重绘，避免误擦内容。应用随后完成一次全屏 clear 或通过 1049 模式从主屏重新进入 alternate screen，并给出绝对 cursor 定位后，背景装饰会自动恢复；只有 clear、相对移动或存在不安全终端模式时不会恢复。
- `/clear` 只作为恢复首页的候选，还需后续应用输出与首页布局；粘贴里的命令不会触发恢复。
- resize 后等待应用完整清屏再恢复装饰；不支持的终端模式会暂停装饰。
- `--check` 不替代真实 TUI 的集成测试。
