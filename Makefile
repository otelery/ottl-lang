# OTTL language — build and test entry points.
#
# Requires: antlr 4.13+, javac, java. Set ANTLR_JAR if `antlr` is not on PATH
# or autodetection fails.

GRAMMAR     := OTTL.g4
BUILD_DIR   := build/java
STAMP       := $(BUILD_DIR)/.stamp

# Autodetect the ANTLR complete jar by parsing the `antlr` wrapper, then
# falling back to common install locations. Override with `make ANTLR_JAR=...`.
ANTLR_JAR ?= $(shell \
    if command -v antlr >/dev/null 2>&1; then \
        grep -oE '/[^ "]*antlr-[0-9.]+-complete\.jar' "$$(command -v antlr)" 2>/dev/null | head -1; \
    fi)
ifeq ($(ANTLR_JAR),)
ANTLR_JAR := $(firstword $(wildcard \
    /usr/local/lib/antlr-*-complete.jar \
    /usr/share/java/antlr-*-complete.jar \
    /opt/homebrew/Cellar/antlr/*/libexec/antlr-*-complete.jar \
    /home/linuxbrew/.linuxbrew/Cellar/antlr/*/antlr-*-complete.jar \
    $(HOME)/.local/share/antlr/antlr-*-complete.jar))
endif

.PHONY: help build conformance test clean

help:
	@echo "Targets:"
	@echo "  build         Generate and compile the ANTLR Java parser"
	@echo "  conformance   Run the conformance suites (depends on build)"
	@echo "  test          Alias for conformance"
	@echo "  clean         Remove $(BUILD_DIR)"
	@echo ""
	@echo "Variables:"
	@echo "  ANTLR_JAR     Path to antlr-*-complete.jar (autodetected: $(ANTLR_JAR))"

build: $(STAMP)

$(STAMP): $(GRAMMAR)
	@if [ -z "$(ANTLR_JAR)" ]; then \
	    echo "error: ANTLR jar not found. Install antlr 4.13+ or set ANTLR_JAR=..." >&2; \
	    exit 1; \
	fi
	@mkdir -p $(BUILD_DIR)
	java -jar "$(ANTLR_JAR)" -Dlanguage=Java $(GRAMMAR) -o $(BUILD_DIR)
	javac -cp "$(ANTLR_JAR):$(BUILD_DIR)" $(BUILD_DIR)/*.java
	@touch $@

conformance: build
	ANTLR_JAR="$(ANTLR_JAR)" ./tests/run_conformance.sh
	ANTLR_JAR="$(ANTLR_JAR)" ./tests/run_conformance.sh tests/conformance/lambda_invalid_statements.ottl statement --expect-fail

test: conformance

clean:
	rm -rf $(BUILD_DIR)
