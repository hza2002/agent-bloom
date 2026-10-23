# Website maintenance

The website renders `docs/user/{zh,en}/*.md` directly. Edit those files for user documentation. Theme facts and preview frames come from the Python registry and renderer; never add a separate theme manifest or hand-edit `public/generated/`.

## Local development

Use Node compatible with `package.json` and Python 3.9+:

```sh
cd website
npm ci
npm run dev
```

Open `http://127.0.0.1:4321/agent-bloom/`. `dev` and `build` export themes before starting Astro. After changing Python code, rerun the command to refresh previews. Markdown and UI edits update through Astro normally.

```sh
npm run build
npm run preview
```

Build checks cover local HTML links, project-base paths, identical Markdown downloads and asset budgets. The only JavaScript sent for playback is the shared player; there is no browser Python runtime or React dependency.

## Content ownership

- `agent_theme/`: theme IDs, names, variants, copy, palettes, durations, geometry and frames.
- `docs/user/`: canonical bilingual user guides, read directly by Astro and copied byte-for-byte for agents.
- `README.md`, `README.en.md`: short repository entries. Their marked quick-start blocks are derived from each locale's installation guide. After editing a block, run `python3 tools/website_docs.py --sync-readme` from the repository root; ordinary builds fail on drift.
- `website/src/`: layouts, navigation labels and the universal player. There is no theme-specific animation implementation here.
- `public/generated/`, `public/raw/`, `public/llms.txt`: ignored build outputs. `llms.txt` is an index, not another installation guide.
- `prototypes/theme-lab/`: internal design experiments, not published as installable themes.

To add a user guide, add Markdown with `title` and numeric `order` frontmatter under both locale directories. Routes, documentation navigation, raw downloads and the agent index derive from those files. Keep relative Markdown links valid on GitHub; Astro maps user-guide links to site routes and developer-document links to GitHub.

The existing `docs/hero.png` is a real-terminal reference image, not the website's animation source. The website's posters are generated from the same production cells as playback. Do not add GIFs for new themes.

## Preview contract

The exporter calls every registered animation of each theme, with fixed geometry, an explicit Simplified Chinese locale and a deterministic seed. The representative application is shown in a Claude-style terminal composition. Both production palettes are exported; page appearance follows the system until the visitor chooses an override. It samples production intro timing and the shared text reveal. Opening choices use the registered animation names. Idle frames, text sheen and cadence also come from the production renderer. The final frame must match production static art exactly. The surrounding header and input area are a noninteractive Claude-style composition, not a running CLI. The header name and badge are exported from production data; the directory is an explicit demo path. PTY behavior and terminal font differences still require real-terminal testing.

Clips contain a dictionary of character/colour/bold values plus timed cell changes. Token `-1` clears a cell. Content hashes deduplicate clips and posters. The browser downloads only the selected entrance, plays it once, then loads its idle sweep on demand. Sweeps follow production timing and reuse one cached idle clip until the selection changes. A pause control stops motion. Playback stops when hidden or outside the viewport and resumes with the idle cadence when visible. Initial navigation loads one clip; reduced-motion preferences and keyboard theme selection keep previews static. Theme and entrance choices stay on the same page and update the URL, launch command and copied agent instruction. Horizontal image-and-text cards use a CSS Grid gallery that wraps as themes are added, with a name search above eight themes. Static previews use Astro Image inside native picture elements; animations are never loaded for every gallery entry. The use action expands installation inline. Old theme-detail URLs redirect into this experience.

`public/generated/metrics.json` records raw size, estimated gzip size and frame count. The estimate does not assume any particular hosting compression. Build limits are 2 MB raw per clip and 500 MB total. If a new animation exceeds the limit, measure it before changing budgets; do not silently reduce visual fidelity.

The exporter reads scene timing and the shared text-reveal duration without modifying production modules. Its tests guard the renderer interface. If production changes, update the exporter rather than copying animation logic into JavaScript.

## Verification

From the repository root:

```sh
python3 -m unittest discover -s website/tests -p 'test_*.py' -v
```

From `website/`, after building:

```sh
npx playwright install chromium
npm test
```

Browser tests cover both locales, narrow screens, on-demand intro and idle loading, both Apple entrances, pause/resume, same-page selection, installation context, failed requests, reduced motion, appearance persistence and a test-only forty-theme catalogue. Screenshots are ignored local test artifacts.

## Publishing

The `website` GitHub Actions workflow builds pull requests without deploying them. Main-branch pushes and manual main-branch runs deploy only after validation. Before the first deployment, select **GitHub Actions** in the repository's **Settings → Pages → Build and deployment**. The workflow uses the `github-pages` environment and the built-in token; no external account, API key or personal token is needed.

The project URL is `https://hza2002.github.io/agent-bloom/`. No custom domain is configured. `astro.config.mjs` owns the site origin and project base. Agent prompts use this public URL, so their links become usable after the first deployment. The locally copied Markdown is already available during preview.

Build failures leave the previous deployment intact. To roll back, revert the website change and redeploy the previous working source. No application data is stored by the website.
