# Agent Bloom website

## Theme
An editorial theme catalogue: a warm paper or forest-charcoal page surrounding a recognizable Claude terminal composition. Production artwork and header badges are the visual signature.

## Palette
Light: paper #f4f2ec, ink #252722, secondary #62665b, rule #d5d7cb, accent #365b40. Dark: paper #181c19, ink #eeeee6, secondary #a7afa6, rule #3a413a, accent #bad2a9. CSS light-dark() follows the system or the saved visitor override. Terminal colours come from production theme palettes.

## Typography
Georgia for English display titles, system CJK for Chinese, system sans for navigation and prose, system monospace for commands. No remote fonts.

## Components
One large terminal preview, a wrapping theme gallery and one primary use action. The navigation provides themes, docs, GitHub, language and a single appearance toggle. No application selector. Themes with multiple entrances show their names as compact inline buttons; one motion control pauses or resumes the preview. Controls use a 4px radius; preview surfaces use 8px. No shadow cards.

## Layout
A compact masthead, one short introduction, one wide preview, a responsive theme gallery and the selected theme with a use action. Installation expands below in the same page. Documentation stays secondary.

## Depth
Whitespace and thin rules separate sections. In light mode the terminal is a pale inset surface; in dark mode it is the deepest surface. A fine frame and restrained shadow distinguish the window.

## Do and do not
Use production exports. Keep unsupported prototypes out of the published catalogue. Do not add marketing statistics, decorative animations or remote tracking.

## Responsive
Each gallery card places artwork on the left and its exact CLI theme name and one metadata line on the right. That line contains the entrance count and idle-motion support; individual entrance names belong only in the preview controls. Mobile uses one card per row; desktop uses multiple columns. Controls wrap without truncation. Code blocks scroll within their own containers. Keyboard focus remains visible.

## Prompt guide
Preserve the editorial page and terminal distinction in both appearances. Put themes before implementation details. Play the selected entrance once on arrival and on pointer selection. Follow with production idle sweeps, using the static poster between sweeps. Never loop the entrance. Reduced-motion and keyboard browsing stay still. Stop when hidden or offscreen.
