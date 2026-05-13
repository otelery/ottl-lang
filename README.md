# ottl-lang

Part of the [`otelery`](https://github.com/otelery) GitHub organisation:
`otelery/ottl-lang`.

A tool-neutral specification of the [OpenTelemetry Transformation
Language (OTTL)][upstream], plus a set of conformant tooling: an ANTLR4
grammar, a Tree-sitter grammar, a TextMate grammar, and a Language
Server Protocol scaffold.

> **Scope.** This repo is about OTTL the language. For tooling that
> understands OTTL strings embedded inside an OpenTelemetry Collector
> YAML config (pipeline graph, component schema, etc.), see the
> sibling `otelery/otelcol-lang` project (separate repository).

The reference implementation of OTTL lives in
[`open-telemetry/opentelemetry-collector-contrib`][upstream-repo]
(specifically [`pkg/ottl`][upstream-pkg]) and is written in Go using
Participle. This project's goals:

1. **One canonical grammar specification** that all parser
   implementations conform to — see [`SPEC.md`](./SPEC.md).
2. **Parsers for languages other than Go** generated from a single
   ANTLR4 grammar — Java, Python, JavaScript, C#, …
3. **Editor tooling**: syntax highlighting (Tree-sitter, TextMate) and
   an LSP for diagnostics, completion, and (eventually) hover and
   go-to-definition.

[upstream]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/LANGUAGE.md
[upstream-repo]: https://github.com/open-telemetry/opentelemetry-collector-contrib
[upstream-pkg]: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/pkg/ottl
[upstream-grammar]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/grammar.go

## Status

**Draft, version 0.1.** The specification and grammars are stable
enough to round-trip every test case in the upstream parser test
suite, but APIs may change as the LSP and tooling mature. See
[`CHANGELOG.md`](./CHANGELOG.md).

| Component              | State    | Coverage                                   |
| ---------------------- | -------- | ------------------------------------------ |
| [`SPEC.md`](./SPEC.md) | Draft    | Lexical + syntactic + semantic constraints |
| ANTLR4 grammar         | Working  | 373/373 conformance cases                  |
| Tree-sitter            | Working  | 373/373 conformance cases                  |
| TextMate               | Working  | All token classes from SPEC §2             |
| LSP server             | Scaffold | Diagnostics, completion stub               |

## Repository layout

```
.
├── SPEC.md                     # Single source of truth — read this first
├── OTTL.g4                     # ANTLR4 grammar (canonical generator input)
├── tree-sitter-ottl/           # Tree-sitter grammar.js + node bindings
├── textmate-ottl/              # ottl.tmLanguage.json
├── lsp-ottl/                   # TypeScript LSP server
├── tests/
│   ├── conformance/            # Test suites (one OTTL input per line)
│   ├── extract_upstream_tests.sh
│   └── run_conformance.sh      # Runs suites against ANTLR Java parser
├── CHANGELOG.md
└── LICENSE                     # Apache-2.0
```

To re-extract the upstream conformance suites, clone
[`open-telemetry/opentelemetry-collector-contrib`][upstream-repo] into
this directory (or symlink it) at `./opentelemetry-collector-contrib`
before running `tests/extract_upstream_tests.sh`. The upstream repo is
not vendored here.

## Quickstart

### Read the specification

Start with [`SPEC.md`](./SPEC.md). It defines the language using
W3C-style EBNF (§2 lexical, §3 syntactic), the semantic constraints
that EBNF can't express (§4), and operator precedence (§5).

### Generate a parser from the ANTLR grammar

```bash
# Java
antlr -Dlanguage=Java OTTL.g4 -o build/java
javac -cp /path/to/antlr-4.13-complete.jar build/java/*.java

# Go
antlr -Dlanguage=Go OTTL.g4 -o build/go

# Python
antlr -Dlanguage=Python3 OTTL.g4 -o build/python

# JavaScript
antlr -Dlanguage=JavaScript OTTL.g4 -o build/js
```

The grammar exposes three entry rules:

- `statement` — one OTTL statement (transform/route processor input).
- `condition` — one boolean expression (filter processor input).
- `file` — a `;`-separated sequence of statements (LSP / formatter).

### Run the conformance suite

```bash
# Build the Java parser first
antlr -Dlanguage=Java OTTL.g4 -o build/java
javac -cp /path/to/antlr-4.13-complete.jar build/java/*.java

# Run all suites
./tests/run_conformance.sh

# Or one suite, one entry point
./tests/run_conformance.sh tests/conformance/upstream_valid_conditions.ottl condition
./tests/run_conformance.sh tests/conformance/upstream_invalid_statements.ottl statement --expect-fail
```

### Use the Tree-sitter grammar

```bash
cd tree-sitter-ottl
npm install
npx tree-sitter generate
npx tree-sitter build         # produces ottl.so
echo 'set(attributes["x"], 1)' | npx tree-sitter parse -

# Run conformance suites through tree-sitter
./run-conformance.sh ../tests/conformance/valid_statements.ottl
./run-conformance.sh ../tests/conformance/upstream_valid_conditions.ottl --entry=condition
```

### Use the TextMate grammar

Point your editor at `textmate-ottl/ottl.tmLanguage.json`. The grammar
declares the scope `source.ottl` and the file extension `.ottl`.

### Run the LSP server

```bash
cd lsp-ottl
npm install
npm run build
node out/server.js --stdio
```

The server expects to find the Tree-sitter grammar at
`../tree-sitter-ottl` (override with `OTTL_TREE_SITTER_DIR`). It
provides:

- Incremental document sync.
- Parse-on-change diagnostics (errors and missing tokens).
- Trivial keyword completion.

What's deferred is documented inline at the top of `lsp-ottl/src/server.ts`.

## Conformance

Per `SPEC.md` §7, an implementation is conformant if it accepts every
input in `tests/conformance/upstream_valid_*.ottl` and rejects every
input in `tests/conformance/upstream_invalid_*.ottl`. The
`tests/conformance/upstream_postparse_*.ottl` suites are statements that
the grammar accepts but a host validator must reject for semantic
reasons (see SPEC §4.4, §4.5).

To re-extract from the upstream test files:

```bash
./tests/extract_upstream_tests.sh
```

## Contributing

The project follows the "spec first, implementation second" rule:

1. If you find a discrepancy between an implementation and `SPEC.md`,
   the spec wins — update the implementation.
2. If you find a discrepancy between `SPEC.md` and the upstream
   reference (`spec/grammar.go`), open an issue. The spec is meant to
   describe the upstream language, not redefine it.
3. New tooling (a parser in another language, an editor plugin) should
   add itself as a top-level directory and run the same conformance
   suites.

## License

Apache-2.0. See [`LICENSE`](./LICENSE).
