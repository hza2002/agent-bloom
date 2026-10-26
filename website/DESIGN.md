# Agent Bloom website

## Theme
A terminal theme fitting room. Real production artwork is the focal point; the page puts the preview, theme choices and use action together. The surrounding interface is quiet, precise and neutral so each theme supplies its own colour.

## Palette
Light: paper #f4f2ec, ink #252722, secondary #62665b, rule #d5d7cb, accent #365b40, surface #e9e7df. Dark: graphite #171819, ink #eeeee6, secondary #a8aaa7, rule #37393a, accent #bad2a9, surface #242627. CSS light-dark() follows the system or saved visitor override. Terminal palettes always come from production data.

## Typography
System sans for headlines and prose, system monospace for the wordmark, theme names and commands. No remote fonts. Headlines use 30–46px, weight 600; Chinese keeps normal tracking and English uses -.045em. Small catalogue labels leave room for exact CLI names, including playstation. Body copy has generous line height; secondary labels remain subordinate to the artwork.

## Components
One large terminal preview, a compact thumbnail catalogue and one primary use action. Navigation provides themes, docs, GitHub, language and appearance. Theme buttons use 4px corners with a thin accent border and raised surface when selected; keyboard focus adds an outer outline. The terminal uses an 8px frame with no decorative shadow. Playback controls have at least 40px hit areas. Search has a 36px minimum height. Replay and Play idle motion are explicit controls; only themes with multiple entrances show entrance choices. The use action opens the installation guide with the current theme, entrance and application.

## Layout
Keep the twelve-theme showroom within a typical laptop viewport, verified at 1280×720 and 1440×900. Use a compact masthead and title without an eyebrow. A selected-theme row sits above the terminal; the terminal window bar contains Claude Code / Codex buttons. Entrance choices and replay / idle controls sit directly below. The catalogue occupies 320px on desktop, 280px at narrower widths. The art height derives from viewport height with a 160px minimum and 380px maximum; never hide overflow to force a fit. Installation opens in the guide with the current selection.

## Depth
Thin rules and surface colour distinguish controls. The theme artwork is the only visual spectacle. No gradients, glass surfaces or decorative page animation. Light mode keeps a warm paper surround; dark mode uses neutral graphite rather than tinting every theme green.

## Do and do not
Use the production exports and existing player. Keep unsupported prototypes out of the catalogue. Never introduce a second theme manifest or browser-side recreation of the artwork. Keep URL, selected theme, installation command and agent prompt in sync. Preserve static posters on failures and for reduced motion. Do not add marketing statistics, autoplay carousels, remote tracking or new dependencies for layout.

## Responsive
At 1050px the catalogue narrows to 280px. At 760px the showroom stacks with compact preview, controls, then catalogue. Four thumbnail columns fit mobile screens, three below 359px. Smaller windows and installation use normal document scrolling rather than clipped controls or nested scroll regions. Both locales must fit horizontally at 320, 375, 760, 761 and 1280px. System icons use one 24px viewBox, 1.6px stroke vocabulary; retain text labels on primary actions.

## Prompt guide
Preserve one real terminal and adjacent choices. Use graphite #171819 / paper #f4f2ec for the surrounding canvas, 4px control corners and 8px terminal corners. Keep the selected theme name at 20px in monospace, the use action at least 40px high, and the gallery title at 16px. Play the selected entrance once on arrival and pointer selection, followed by production idle sweeps. Keyboard theme browsing skips the entrance and keeps automatic idle playback; explicit playback controls work with either input method. Reduced-motion preferences suppress automatic playback; an explicit play request runs once and then returns to the static preview. Pause when hidden or offscreen. Bring offscreen art into view before explicit playback and report loading / playback state beside the selected name. The Canvas player owns frame drawing and cancellation; page code owns selection, resource loading and installation state.
