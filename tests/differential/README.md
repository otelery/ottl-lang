# Differential parser tests

Feeds the same inputs to three independent parsers and reports every input where they disagree:

| Parser                           | Role                                          |
| -------------------------------- | --------------------------------------------- |
| upstream `pkg/ottl` (Participle) | **oracle** — `parseStatement/Condition/Value` |
| `OTTL.g4` (ANTLR, `Diff.java`)   | this repo's reference grammar                 |
| `tree-sitter-ottl/grammar.js`    | this repo's editor grammar                    |

```sh
make build                                  # ANTLR parser
(cd tree-sitter-ottl && npm ci)             # tree-sitter CLI
tests/differential/run.py                   # default: seed 1, ~10k inputs, report in build/differential/report.md
tests/differential/run.py --seed 7 --random 20000
tests/differential/run.py --upstream ~/src/opentelemetry-collector-contrib   # use a local checkout
tests/differential/run.py --ref <sha>       # pin an upstream commit
```

Needs `go`, `java`/`javac` + the ANTLR jar (autodetected like the `Makefile`; or set `ANTLR_JAR`), `node`, `git`.
The first run sparse-clones `pkg/ottl` into `build/differential/`.

## Inputs (`gen.py`, seeded)

- every line of `tests/conformance/*.ottl`, each in its natural mode (statement / condition / value);
- ~600 hand-written edge cases (numbers, signs, identifier classes, keywords, maps, keys, lambdas, escapes, whitespace);
- token- and character-level mutations of the corpus;
- random derivations from the SPEC grammar.

## Reading the report

`all three agree` is the goal. Disagreements are grouped by which engine differs and by upstream's error. Groups tagged
_expected_ are documented divergences and do not fail the run:

| Tag                                                | Why                                                                                       |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| post-parse semantic check (SPEC §4)                | grammar accepts, upstream rejects after parsing (casing, indexed editors, nested lambdas) |
| comments extension / file-grammar `;` / empty file | SPEC §6 tooling extensions                                                                |
| identifier-run gluing (upstream quirk)             | `S plit(` is `Split(` upstream (SPEC §2.5)                                                |
| integer-led key expression (upstream quirk)        | upstream rejects `x[1+1]` (SPEC §3.4)                                                     |
| keyword without word boundary                      | `andTest`, `A1notX`: upstream's `\b` keywords; Tree-sitter's lexer is context-aware       |
| lambda body greediness                             | upstream commits to a boolean body; ANTLR's adaptive parsing explores both                |

Exit status is 1 when unexpected disagreements remain, so this can gate CI. Tree-sitter has one start rule, so the
runner builds a private copy of `grammar.js` with extra `@@c` / `@@v` entry points for condition and value inputs.
