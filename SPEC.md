# OpenTelemetry Transformation Language — Specification

**Status:** Draft 0.1
**Source of truth:** This document. All parser implementations (ANTLR `.g4`, Tree-sitter `grammar.js`, TextMate `.tmLanguage.json`, LSP) MUST conform to it.
**Reference implementation:** [`pkg/ottl`][upstream-pkg] in [`open-telemetry/opentelemetry-collector-contrib`][upstream-repo] ([`spec/grammar.go`][upstream-grammar], Participle).

---

## 1. Notation

| Form        | Meaning                                |
| ----------- | -------------------------------------- |
| `A ::= B`   | `A` is defined as `B`                  |
| `A B`       | concatenation                          |
| `A \| B`    | alternation                            |
| `A?`        | optional (zero or one)                 |
| `A*`        | zero or more                           |
| `A+`        | one or more                            |
| `( ... )`   | grouping                               |
| `'x'`       | literal terminal                       |
| `"x"`       | literal terminal (alternative quoting) |
| `[a-z]`     | character class                        |
| `[^x]`      | negated character class                |
| `/* ... */` | non-normative comment                  |

Productions whose names are `UPPER_CASE` are **lexical** (tokens); productions whose names are `lowerCamelCase` are **syntactic** (parser rules). Whitespace between tokens is permitted and ignored everywhere except inside string literals.

---

## 2. Lexical structure

### 2.1 Whitespace

```
WS         ::= [ \t\r\n]+        /* skipped */
```

OTTL has **no comment syntax**. Tooling MAY add comments at the file/config level; see §6.

### 2.2 Keywords

The following identifiers are reserved and MUST NOT be used as editor, converter, path, or argument names:

```
WHERE      ::= 'where'
NOT        ::= 'not'
AND        ::= 'and'
OR         ::= 'or'
NIL        ::= 'nil'
TRUE       ::= 'true'
FALSE      ::= 'false'
```

`true` and `false` together form the `BOOLEAN` token.

### 2.3 Literals

```
BOOLEAN    ::= 'true' | 'false'
BYTES      ::= '0x' [a-fA-F0-9]+
FLOAT      ::= [+-]? [0-9]* '.' [0-9]+ ([eE] [+-]? [0-9]+)?
INT        ::= [+-]? [0-9]+
STRING     ::= '"' ( '\' . | [^\\"] )* '"'
```

Lexer precedence (longest-match, then declaration order): `BYTES` before `INT` (the `0x` prefix), `FLOAT` before `INT` (the decimal point), keywords before identifiers.

String escapes follow Go's interpreted string rules.

### 2.4 Operators and punctuation

```
EQ         ::= '=='
NEQ        ::= '!='
LTE        ::= '<='
GTE        ::= '>='
LT         ::= '<'
GT         ::= '>'
PLUS       ::= '+'
MINUS      ::= '-'
MULT       ::= '*'
DIV        ::= '/'
EQUAL      ::= '='
LPAREN     ::= '('
RPAREN     ::= ')'
LBRACE     ::= '{'
RBRACE     ::= '}'
LBRACKET   ::= '['
RBRACKET   ::= ']'
DOT        ::= '.'
COMMA      ::= ','
COLON      ::= ':'
```

Multi-character operators MUST be matched before their single-character prefixes (e.g. `==` before `=`, `<=` before `<`).

### 2.5 Identifiers

OTTL distinguishes identifiers by the case of their first character. The reference implementation tokenizes maximal lowercase and uppercase runs separately and concatenates them at the parser level; conformant lexers MAY instead emit a single token whose first character determines its class. Both strategies accept the same language.

```
LOWER_ID   ::= [a-z] [a-zA-Z0-9_]*    /* editors, fields, argument names, path context */
UPPER_ID   ::= [A-Z] [a-zA-Z0-9_]*    /* converters, enums */
```

Examples:

| Token              | Class      | Used as        |
| ------------------ | ---------- | -------------- |
| `set`              | `LOWER_ID` | editor name    |
| `attributes`       | `LOWER_ID` | path field     |
| `headerDelimiter`  | `LOWER_ID` | named argument |
| `ParseJSON`        | `UPPER_ID` | converter name |
| `SPAN_KIND_SERVER` | `UPPER_ID` | enum symbol    |

