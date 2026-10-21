# Changelog

## 0.4.1 - 2026-10-21

- Add standard Python packaging with a `huawei-bloom` console script for
  `uv tool install` and `pipx install`; keep the checkout symlink for development.
- Move the trademark notice out of `LICENSE` so the code is detected as MIT;
  the notice remains in `NOTICE`.
- Sanitize the demo screenshots and embedded app fixtures; no session-specific
  header details remain in the source or install package.
- Include docs and the fake TUI in the sdist so it is self-contained.
- Document clone-based installation, PATH setup and tested app versions.
- Use non-affiliated wording for the Huawei-style mark.
- Bound the replacer buffer so continuous coloured output cannot stall.
- Block signals during startup setup so a termination signal cannot leave the
  terminal raw.
- Fix filled clears wider than 256 columns and make the narrow-header check
  assert the replacement actually happened.
- Exercise input during the intro, wide overlays and large streams in tests.

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
