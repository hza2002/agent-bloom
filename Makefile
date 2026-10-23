.PHONY: test check

test:
	python3 -m unittest discover -s tests -v

check:
	./agent-bloom --check claude
	./agent-bloom --check codex