> **Note (semantic, not lexical):** the _casing convention_ is enforced after parsing — see §4.1.

---

## 3. Syntactic grammar

### 3.1 Entry points

A conformant parser MUST expose at least these two entry points:

```
statement  ::= editor whereClause? EOF        /* used by transform/route processors */
condition  ::= booleanExpr EOF                /* used by filter processor */
```

A multi-statement file rule is defined in §6.

### 3.2 Statement structure

```
whereClause::= WHERE booleanExpr

editor     ::= LOWER_ID LPAREN arguments? RPAREN
converter  ::= UPPER_ID LPAREN arguments? RPAREN keys?

arguments  ::= argument (COMMA argument)*
argument   ::= (LOWER_ID EQUAL)? value
             | (LOWER_ID EQUAL)? UPPER_ID    /* bare converter/enum name as argument */
```

The bare-`UPPER_ID` alternative in `argument` allows passing a function reference by name (e.g. `aggregate(metrics, Sum)`); see the reference implementation's `argument.FunctionName` field.

### 3.3 Values

```
value      ::= NIL
             | mathExprLiteral                /* literal not followed by + - * / */
             | mathExpression
             | BYTES
             | STRING
             | BOOLEAN
             | enumValue
             | mapValue
             | listValue

enumValue  ::= UPPER_ID                       /* not followed by '(' — see §4.2 */
listValue  ::= LBRACKET (value (COMMA value)*)? RBRACKET
mapValue   ::= LBRACE (mapItem (COMMA mapItem)* COMMA?)? RBRACE
mapItem    ::= STRING COLON value
```

### 3.4 Paths and keys

```
path       ::= (LOWER_ID DOT)? field (DOT field)*
field      ::= LOWER_ID keys?
keys       ::= key+
key        ::= LBRACKET keyValue RBRACKET
keyValue   ::= STRING                         /* map key */
             | INT                            /* slice index */
             | mathExpression                 /* dynamic key */
             | mathExprLiteral                /* simple expression */
```

The first segment of a `path` (when present) is interpreted by the host as a _context_ identifier (`resource`, `span`, `metric`, `log`, `datapoint`, `instrumentation_scope`, …). The grammar does not enforce this — see §4.3.

### 3.5 Math expressions

Precedence (lowest to highest): additive < multiplicative < parenthesized.

```
mathExpression ::= addSubTerm ((PLUS | MINUS) addSubTerm)*
addSubTerm     ::= mathValue ((MULT | DIV) mathValue)*
mathValue      ::= mathExprLiteral
                 | LPAREN mathExpression RPAREN
mathExprLiteral::= editor                     /* SYNTACTIC ONLY — rejected, see §4.4 */
                 | converter
                 | FLOAT
                 | INT
                 | path
```

### 3.6 Boolean expressions

Precedence (lowest to highest): `or` < `and` < `not` < parenthesized / atom.

```
booleanExpr  ::= orTerm (OR orTerm)*
orTerm       ::= andTerm (AND andTerm)*
andTerm      ::= NOT? booleanValue
booleanValue ::= comparison
               | BOOLEAN
               | converter                    /* converter returning bool */
               | LPAREN booleanExpr RPAREN
comparison   ::= value comparisonOp value
comparisonOp ::= EQ | NEQ | LTE | GTE | LT | GT
```

---

## 4. Semantic constraints

These rules cannot be expressed in pure EBNF. Implementations MUST enforce them after parsing (or via parser predicates) and produce diagnostic errors with source positions.

### 4.1 Identifier casing

| Construct     | First character | Token rule used | Enforced by                  |
| ------------- | --------------- | --------------- | ---------------------------- |
| Editor        | lowercase       | `LOWER_ID`      | grammar (rule `editor`)      |
| Converter     | uppercase       | `UPPER_ID`      | grammar (rule `converter`)   |
| Enum          | uppercase       | `UPPER_ID`      | grammar (`enumValue`) + §4.2 |
| Path field    | lowercase       | `LOWER_ID`      | grammar (rule `field`)       |
| Argument name | lowercase       | `LOWER_ID`      | grammar (rule `argument`)    |

