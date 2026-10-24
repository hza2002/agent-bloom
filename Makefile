.PHONY: test check themes-check

test:
	python3 -m unittest discover -s tests -v

themes-check:
	python3 tools/build_theme_art.py --check

check:
	./agent-bloom --check claude
	./agent-bloom --check codex
