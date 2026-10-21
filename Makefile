.PHONY: test check install check-install uninstall

PREFIX ?= $(HOME)/.local/lib/huawei-bloom
BINDIR ?= $(HOME)/.local/bin

test:
	python3 -m unittest discover -s tests -v

check:
	./huawei-bloom --check claude
	./huawei-bloom --check codex

install:
	mkdir -p "$(PREFIX)" "$(BINDIR)"
	rsync -a --exclude=__pycache__ agent_theme "$(PREFIX)"/
	cp huawei-bloom README.md README.en.md LICENSE NOTICE "$(PREFIX)"/
	chmod +x "$(PREFIX)/huawei-bloom"
	ln -sf "$(PREFIX)/huawei-bloom" "$(BINDIR)/huawei-bloom"

check-install:
	@out="$$(rsync -anc --delete --exclude=__pycache__ agent_theme/ "$(PREFIX)/agent_theme/")"; \
	test -z "$$out" || { printf '%s\n' "$$out"; exit 1; }

uninstall:
	rm -f "$(BINDIR)/huawei-bloom"
	rm -rf "$(PREFIX)"