If a parser encounters `UPPER_ID '(' ... ')'` where `editor` is expected, it MUST emit:

> `editor names must start with a lowercase letter but got '<Name>'`

If a parser encounters `LOWER_ID '(' ... ')'` inside a `mathExprLiteral` (where a converter is expected), it MUST emit:

> `converter names must start with an uppercase letter but got '<name>'`

### 4.2 Enum vs. converter disambiguation

`UPPER_ID` is a `converter` if followed by `LPAREN`, otherwise an `enumValue`. Implementations SHOULD use one-token lookahead. ANTLR4 adaptive prediction handles this without explicit predicates; PEG/Tree-sitter implementations should encode the lookahead.

### 4.3 Path context

The grammar accepts both `resource.attributes["x"]` and `attributes["x"]`. Whether the first segment is a context identifier or a field name is determined by the host's `PathExpressionParser`. The parser MUST surface the position of the first segment so the host can rewrite or reject it.

### 4.4 Editors are not values

`mathExprLiteral` syntactically permits `editor` so that the parser can produce a precise error message rather than a generic syntax failure. Implementations MUST reject any `editor` occurring inside a `value`, `mathExprLiteral`, or `comparison` with:

> `converter names must start with an uppercase letter but got '<name>'`

(The reference implementation reuses the casing error; an implementation MAY emit a more specific message.)

### 4.5 Editors cannot be indexed

The grammar does **not** allow `editor` followed by `keys`. Some historical implementations accepted `editor keys?` and rejected it post-parse; conformant new implementations MUST reject it at the grammar level. Error message:

> `only paths and converters may be indexed, not editors, but got <name>[<keys>]`

### 4.6 Argument ordering

Within a single `arguments` list:

1. All positional arguments MUST precede all named arguments.
2. Argument names MUST be unique within the call.
3. Optional arguments may be skipped only when subsequent arguments are named.

These rules are enforced by the host's function registry, not by the grammar.

### 4.7 Math type rules

Math operations are evaluated at runtime. The grammar does not type-check.

- `int64 op int64 → int64` (Go integer division semantics)
- `float64 op float64 → float64`
- Mixing `int64` and `float64` in one expression is a runtime error.
- `time.Time` and `time.Duration` support only `+` and `-` per the table in `LANGUAGE.md` §Math Expressions.
- Division by zero is a runtime error (not a panic).

### 4.8 Comparison rules

See `LANGUAGE.md` §Comparison Rules. Numeric comparisons widen to `float64` when types differ; non-primitive types support only `==` and `!=`. Implementations MUST NOT attempt static type-checking of comparisons.

---

## 5. Operator precedence (summary)

From lowest to highest binding:

| Level | Operator                     | Associativity | Category   |
| ----- | ---------------------------- | ------------- | ---------- |
| 1     | `or`                         | left          | boolean    |
| 2     | `and`                        | left          | boolean    |
| 3     | `not`                        | prefix        | boolean    |
| 4     | `==` `!=` `<` `<=` `>` `>=`  | non-assoc     | comparison |
| 5     | `+` `-`                      | left          | arithmetic |
| 6     | `*` `/`                      | left          | arithmetic |
| 7     | `( ... )` `[ ... ]` `f(...)` | —             | primary    |

Comparisons are non-associative: `a == b == c` is a syntax error.

---

## 6. Files of statements (extension)

The reference implementation parses one statement per call and lets the host (YAML config, processor) supply the list. For tooling (LSP, formatters, CLI validators) a file-level grammar is convenient.

### 6.1 File grammar (informative)

```
file       ::= (statement statementSep)* statement? EOF
statementSep::= NEWLINE+ | ';'
NEWLINE    ::= '\r'? '\n'
```

### 6.2 Comments (extension, tooling-only)

Conformant _parsers_ MUST reject comments unless the host explicitly enables them. When enabled, comments are tokenized and skipped:

```
LINE_COMMENT  ::= '//' [^\n]*
BLOCK_COMMENT ::= '/*' (.|NEWLINE)*? '*/'
```

Comments MUST NOT appear inside `STRING`, `BYTES`, or between the parts of a multi-character operator.

> **Compatibility:** The OpenTelemetry Collector's transform processor does not recognize comments. Files using §6.2 must be preprocessed before being passed to the upstream parser.

