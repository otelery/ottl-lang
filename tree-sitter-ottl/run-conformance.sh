#!/usr/bin/env bash
# Run conformance suites through the Tree-sitter OTTL grammar.
#
# Uses `tree-sitter parse --quiet` and checks the exit code: zero means a
# successful parse, non-zero means errors in the tree.
#
# Usage: ./run-conformance.sh [file.ottl] [--expect-fail] [--entry=statement|condition]
set -uo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
TS="$DIR/node_modules/.bin/tree-sitter"

EXPECT_FAIL=0
ENTRY="statement"
FILES=()
for a in "$@"; do
    case "$a" in
        --expect-fail) EXPECT_FAIL=1 ;;
        --entry=*) ENTRY="${a#--entry=}" ;;
        *) FILES+=("$a") ;;
    esac
done
[[ ${#FILES[@]} -eq 0 ]] && {
    echo "usage: $0 <file.ottl> [--expect-fail] [--entry=condition]" >&2
    exit 2
}

cd "$DIR"   # tree-sitter resolves grammar from cwd

wrap() {
    if [[ "$ENTRY" == "condition" ]]; then
        printf 'set(x, true) where %s\n' "$1"
    else
        printf '%s\n' "$1"
    fi
}

GRAND_T=0; GRAND_F=0
for file in "${FILES[@]}"; do
    [[ ! -f "$file" ]] && { echo "skip: $file"; continue; }
    T=0; P=0; F=0
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "${line//[[:space:]]/}" ]] && continue
        [[ "${line# }" =~ ^# ]] && continue
        T=$((T+1))
        wrap "$line" > /tmp/_ottl.in
        if "$TS" parse --quiet /tmp/_ottl.in >/dev/null 2>&1; then ok=1; else ok=0; fi
        if (( EXPECT_FAIL == 0 && ok == 1 )) || (( EXPECT_FAIL == 1 && ok == 0 )); then
            P=$((P+1))
        else
            F=$((F+1))
            printf '  FAIL: %s\n' "$line"
        fi
    done < "$file"
    printf '%s: %d/%d passed (entry=%s, expect-fail=%d)\n' "$(basename "$file")" "$P" "$T" "$ENTRY" "$EXPECT_FAIL"
    GRAND_T=$((GRAND_T+T)); GRAND_F=$((GRAND_F+F))
done
echo "Total: $((GRAND_T-GRAND_F))/$GRAND_T passed"
[[ $GRAND_F -eq 0 ]]
