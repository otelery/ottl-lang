# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version policy for `SPEC.md` is documented in §8 of that document.

## [Unreleased]

### Changed

- Project name is now `ottl-lang`, hosted under the
  [`otelery`](https://github.com/otelery) GitHub organisation as
  `otelery/ottl-lang` (was the descriptive
  "opentelemetry-transformation-language"). Sub-package names
  (`ottl-lsp`, `tree-sitter-ottl`) are unchanged and remain the
  intended publish names.

### Added

- [`docs/otelcol-lang.md`](./docs/otelcol-lang.md) — planning notes
  for a separate `otelcol-lang` project (YAML LSP for the
  OpenTelemetry Collector config with embedded OTTL). Captures the
  architecture, the obligations on this repo, and the bootstrapping
  order so the work can start without retrofits.

## [0.1.0] — 2026-05-10

Initial public draft. Establishes the project as a tool-neutral
specification of OTTL plus a set of conformant tooling.

### Added

- **`SPEC.md` (Draft 0.1).** W3C-style EBNF grammar covering the lexical
  structure (§2), syntactic grammar (§3), semantic constraints (§4),
  precedence table (§5), an extension for multi-statement files (§6),
  conformance criteria (§7), versioning rules (§8), and a cross-reference
  appendix to `spec/grammar.go`.
- **ANTLR4 grammar (`OTTL.g4`).** Reconciled against `SPEC.md`; rejects
  `editor[…]` at parse time per §4.5; adds a `file` entry rule per §6.1;
  skips `//` and `/* */` comments per §6.2.
- **Tree-sitter grammar (`tree-sitter-ottl/grammar.js`).** GLR-based
  parser using the same EBNF as the ANTLR grammar; ships with
  `run-conformance.sh` that runs every conformance suite through the
  `tree-sitter parse` CLI.
- **TextMate grammar (`textmate-ottl/ottl.tmLanguage.json`).** Token
  scopes for editors (`entity.name.function.editor`), converters
  (`entity.name.function.converter`), enums (`constant.other.enum`),
  paths (`variable.other`), keywords, operators, and literals.
- **LSP scaffold (`lsp-ottl/`).** TypeScript Node.js server using
  `vscode-languageserver`. Implements lifecycle, incremental document
  sync, parse-on-change diagnostics (via `tree-sitter parse`
  subprocess), and a keyword completion stub.
- **Conformance suites (`tests/conformance/`).**
  - `valid_statements.ottl` (230 cases, hand-curated).
  - `valid_conditions.ottl` (14 cases).
  - `upstream_valid_statements.ottl` (46), `upstream_valid_conditions.ottl`
    (29), `upstream_valid_value_expr.ottl` (4) — extracted from
    [`pkg/ottl/parser_test.go`][upstream-parser-test] and
    [`pkg/ottl/expression_test.go`][upstream-expression-test] in
    [`open-telemetry/opentelemetry-collector-contrib`][upstream-repo].
  - `upstream_invalid_statements.ottl` (30), `upstream_invalid_conditions.ottl`
    (24), `upstream_invalid_value_expr.ottl` (4) — same source, `wantErr`
    cases.
  - `upstream_postparse_*.ottl` — `wantErrContaining` cases that pass
    grammar validation but fail post-parse semantic checks.
- **Test runners.**
  - `tests/run_conformance.sh` — runs any suite against the ANTLR-generated
    Java parser via `grun`.
  - `tests/extract_upstream_tests.sh` — re-extracts the upstream suites.
  - `tree-sitter-ottl/run-conformance.sh` — runs any suite against the
    Tree-sitter parser.

### Status

- ANTLR parser: 230/230 valid + 14/14 valid conditions + 46/46 upstream valid
  statements + 29/29 upstream valid conditions + 30/30 upstream invalid
  statements + 24/24 upstream invalid conditions = **373/373** parseable
  cases pass.
- Tree-sitter parser: same, with the conditional suites wrapped via a
  synthetic `set(x, true) where …` prefix.
- Two upstream invalid cases (`test() where one() == 1`, `"test" == Foo`)
  are accepted by both grammars per the SPEC §2.5 single-token tokenizer
  decision; they are routed to the postparse suite for the host
  validator to reject.

### Known limitations

- The LSP server uses a per-change `tree-sitter parse` subprocess, which
  is fine for files but not for high-frequency typing. A `web-tree-sitter`
  WASM build is the planned next step.
- No parser is currently published as an installable package
  (npm/PyPI/Go module). The ANTLR `.g4` is the canonical source for
  generating in-tree.
- No formatter, no semantic-token highlighting in the LSP, no hover or
  go-to-definition (these need a function and path registry).

### Repository layout

- `archive/` — superseded agent-generated documentation and the original
  `OTTL.g4` v1.0 build artifacts. Kept for history.
- `opentelemetry-collector-contrib/` — vendored copy of
  [`open-telemetry/opentelemetry-collector-contrib`][upstream-repo],
  used as the canonical reference for both the grammar and the
  conformance suites.
- `spec/` — vendored upstream [`pkg/ottl`][upstream-pkg] files
  ([`grammar.go`][upstream-grammar],
  [`LANGUAGE.md`][upstream-langmd], test files, playground).

[Unreleased]: ./
[0.1.0]: ./
[upstream-repo]: https://github.com/open-telemetry/opentelemetry-collector-contrib
[upstream-pkg]: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/pkg/ottl
[upstream-grammar]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/grammar.go
[upstream-langmd]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/LANGUAGE.md
[upstream-parser-test]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/parser_test.go
[upstream-expression-test]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/expression_test.go