---

## 7. Conformance

An implementation is _conformant_ if it:

1. Accepts every statement in `test_cases.ottl` (the conformance suite, currently 230 cases).
2. Rejects every input listed in the negative test suite (TODO: extract from `expression_test.go`).
3. Produces the diagnostic messages specified in §4 with byte-accurate source positions.
4. Round-trips an AST → text formatter such that re-parsing yields a structurally equal AST (whitespace insensitive).

A _strictly_ conformant implementation additionally tokenizes identifiers using the maximal-run strategy of the reference Participle lexer (§2.5).

---

## 8. Versioning

This document is versioned independently of the upstream collector. Version increments:

- **Patch** — clarifications, typo fixes, no grammar change.
- **Minor** — additions that all prior conformant inputs continue to parse identically (e.g. adding §6 file grammar).
- **Major** — any change that could reject a previously accepted input.

| Version | Date       | Notes                                                                   |
| ------- | ---------- | ----------------------------------------------------------------------- |
| 0.1     | 2026-05-10 | Initial draft from `OTTL.g4` and [`spec/grammar.go`][upstream-grammar]. |

---

## 9. Non-goals

- **Static type checking.** OTTL is dynamically typed at the value level; type errors surface at runtime.
- **A canonical function library.** The set of editors and converters is host-supplied and varies across processors. The spec defines call syntax (§3) and the **schema** for describing a registry (§10); it does not enumerate functions. A reference catalog derived from upstream `ottlfuncs` ships separately under `functions/`.
- **Path semantics.** The interpretation of `resource.attributes["x"]` is the host's responsibility.
- **Evaluation semantics.** This spec defines syntax and the diagnostics tied to it. Evaluation is normative in [`LANGUAGE.md`][upstream-langmd] and the [reference implementation][upstream-pkg].

---

## 10. Function signature schema

This section is **normative** for the _shape_ of function-registry data, not for the membership of any registry. A host advertises its registry as a document conforming to §10; tooling (LSP completion, hover, signature help, diagnostics) consumes it. See [`functions/SCHEMA.md`](./functions/SCHEMA.md) for the JSON Schema and a worked example.

### 10.1 Registry document

A registry is a flat list of function entries plus a small header:

```
registry        ::= header functionEntry+
header          ::= name version ottlSpecVersion sourceRef?
functionEntry   ::= name kind parameters returnType description? examples? since?
```

- `kind ∈ { "editor", "converter" }`. MUST agree with the casing of `name` per §4.1 (`editor` → `LOWER_ID`, `converter` → `UPPER_ID`).
- `name` MUST be a valid `LOWER_ID` or `UPPER_ID` per §2.5.
- `sourceRef` is a commit hash / tag of the upstream this registry was generated from, when applicable.

### 10.2 Parameter descriptors

Each parameter has a `name` (valid `LOWER_ID`, §2.5), a `type` (§10.3), and flags:

| Flag       | Meaning                                                                |
| ---------- | ---------------------------------------------------------------------- |
| `optional` | May be omitted; when omitted by position, all later args MUST be named |
| `variadic` | Repeats; MUST be the last positional parameter; type is element type   |
| `target`   | `true` for the lvalue of an editor (the `GetSetter` slot)              |

Argument-ordering rules from §4.6 are normative; §10 does not relax them.

### 10.3 Type language

The type expression grammar is closed. Tooling MUST reject unknown atoms.

```
type        ::= atom
              | 'Optional<' type '>'
              | 'List<' type '>'
              | 'Getter<' valueAtom '>'           /* coercing reader */
              | 'Setter<' valueAtom '>'           /* editor target (lvalue) */
              | 'Enum<' enumName '>'              /* host-defined symbol set */
              | 'FunctionRef'                     /* bare UPPER_ID argument, §3.2 */

atom        ::= valueAtom | pdataAtom
valueAtom   ::= 'String' | 'Int' | 'Float' | 'Bool' | 'Bytes'
              | 'Time' | 'Duration' | 'Any'
pdataAtom   ::= 'PMap' | 'PSlice' | 'PValue'
```

Mapping from the reference implementation's Go types is normative:

