# Changelog

## 0.4.1 - 2026-10-21

- Add standard Python packaging with a `huawei-bloom` console script for
  `uv tool install` and `pipx install`; keep the checkout symlink for development.
- Move the trademark notice out of `LICENSE` so the code is detected as MIT;
  the notice remains in `NOTICE`.
- Sanitize the demo screenshots and hide session-specific header details.
- Document tested app versions and the fail-open behavior.

## 0.4.0 - 2026-10-21

- Use one Bloom timeline for Claude and Codex; remove the Claude-only prelude.
- Keep platform-line spacing attached to the tagline and preserve centering.
- Move app-specific engine policy into `Profile`; add `docs/architecture.md`.
- Add PTY integration tests for headers, home paint, input, resize, signals,
  exit status and fail-open.
- Bump the package to 0.4.0 and simplify installation to the checkout symlink.

## 0.3.0

- Initial theme release with the Huawei mark, wordmark, Bloom,
  ambient sweep, branded headers and locale-aware Chinese copy.
