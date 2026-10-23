# Agent Bloom

[简体中文](README.md) | **English**

Theme artwork, animated entrances and idle sweeps for **Claude Code** and **Codex CLI**.
A PTY wrapper with no runtime dependencies.

[Theme website](https://hza2002.github.io/agent-bloom/en/) · [Installation guide](docs/user/en/get-started.md) · [Usage and troubleshooting](docs/user/en/usage.md)

<p align="center"><img src="docs/hero.png" alt="Agent Bloom running in Claude Code and Codex terminals" width="900"></p>

## Get started

Read the [installation guide](docs/user/en/get-started.md) to check your environment and existing installation, then use an existing uv installation:

<!-- quickstart:start -->
```sh
git clone https://github.com/hza2002/agent-bloom
cd agent-bloom
uv tool install .
agent-bloom --list
```
<!-- quickstart:end -->

Run `agent-bloom claude` or `agent-bloom codex` in a real interactive terminal. Use `agent-bloom --list` to discover themes and animations. The installation guide covers Codex home configuration and optional shell integration.

**Ask your agent to install it:** provide the [same installation guide](docs/user/en/get-started.md). Ask it to inspect the environment, preserve existing configuration, and report automated checks separately from pending visual checks.

## Development and contributions

- [Architecture](docs/architecture.md), [theme maintenance](docs/themes.md), [renderer benchmarks](docs/benchmark.md)
- [Website maintenance](website/README.md), [changelog](CHANGELOG.md)
- Run tests: `python3 -m unittest discover -s tests -v`

User documentation lives only in `docs/user/`; the website renders those files. Theme listings and previews are generated from production code.

## Provenance and license

The Bloom engine, overlay model and Huawei-style artwork are adapted from [pangu-cli-theme](https://github.com/Lightly20110815/pangu-cli-theme) (MIT). Code and layout use the [MIT license](LICENSE). See [NOTICE](NOTICE) for asset provenance and trademark information. This project is unaffiliated with the featured brands and application vendors.
