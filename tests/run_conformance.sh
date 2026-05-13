#!/usr/bin/env bash
# OTTL conformance test runner.
#
# Usage:
#   ./tests/run_conformance.sh                           # all suites
#   ./tests/run_conformance.sh tests/conformance/valid_statements.ottl statement
#   ./tests/run_conformance.sh tests/conformance/invalid_statements.ottl statement --expect-fail
#
# Each test file is line-oriented:
#   - Lines starting with `#` are comments (printed, not tested).
#   - Blank lines are ignored.
#   - Every other line is a single OTTL input fed to the parser.
#
# In --expect-fail mode, parse errors count as PASS and clean parses as FAIL.
set -uo pipefail

INVOKED_FROM="$PWD"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ANTLR_JAR="${ANTLR_JAR:-/home/linuxbrew/.linuxbrew/Cellar/antlr/4.13.2/antlr-4.13.2-complete.jar}"
BUILD_DIR="$ROOT/build/java"
# grun's TestRig only resolves grammar classes from `.` in CLASSPATH —
# absolute entries are ignored. Run from BUILD_DIR.
export CLASSPATH=".:$ANTLR_JAR"

if [[ ! -d "$BUILD_DIR" ]]; then
    echo "Generated parser missing. Run: make build" >&2
    exit 2
fi
cd "$BUILD_DIR"

EXPECT_FAIL=0
FILES=()
ENTRY="statement"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --expect-fail) EXPECT_FAIL=1; shift ;;
        statement|condition|file) ENTRY="$1"; shift ;;
        *) FILES+=("$1"); shift ;;
    esac
done

if [[ ${#FILES[@]} -eq 0 ]]; then
    FILES=(
        "$ROOT/tests/conformance/valid_statements.ottl"
        "$ROOT/tests/conformance/valid_conditions.ottl:condition"
    )
fi

# Resolve any relative file paths to absolute before cd-ing into BUILD_DIR.
RESOLVED=()
for spec in "${FILES[@]}"; do
    file="$spec"; suffix=""
    if [[ "$spec" == *:* ]]; then
        file="${spec%%:*}"
        suffix=":${spec##*:}"
    fi
    if [[ "$file" != /* ]]; then
        file="$INVOKED_FROM/$file"
    fi
    RESOLVED+=("$file$suffix")
done
FILES=("${RESOLVED[@]}")

run_one() {
    local input="$1"
    local entry="$2"
    # grun reads from stdin; suppress trees, capture errors only.
    local out
    out=$(printf '%s' "$input" | grun OTTL "$entry" 2>&1)
    [[ -z "$out" ]]
}

GRAND_TOTAL=0
GRAND_FAIL=0

for spec in "${FILES[@]}"; do
    local_entry="$ENTRY"
    file="$spec"
    if [[ "$spec" == *:* ]]; then
        file="${spec%%:*}"
        local_entry="${spec##*:}"
    fi
    [[ -f "$file" ]] || { echo "skip: $file (not found)"; continue; }
    echo "=== $file (entry=$local_entry, expect-fail=$EXPECT_FAIL) ==="
    total=0; pass=0; fail=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "${line//[[:space:]]/}" ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        total=$((total+1))
        if run_one "$line" "$local_entry"; then
            ok=1
        else
            ok=0
        fi
        if [[ $EXPECT_FAIL -eq 0 && $ok -eq 1 ]] || [[ $EXPECT_FAIL -eq 1 && $ok -eq 0 ]]; then
            pass=$((pass+1))
        else
            fail=$((fail+1))
            printf '  FAIL: %s\n' "$line"
        fi
    done < "$file"
    echo "  $pass/$total passed"
    GRAND_TOTAL=$((GRAND_TOTAL+total))
    GRAND_FAIL=$((GRAND_FAIL+fail))
done

echo
echo "Total: $((GRAND_TOTAL-GRAND_FAIL))/$GRAND_TOTAL passed"
[[ $GRAND_FAIL -eq 0 ]]
