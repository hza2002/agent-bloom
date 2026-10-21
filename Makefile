.PHONY: test check install check-install uninstall

PREFIX ?= $(HOME)/.local/lib/agent-theme
BINDIR ?= $(HOME)/.local/bin

test:
	python3 -m unittest discover -s tests -v

check:
	./agent-theme --check claude
	./agent-theme --check codex

install:
	mkdir -p "$(PREFIX)" "$(BINDIR)"
	rsync -a --exclude=__pycache__ agent_theme "$(PREFIX)"/
	cp agent-theme README.md LICENSE NOTICE "$(PREFIX)"/
	chmod +x "$(PREFIX)/agent-theme"
	ln -sf "$(PREFIX)/agent-theme" "$(BINDIR)/agent-theme"

check-install:
	@out="$$(rsync -anc --delete --exclude=__pycache__ agent_theme/ "$(PREFIX)/agent_theme/")"; \
	test -z "$$out" || { printf '%s\n' "$$out"; exit 1; }

uninstall:
	rm -f "$(BINDIR)/agent-theme"
	rm -rf "$(PREFIX)"
