Codex header symbol subset
Source: Nerd Fonts Symbols v3.4.0
https://github.com/ryanoasis/nerd-fonts/blob/v3.4.0/patched-fonts/NerdFontsSymbolsOnly/SymbolsNerdFont-Regular.ttf
Only the header_icon characters registered in agent_theme.themes are included.
Generated with fontTools subset and Brotli, preserving the original outlines.
License and upstream component notices: codex-symbols-LICENSE.txt

Regenerate from the source font:
python3 -c "from agent_theme.themes import THEME_NAMES,get_theme; print(''.join(get_theme(n).header_icon for n in THEME_NAMES))" > /tmp/bloom-glyphs.txt
uvx --from fonttools --with brotli fonttools subset SymbolsNerdFont-Regular.ttf --text-file=/tmp/bloom-glyphs.txt --flavor=woff2 --output-file=website/src/assets/codex-symbols.woff2
