# Agent Bloom

[English](README.en.md) | **简体中文**

给 **Claude Code** 和 **Codex CLI** 添加主题图稿、开场动画与待机扫光。
通过 PTY 包装原应用，零运行时依赖。

[主题网站](https://hza2002.github.io/agent-bloom/zh/) · [安装指南](docs/user/zh/get-started.md) · [使用与排查](docs/user/zh/usage.md)

<p align="center"><img src="docs/hero.png" alt="Agent Bloom 在 Claude Code 和 Codex 中的实际终端效果" width="900"></p>

## 开始使用

先阅读[安装指南](docs/user/zh/get-started.md)确认环境和已有安装，再使用已有的 uv：

<!-- quickstart:start -->
```sh
git clone https://github.com/hza2002/agent-bloom
cd agent-bloom
uv tool install .
agent-bloom --list
```
<!-- quickstart:end -->

在真实交互终端运行 `agent-bloom claude` 或 `agent-bloom codex`。主题与动画通过 `agent-bloom --list` 查看；Codex 首页配置和可选 shell 接入见安装指南。

**让 agent 安装：** 把[同一份安装指南](docs/user/zh/get-started.md)交给 agent，要求先检查环境、保留已有配置，并分别报告自动检查和待人工验证的结果。

## 内置主题

Huawei、Apple、PlayStation、Xbox、Nintendo、Mario、Google、Android、Microsoft、NVIDIA、Intel、AMD，共 12 套。Windows 飘旗已合并到 Microsoft。

```sh
agent-bloom --theme nvidia claude
agent-bloom --theme mario codex
agent-bloom --theme apple --animation random claude
```

各主题共用标题、三行文字和终端安全机制，大图开场与待机各有设计。

## 开发与贡献

- [架构](docs/architecture.md)、[主题维护](docs/themes.md)、[渲染基准](docs/benchmark.md)
- [网站维护](website/README.md)、[版本记录](CHANGELOG.md)
- 运行测试：`python3 -m unittest discover -s tests -v`

用户文档只在 `docs/user/` 维护，网站直接渲染；主题目录与动画由生产代码生成。

## 来源与许可

Bloom 引擎、overlay 模型和华为风格图稿改作自 [pangu-cli-theme](https://github.com/Lightly20110815/pangu-cli-theme)（MIT）。代码与版面按 [MIT](LICENSE) 授权，素材来源及商标说明见 [NOTICE](NOTICE)。本项目与展示的品牌及应用厂商无隶属关系。