| Go type                                        | §10.3 type                                    |
| ---------------------------------------------- | --------------------------------------------- |
| `string`, `int64`, `float64`, `bool`, `[]byte` | `String` / `Int` / `Float` / `Bool` / `Bytes` |
| `ottl.Getter[K]`                               | `Getter<Any>`                                 |
| `ottl.StringGetter[K]`                         | `Getter<String>`                              |
| `ottl.IntGetter[K]`                            | `Getter<Int>`                                 |
| `ottl.FloatGetter[K]`                          | `Getter<Float>`                               |
| `ottl.BoolGetter[K]`                           | `Getter<Bool>`                                |
| `ottl.StringLikeGetter[K]`                     | `Getter<String>` _(coerces — see §10.4)_      |
| `ottl.FloatLikeGetter[K]`                      | `Getter<Float>` _(coerces)_                   |
| `ottl.IntLikeGetter[K]`                        | `Getter<Int>` _(coerces)_                     |
| `ottl.ByteSliceLikeGetter[K]`                  | `Getter<Bytes>` _(coerces)_                   |
| `ottl.PMapGetter[K]`                           | `Getter<PMap>`                                |
| `ottl.PSliceGetter[K]`                         | `Getter<PSlice>`                              |
| `ottl.TimeGetter[K]`                           | `Getter<Time>`                                |
| `ottl.DurationGetter[K]`                       | `Getter<Duration>`                            |
| `ottl.FunctionGetter[K]`                       | `FunctionRef`                                 |
| `ottl.GetSetter[K]` (target field)             | `Setter<Any>`                                 |
| `ottl.Optional[T]`                             | `Optional<T'>`                                |
| `[]T`                                          | `List<T'>` (variadic when in tail position)   |

`Like` variants are not a separate type; they are a runtime coercion flag (§10.4) on a `Getter<...>`.

### 10.4 Coercion flag

Parameter descriptors MAY carry `coerce: true` to indicate the host accepts cross-type inputs and converts them (the upstream `*LikeGetter` interfaces). Tooling SHOULD suppress type-mismatch diagnostics on such parameters and instead surface them as info-level notes.

### 10.5 Return type

`returnType` is a §10.3 `type`. For editors, `returnType` MUST be `Any` (editors are statements, not expressions) and tooling MUST reject any expression-position use per §4.4.

### 10.6 Validation

A conformant registry document MUST satisfy:

1. Every `name` unique within the registry.
2. `kind` matches `name` casing (§4.1).
3. `target: true` appears on at most one parameter, only when `kind = "editor"`, and that parameter's type is `Setter<...>`.
4. Variadic parameter, if present, is last and positional.
5. All types parse under §10.3.

### 10.7 Versioning

The schema (§10) versions independently of any registry document. A registry document declares the schema version it conforms to and the `ottlSpecVersion` (§8) it targets. Upstream `ottlfuncs` is one such registry; processor-specific registries (transform, filter, routing) MAY extend it.

---

## Appendix A — Cross-reference to reference implementation

All symbols below live in [`pkg/ottl/grammar.go`][upstream-grammar] in
[`open-telemetry/opentelemetry-collector-contrib`][upstream-repo].

| This spec        | `spec/grammar.go`                                              |
| ---------------- | -------------------------------------------------------------- |
| §3.1 `statement` | `parsedStatement`                                              |
| §3.2 `editor`    | `editor`                                                       |
| §3.2 `converter` | `converter`                                                    |
| §3.2 `argument`  | `argument`                                                     |
| §3.3 `value`     | `value`                                                        |
| §3.4 `path`      | `path`, `field`, `key`                                         |
| §3.5 math        | `mathExpression`, `addSubTerm`, `mathValue`, `mathExprLiteral` |
| §3.6 boolean     | `booleanExpression`, `term`, `booleanValue`, `comparison`      |
| §4.1, §4.4, §4.5 | `grammarCustomErrorsVisitor`                                   |
| §2 lexer         | `buildLexer()`                                                 |

[upstream-repo]: https://github.com/open-telemetry/opentelemetry-collector-contrib
[upstream-pkg]: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/pkg/ottl
[upstream-grammar]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/grammar.go
[upstream-langmd]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/LANGUAGE.md
