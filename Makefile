.PHONY: test check

test:
	python3 -m unittest discover -s tests -v

check:
	./huawei-bloom --check claude
	./huawei-bloom --check codex
