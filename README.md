# huawei-bloom

[English](README.en.md) | **简体中文**

给 **Claude Code** 和 **Codex CLI** 加一层华为风格的终端主题：花瓣开场、HUAWEI 首页、品牌 header。  
不修改应用的配置文件、凭证或插件。

<p align="center">
  <img src="docs/hero.png" alt="huawei-bloom 的 Claude Code 与 Codex 首页" width="900">
</p>

<p align="center"><sub>Claude Code / Codex · 简体中文 · 95×55 / 111×55</sub></p>

## 特性

- 官方八瓣花轮廓与 HUAWEI 矢量字标，使用 octant 字形渲染
- 启动时播放一次 Bloom，之后每 8 秒缓慢扫光；只绘制应用认为空白的区域
- Header 改为 `盘古·Claude` / `盘古 · Codex`，Claude 图标换成小花
- 中文根据 locale 自动切换简体 / 繁体
- `/clear` 恢复首页；非空提交停止 ambient 并清除背景 art
- 直接命令、非 TTY、`--raw` 完全绕过 wrapper
- Codex 首页开启时使用会话级 `-c tui.effects.welcome=false` / `-c tui.show_tooltips=false`，不写配置

## 演示

<p align="center">
  <img src="docs/intro.gif" alt="huawei-bloom 启动动画：Claude Code 与 Codex" width="900">
</p>

<p align="center"><sub>左：Claude Code · 右：Codex CLI · 简体中文</sub></p>

## 安装

需要 macOS 或 Linux、Python 3.9+、支持 Unicode / truecolor 的终端；Ghostty 推荐。  
终端字体需要覆盖所选中文字形。

链接到单一 checkout：

```sh
mkdir -p ~/.local/bin
ln -sf /path/to/huawei-bloom/huawei-bloom ~/.local/bin/huawei-bloom
```

加入 shell function：

```zsh
_huawei_bloom() {
  local app=$1; shift
  (( $+commands[huawei-bloom] )) && { command huawei-bloom "$app" "$@"; return; }
  command "$app" "$@"
}
claude() { _huawei_bloom claude "$@"; }
codex() { _huawei_bloom codex "$@"; }
```

`command claude` / `command codex` 可以随时绕过 wrapper。  
移除 function、`~/.local/bin/huawei-bloom` 和安装目录即可卸载。

## 使用

```sh
huawei-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]
```

| 选项 | 默认 | 用途 |
| --- | --- | --- |
| `--logo` / `--no-logo` | 开 | 只切换 header 图标：Claude 小花 / Codex `✿` |
| `--header` / `--no-header` | 开 | Header 名称：`盘古·Claude` / `盘古 · Codex` |
| `--title` / `--no-title` | 关 | 窗口标题；默认关闭以保留 tmux pane 搜索 |
| `--home` / `--no-home` | 开 | Bloom、ambient、首页；`--no-home` 关闭整个 overlay，Codex 恢复原生 welcome |
| `--raw` | 关 | 完全绕过 wrapper |
| `--check` |  | 检查内置 pattern、引擎、binary 和版本 |

element flags、`--raw`、`--check` 可以放在 app 名称前后；`--help` / `--version` 放在 app 名称后时会传给 app。  
`--` 后的参数全部传给 app。

## 行为

- 全新 session 播放入场动画；header 和输入区立即可用，不阻塞输入。
- `claude -c`、`--resume`、`codex resume` / `fork` 或命令行初始 prompt 不播放入场动画。
- 空 Enter 不打断动画；非空提交停止 ambient。
- `/clear` 后首页和 ambient 回来。
- 直接 / 非交互命令直接执行原程序，不建立 PTY。

## 语言

主题文案随终端 locale 切换：

- `zh_TW` / `zh_HK` / `zh_MO` → 繁体
- `zh_CN` / `zh_SG` → 简体
- 非中文 locale → 繁体

可强制指定：

```sh
AGENT_THEME_LANG=zh-Hans huawei-bloom claude
AGENT_THEME_LANG=zh-Hant huawei-bloom codex
```

README 里的截图使用简体中文。

## 环境变量

| 变量 | 默认 | 用途 |
| --- | --- | --- |
| `AGENT_THEME_GLYPHS` | 自动 | `octant` / `quadrant`，自动检测 Ghostty（包括 tmux） |
| `AGENT_THEME_PALETTE` | 自动 | `light` / `dark`，读取 `COLORFGBG`、macOS 外观 |
| `AGENT_THEME_CELL_RATIO` | 自动，回退 `2.12` | 终端字符格高宽比 |
| `AGENT_THEME_LANG` | 自动，回退繁体 | `zh-Hant` / `zh-Hans` |
| `AGENT_THEME_DEBUG` | 未设置 | 写入 overlay timing 日志；默认不写 |

在 tmux 中，`automatic-rename` 开启时窗口名会是 `claude` / `codex`；手动命名的窗口不会被覆盖。  
`#{pane_current_command}` 仍是 Python，状态栏请使用 `#{window_name}` / `#W`。

## 验证

```sh
python3 -m unittest discover -s tests -v
./huawei-bloom --check claude
./huawei-bloom --check codex
```

`--check` 检查内置 fixture、引擎、binary 和版本；不会启动真实 TUI，也不能检测未来的 renderer 改版。渲染变化会 fail-open。

## 项目结构

```text
huawei-bloom              executable entry point
agent_theme/              CLI、PTY、overlay、动画、i18n、art
docs/                     README 图片、动画和架构说明
tests/                    stdlib unittest
```

## 来源与许可

Bloom 引擎、overlay 模型和华为风格图稿改作自
[pangu-cli-theme](https://github.com/Lightly20110815/pangu-cli-theme)（MIT，commit
`cefaa53080dd625be9bcc8060051fbbf2dc89723`）。

代码和版面按 MIT 授权；HUAWEI、华为花瓣标志与 HUAWEI 字标是华为技术有限公司的商标，不在此授权范围内。本项目与 Huawei、Anthropic、OpenAI 无隶属关系。

## 限制

- 仅支持 POSIX；Windows 不支持。
- 首页需要空白行；窄、矮或被帮助列表占满的 pane 可能没有首页。
- `/clear` 后可能因 echo 行重新缩放。
- `--check` 不替代真实 TUI 的集成测试。
