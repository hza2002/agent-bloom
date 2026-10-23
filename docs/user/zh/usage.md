---
title: 使用与排查
order: 2
---

# 使用与排查

## 命令与主题

```sh
agent-bloom [OPTIONS] <claude|codex> [--] [APP ARGS...]
```

使用 `agent-bloom --help` 查看当前 CLI 参数，使用 `agent-bloom --list` 查看当前内置主题、动画与默认值。网站的命令参考由这两类代码数据生成。

`--theme` 选择主题，`--animation` 接受一个动画名称、逗号分隔的候选列表或 `random`。候选列表去重后等概率选择一套；`random` 代表当前主题的全部动画，必须单独使用。无效名称或空候选项会报错，不静默回退。

选择在每次启动时固定，缩放、重绘与 `/clear` 不重新选择。恢复会话或传入初始提示词仍跳过开场，静态首页使用选定方案。

`--theme`、`--animation`、element flags、`--raw` 和 `--check` 可以放在 app 名称前后。`--help` / `--version` 放在 app 名称后时传给 app，`--` 后的参数全部透传。`--list` 支持可选的主题和 app 名称，不接受应用运行参数。

只看一次开场，之后保留静态首页：`agent-bloom --no-ambient claude`（或 `codex`）。`/clear` 恢复首页时仍保持静态；`--no-home` 关闭整个首页。

主题由项目内部维护，不加载外部主题或插件。添加主题和动画见 [主题维护说明](../../themes.md)。

[Codex 首页配置见安装指南](get-started.md#codex)。

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

网站的标准预览使用简体中文。

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


## 限制

- 仅支持 POSIX；Windows 不支持。
- 首页需要空白行；窄、矮或被帮助列表占满的 pane 可能没有首页。
- 应用输出文字后，背景绘制等待明确的光标定位；仅输出文字的 renderer 可能不显示背景。
- 遇到当前观察器不能可靠处理的 emoji／组合序列，会隔离背景装饰，继续原样透传；header／title 替换继续工作。如果无法在安全边界清除旧装饰，会保留残影直到应用重绘，避免误擦内容。应用随后完成一次全屏 clear 或通过 1049 模式从主屏重新进入 alternate screen，并给出绝对 cursor 定位后，背景装饰会自动恢复；只有 clear、相对移动或存在不安全终端模式时不会恢复。
- `/clear` 只作为恢复首页的候选，还需后续应用输出与首页布局；粘贴里的命令不会触发恢复。
- resize 后等待应用完整清屏再恢复装饰；不支持的终端模式会暂停装饰。
- `--check` 不替代真实 TUI 的集成测试。
