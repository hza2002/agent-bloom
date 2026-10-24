# Theme lab

Internal drawing sources and comparison prototypes for the ten installed frame themes. Production workflow:
[主题制作流程](../../docs/theme-production.md).

```sh
python3 -m http.server 8768 --bind 127.0.0.1 --directory prototypes
```

- Gallery: <http://127.0.0.1:8768/theme-lab/>
- Xbox motion comparison: <http://127.0.0.1:8768/theme-lab/xbox.html>
- Badge comparison: <http://127.0.0.1:8768/theme-lab/badges.html>
- Technology studies: <http://127.0.0.1:8768/theme-lab/tech.html>
- Nintendo / Mario comparison: <http://127.0.0.1:8768/theme-lab/nintendo.html>
- Repeatable Canvas checks: <http://127.0.0.1:8768/theme-lab/checks.html>

Add modules explicitly to `catalogue.js`. A comparison page can select a subset
with `body[data-themes]`. Both the gallery and checker use `pixels.js` for solid
octant/quadrant colour conversion. No build step or third-party packages needed.

Checks cover sampled intro/idle motion, exact settled endpoints, nonempty art,
independent badge selection and distinct badges in both palettes and glyph modes.
Visual quality, real-terminal rendering, performance and source permissions still
require the production checklist. Do not treat green browser checks as release approval.

Current gallery: 10 prototypes, with at least one selected intro and an ambient motion.
Technology batch adds Google, NVIDIA, Intel, AMD and Microsoft (including the merged Windows direction); Android
now uses a full-body large character with a separate head badge. The selected production variants are installed; additional variants remain lab-only.
See docs/themes.md for the shared layout and asset contract.
