# Agent Bloom website

## Theme
A terminal theme fitting room. Real production artwork is the focal point; the page puts the preview, theme choices and use action together. The surrounding interface is quiet, precise and neutral so each theme supplies its own colour.

## Palette
Light: paper #f4f2ec, ink #252722, secondary #62665b, rule #d5d7cb, accent #365b40, surface #e9e7df. Dark: graphite #171819, ink #eeeee6, secondary #a8aaa7, rule #37393a, accent #bad2a9, surface #242627. CSS light-dark() follows the system or saved visitor override. Terminal palettes always come from production data.

## Typography
System sans for headlines and prose, system monospace for the wordmark, theme names and commands. No remote fonts. Headlines use 30–46px, weight 600; Chinese keeps normal tracking and English uses -.045em. Small catalogue labels leave room for exact CLI names, including playstation. Body copy has generous line height; secondary labels remain subordinate to the artwork.

## Components
One large terminal preview, a compact thumbnail catalogue and one primary use action. Navigation provides themes, docs, GitHub, language and appearance. Theme buttons use 4px corners with a thin accent border and raised surface when selected; keyboard focus adds an outer outline. The terminal uses an 8px frame with no decorative shadow. Search and playback controls have at least 40px hit areas. Pause and replay are explicit controls; only themes with multiple entrances show entrance choices. Installation expands inline.

## Layout
At desktop widths, a left-aligned introduction leads into a wide preview and a 350px catalogue. The preview sticks below navigation while browsing longer catalogues. The twelve current themes form three columns. Installation spans the page below the showroom. The page is at most 1240px wide; spacing uses 8/12/16/24/32px increments.

## Depth
Thin rules and surface colour distinguish controls. The theme artwork is the only visual spectacle. No gradients, glass surfaces or decorative page animation. Light mode keeps a warm paper surround; dark mode uses neutral graphite rather than tinting every theme green.

## Do and do not
Use the production exports and existing player. Keep unsupported prototypes out of the catalogue. Never introduce a second theme manifest or browser-side recreation of the artwork. Keep URL, selected theme, installation command and agent prompt in sync. Preserve static posters on failures and for reduced motion. Do not add marketing statistics, autoplay carousels, remote tracking or new dependencies for layout.

## Responsive
At 1050px the introduction stacks and the catalogue narrows to 310px. At 760px the showroom stacks: compact preview, controls, then catalogue; sticky positioning turns off. Three thumbnail columns fit 375px screens, two below 359px. Controls wrap, names remain complete and command blocks scroll within their containers. Both locales must fit at 320, 375, 760, 761 and 1280px.

## Prompt guide
Preserve one real terminal and adjacent choices. Use graphite #171819 / paper #f4f2ec for the surrounding canvas, 4px control corners and 8px terminal corners. Keep the selected theme name at 25px in monospace, the use action at least 46px high, and the gallery title at 20px. Play the selected entrance once on arrival and pointer selection, followed by production idle sweeps. Keyboard theme browsing stays still; explicit playback controls work with either input method. Reduced-motion preferences suppress playback. Pause when hidden or offscreen. The Canvas player owns frame drawing and cancellation; page code owns selection, resource loading and installation state.
