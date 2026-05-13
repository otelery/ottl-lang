#!/usr/bin/env bash
# Extract OTTL test cases from the upstream collector-contrib parser tests
# into per-entrypoint conformance suites.
#
# Output (in tests/conformance/):
#   upstream_valid_statements.ottl    - Test_parseStatement (no wantErr)
#   upstream_invalid_statements.ottl  - Test_parseStatement wantErr: true
#   upstream_postparse_statements.ottl- Test_parseStatement wantErrContaining (semantic, not grammar)
#   upstream_valid_conditions.ottl    - Test_parseCondition / Test_parseWhere (no wantErr)
#   upstream_invalid_conditions.ottl  - parseCondition/parseWhere wantErr: true
#   upstream_postparse_conditions.ottl- parseCondition wantErrContaining
#   upstream_valid_value_expr.ottl    - Test_parseValueExpression (no wantErr)
#   upstream_invalid_value_expr.ottl  - Test_parseValueExpression wantErr
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/opentelemetry-collector-contrib/pkg/ottl"
OUT="$ROOT/tests/conformance"
mkdir -p "$OUT"

# awk extractor: track current Test_<name> function and emit
#   <function>\t<status>\t<entry>\t<input>
# where status ∈ {valid, invalid, postparse} and entry ∈ {statement, condition, valueExpression}.
awk_extract() {
    local file="$1"
    awk '
        /^func Test_parse[A-Z][A-Za-z0-9_]*\s*\(/ {
            match($0, /Test_parse[A-Za-z0-9_]+/)
            fn = substr($0, RSTART, RLENGTH)
            next
        }
        # field-style entries: { entry: `...`, [wantErr/wantErrContaining]... }
        /^[[:space:]]*\{(statement|condition|valueExpression):[[:space:]]+`/ {
            line = $0
            # Extract entry type
            match(line, /(statement|condition|valueExpression):/)
            entry = substr(line, RSTART, RLENGTH-1)
            # Test_parseWhere wraps inputs as `set(...) where <input>`, so the
            # input itself is a condition, not a statement.
            if (fn == "Test_parseWhere") entry = "condition"
            # Extract content between first pair of backticks
            i = index(line, "`")
            rest = substr(line, i+1)
            j = index(rest, "`")
            input = substr(rest, 1, j-1)
            # Status
            status = "valid"
            if (line ~ /wantErr:[[:space:]]*true/)         status = "invalid"
            else if (line ~ /wantErrContaining/)            status = "postparse"
            print fn "\t" status "\t" entry "\t" input
        }
        # Multi-line struct entries: `statement: \`...\`,$` then `wantErr: true,` later
        /^[[:space:]]*statement:[[:space:]]+`[^`]*`,$/ {
            entry = (fn == "Test_parseWhere") ? "condition" : "statement"
            i = index($0, "`")
            rest = substr($0, i+1)
            j = index(rest, "`")
            input = substr(rest, 1, j-1)
            print fn "\tvalid\t" entry "\t" input
        }
    ' "$file"
}

for src in parser_test.go expression_test.go; do
    awk_extract "$SRC/$src"
done | sort -u > /tmp/ottl_extract.tsv

echo "Total extracted: $(wc -l < /tmp/ottl_extract.tsv)"

emit() {
    local out="$1"; shift
    local desc="$1"; shift
    {
        echo "# $desc"
        echo "# Auto-extracted from opentelemetry-collector-contrib/pkg/ottl/{parser,expression}_test.go"
        echo "# by tests/extract_upstream_tests.sh — do not edit by hand."
        echo ""
        awk -F'\t' "$1" /tmp/ottl_extract.tsv | sort -u
    } > "$out"
    echo "  $(grep -cv '^[[:space:]]*\(#\|$\)' "$out") $out"
}

# Two cases are grammar errors upstream (stricter `[A-Z][A-Z0-9_]*` tokenizer +
# enum lookahead) but accepted by our SPEC §2.5 single-token tokenizer. They
# remain semantic errors and route to the postparse suite:
#   - `test() where one() == 1`   -- lowercase fn in value position (§4.4)
#   - `"test" == Foo`             -- mixed-case identifier as enum (§4.2)
SEMANTIC_ONLY='$4 == "test() where one() == 1" || $4 == "\"test\" == Foo"'

emit "$OUT/upstream_valid_statements.ottl"  "Valid OTTL statements" \
    '$2=="valid" && $3=="statement" {print $4}'
emit "$OUT/upstream_invalid_statements.ottl" "Invalid OTTL statements (grammar errors)" \
    "\$2==\"invalid\" && \$3==\"statement\" && !($SEMANTIC_ONLY) {print \$4}"
emit "$OUT/upstream_postparse_statements.ottl" "OTTL statements that fail post-parse semantic validation" \
    "(\$2==\"postparse\" && \$3==\"statement\") || (\$2==\"invalid\" && \$3==\"statement\" && ($SEMANTIC_ONLY)) {print \$4}"
emit "$OUT/upstream_valid_conditions.ottl" "Valid OTTL conditions" \
    '$2=="valid" && $3=="condition" {print $4}'
emit "$OUT/upstream_invalid_conditions.ottl" "Invalid OTTL conditions (grammar errors)" \
    "\$2==\"invalid\" && \$3==\"condition\" && !($SEMANTIC_ONLY) {print \$4}"
emit "$OUT/upstream_postparse_conditions.ottl" "OTTL conditions that fail post-parse semantic validation" \
    "(\$2==\"postparse\" && \$3==\"condition\") || (\$2==\"invalid\" && \$3==\"condition\" && ($SEMANTIC_ONLY)) {print \$4}"
emit "$OUT/upstream_valid_value_expr.ottl" "Valid OTTL value expressions (Test_parseValueExpression)" \
    '$2=="valid" && $3=="valueExpression" {print $4}'
emit "$OUT/upstream_invalid_value_expr.ottl" "Invalid OTTL value expressions" \
    '$2=="invalid" && $3=="valueExpression" {print $4}'
