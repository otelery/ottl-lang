# OpenTelemetry Transformation Language — Specification

**Status:** Draft 0.2
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

The following words are reserved and MUST NOT be used as editor, converter, path, or argument names:

```
NOT        ::= 'not'
AND        ::= 'and'
OR         ::= 'or'
NIL        ::= 'nil'
TRUE       ::= 'true'
FALSE      ::= 'false'
```

`true` and `false` together form the `BOOLEAN` token.

A keyword is recognized only as a whole word: `not`, `nil`, … followed by a letter, digit or `_` is not a keyword (`nilx` is a lowercase run, and `andTest` is the lowercase run `and` followed by the uppercase run `Test`, see §2.5).

`where` is **not** reserved. It is an ordinary lowercase run (`where.x` is a valid path, `where(…)` a valid editor name) and is recognized as the where-clause introducer only directly after an editor call (§3.2).

### 2.3 Literals

```
BOOLEAN    ::= 'true' | 'false'
BYTES      ::= '0x' ([a-fA-F0-9] [a-fA-F0-9])+       /* even number of hex digits */
FLOAT      ::= ( [0-9]+ '.' [0-9]* | [0-9]* '.' [0-9]+ ) ([eE] [+-]? [0-9]+)?
INT        ::= [0-9]+
STRING     ::= '"' ( ESCAPE | [^\\"] )* '"'
ESCAPE     ::= '\\' ( [abfnrtv\\"]
                    | 'x' HEX HEX
                    | [0-3] [0-7] [0-7]
                    | 'u' HEX{4}                    /* not a surrogate, D800–DFFF */
                    | 'U' HEX{8} )                  /* a valid code point */
```

Numeric tokens are **unsigned**: a leading `+` or `-` is the unary operator of §3.5, never part of the token. `3.` and `.5` are valid `FLOAT`s; `3e5` is not (an `INT` followed by an identifier).

Lexer precedence (longest-match, then declaration order): `BYTES` before `INT` (the `0x` prefix), `FLOAT` before `INT` (the decimal point), keywords before identifiers. `0xabc` (odd digit count) is a lexical error.

String escapes are Go's interpreted-string escapes. An unknown escape such as `\q` or `\'` is an error, as is `\0` (octal escapes take exactly three digits). A raw newline inside a string is accepted.

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
ARROW      ::= '=>'                   /* lambda expressions, §3.7 */
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

Multi-character operators MUST be matched before their single-character prefixes (e.g. `==` before `=`, `<=` before `<`, `=>` before `=`).

### 2.5 Identifiers

The reference implementation tokenizes **runs**: a lowercase run starts with `[a-z]`, an uppercase run with `[A-Z]`, and each continues over `[a-z0-9_]` / `[A-Z0-9_]` respectively. A change of letter case starts a new run. Whitespace between tokens is skipped.

```
LOWER_RUN  ::= [a-z] [a-z0-9_]*
UPPER_RUN  ::= [A-Z] [A-Z0-9_]*
```

The grammar then builds the names it needs from runs:

```
lowerName  ::= LOWER_RUN (LOWER_RUN | UPPER_RUN)*     /* editors, argument names */
upperName  ::= UPPER_RUN (LOWER_RUN | UPPER_RUN)*     /* converters, function references */
fieldName  ::= LOWER_RUN                              /* path fields and contexts, lambda parameters */
enumName   ::= UPPER_RUN                              /* not followed by a LOWER_RUN, see §4.2 */
```

Consequences that differ from a naive "identifier" token:

- A path field, context, lambda parameter or enum is a **single run**. `aB.x`, `a.bC` and `x == Foo` are syntax errors; `a_b`, `attributes` and `SPAN_KIND_SERVER` are fine. Only editor, converter and argument names may mix cases (`headerDelimiter`, `ParseJSON`).
- Because runs are joined _after_ whitespace is skipped, whitespace between runs inside a name is accepted: `S plit(…)` is `Split(…)`, and `resource resolveConflicts=true` names the argument `resourceresolveConflicts`. This is a reference-implementation quirk; conformant parsers are not required to reproduce it (the differential test classifies it as expected), and new code SHOULD NOT rely on it.

Examples:

| Token              | Class       | Used as                               |
| ------------------ | ----------- | ------------------------------------- |
| `set`              | `lowerName` | editor name                           |
| `attributes`       | `fieldName` | path field                            |
| `headerDelimiter`  | `lowerName` | named argument (not a path field)     |
| `ParseJSON`        | `upperName` | converter name (not an enum)          |
| `SPAN_KIND_SERVER` | `enumName`  | enum symbol (or a converter with `(`) |

> **Note (semantic, not lexical):** the _casing convention_ is enforced after parsing — see §4.1.

A standalone underscore is tokenized separately:

```
UNDERSCORE ::= '_'                    /* blank lambda parameter, §3.7 */
```

`_` inside a longer run (e.g. `my_field`) is absorbed into that run; `UNDERSCORE` only matches a bare `_` that is not adjacent to another identifier character.

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

editor     ::= lowerName LPAREN arguments? RPAREN
converter  ::= upperName LPAREN arguments? RPAREN keys?

arguments  ::= argument (COMMA argument)*
argument   ::= (lowerName EQUAL)? value
             | (lowerName EQUAL)? upperName  /* bare converter name as argument */
```

The bare-`upperName` alternative in `argument` (a mixed-case name such as `Sum`; an all-caps run parses as an enum value) allows passing a function reference by name (e.g. `aggregate(metrics, Sum)`); see the reference implementation's `argument.FunctionName` field.

### 3.3 Values

```
value      ::= NIL
             | lambda                         /* function-argument position only, §3.7 */
             | mathExprLiteral                /* literal not followed by + - * / */
             | mathExpression
             | BYTES
             | STRING
             | BOOLEAN
             | enumValue
             | mapValue
             | listValue

enumValue  ::= enumName                       /* not followed by '(' — see §4.2 */
listValue  ::= LBRACKET (value (COMMA value)*)? RBRACKET
mapValue   ::= LBRACE (mapItem COMMA?)* RBRACE   /* the comma after each item is optional */
mapItem    ::= STRING COLON value
```

### 3.4 Paths and keys

```
path       ::= (fieldName DOT)? field (DOT field)*
field      ::= fieldName keys?
keys       ::= key+
key        ::= LBRACKET keyValue RBRACKET
keyValue   ::= STRING                         /* map key */
             | INT                            /* slice index */
             | mathExpression                 /* dynamic key */
             | mathExprLiteral                /* simple expression */
```

> **Quirk:** the reference implementation tries `INT` before `mathExpression` in a key and does not backtrack, so a key that _starts_ with an integer literal must consist of that literal alone: `x[1]` is valid but `x[1+1]` and `x[2*y]` are syntax errors, while `x[(1)+1]`, `x[y+1]` and `x[-1]` are valid. Conformant parsers MAY accept the former.

The first segment of a `path` (when present) is interpreted by the host as a _context_ identifier (`resource`, `span`, `metric`, `log`, `datapoint`, `instrumentation_scope`, …). The grammar does not enforce this — see §4.3.

### 3.5 Math expressions

Precedence (lowest to highest): additive < multiplicative < parenthesized.

```
mathExpression ::= addSubTerm ((PLUS | MINUS) addSubTerm)*
addSubTerm     ::= mathValue ((MULT | DIV) mathValue)*
mathValue      ::= (PLUS | MINUS)? ( mathExprLiteral
                                   | LPAREN mathExpression RPAREN )   /* at most one unary sign */
mathExprLiteral::= editor                     /* SYNTACTIC ONLY — rejected, see §4.4 */
                 | converter
                 | FLOAT
                 | INT
                 | path
```

### 3.6 Boolean expressions

Precedence (lowest to highest): `or` < `and` < `not` < parenthesized / atom. `not` applies to a single `booleanValue`; `not not x` is a syntax error.

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

### 3.7 Lambda expressions (experimental)

> **Status: experimental.** Upstream ships lambdas as `alpha`, behind the `ottl.functions.enableLambda` feature gate (disabled by default), and the lambda API and all functions that accept lambdas live in the experimental `xottl` module. They are **not** covered by OTTL's stability guarantee (traces, metrics and logs signals promoted to stable in [#51236](https://github.com/open-telemetry/opentelemetry-collector-contrib/pull/51236)). The syntax below may change or be removed without a major spec version. A conformant parser SHOULD accept it; a host that does not enable lambdas MUST reject it (§4.9).

```
lambda      ::= LPAREN (lambdaParam (COMMA lambdaParam)*)? RPAREN ARROW lambdaBody
lambdaParam ::= fieldName | UNDERSCORE
lambdaBody  ::= value
              | booleanExpr
```

A lambda expression is inline logic passed to a higher-order function (e.g. `Filter`,
`MapEach`, `When` — see [`functions/ottlfuncs-lambda.yaml`](./functions/ottlfuncs-lambda.yaml)
for the catalog). Syntactically a lambda is a `value`, so the grammar admits it wherever a
value is allowed. It is only meaningful as an argument of a function whose parameter has
type `Lambda` (§10.3); the host rejects it anywhere else. It is never a statement or a
bare top-level expression.

`lambdaParam` names introduce local identifiers scoped to `lambdaBody`; `_` marks a
parameter whose value is unused. The number and role of parameters (e.g. "index-or-key,
then value") is defined per function by the host's function registry (§10), not by the
grammar — the grammar only constrains parameters to a comma-separated list of single lowercase runs (`fieldName`)
or `_`.

`lambdaBody` tries `value` before `booleanExpr`, so a body like `v * 2` parses as a math
value while a body like `v == "prod"` or `a and b` falls back to a boolean expression.

Upstream commits to a body greedily: a value body that is followed by `or`, `and` or a comparison operator becomes a boolean expression instead. So a lambda used as an operand of a comparison or boolean operator — `(x) => x == 1` as a whole condition, or `a < (x) => x or y` — is a syntax error upstream. `OTTL.g4` and the Tree-sitter grammar parse such inputs by ending the body early; hosts reject them anyway, because a lambda is only valid where a `Lambda`-typed parameter is declared. The differential test (§7) tolerates these.

Examples:

```
(key, value) => HasPrefix(key, "http.")
(_, v) => v * 2
() => IsMap(log.attributes)
```

See §4 for semantic constraints (nested lambdas, the feature-gate requirement).

---

## 4. Semantic constraints

These rules cannot be expressed in pure EBNF. Implementations MUST enforce them after parsing (or via parser predicates) and produce diagnostic errors with source positions.

### 4.1 Identifier casing

| Construct     | First character | Name rule   | Enforced by                  |
| ------------- | --------------- | ----------- | ---------------------------- |
| Editor        | lowercase       | `lowerName` | grammar (rule `editor`)      |
| Converter     | uppercase       | `upperName` | grammar (rule `converter`)   |
| Enum          | uppercase       | `enumName`  | grammar (`enumValue`) + §4.2 |
| Path field    | lowercase       | `fieldName` | grammar (rule `field`)       |
| Argument name | lowercase       | `lowerName` | grammar (rule `argument`)    |

If a parser encounters `upperName '(' ... ')'` where `editor` is expected, it MUST emit:

> `editor names must start with a lowercase letter but got '<Name>'`

If a parser encounters `lowerName '(' ... ')'` inside a `mathExprLiteral` (where a converter is expected), it MUST emit:

> `converter names must start with an uppercase letter but got '<name>'`

### 4.2 Enum vs. converter disambiguation

An `UPPER_RUN` is a `converter` name if followed by `LPAREN`, otherwise an `enumValue` — and only when the next token is not a `LOWER_RUN` (`Foo` is not an enum; `FOO` is). Implementations SHOULD use one-token lookahead. ANTLR4 adaptive prediction handles this without explicit predicates; PEG/Tree-sitter implementations should encode the lookahead.

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

### 4.9 Lambda constraints

- A lambda `lambdaBody` MUST NOT itself be a `lambda` (e.g. `(x) => (y) => x + y` is
  grammatically accepted but MUST be rejected post-parse with
  `lambda body cannot result into another lambda expression`). A body that evaluates to a
  lambda does not retain the outer lambda's parameter bindings. A lambda nested _inside_ a
  body, for example as an argument of a function call, is allowed and may read the outer
  parameters: `(_, a) => Any(xs, (_, b) => a == b)`.
- Parameter names other than `_` MUST be unique within one lambda; `_` may repeat.
- A conformant host MUST reject any statement or condition containing a `lambda` value
  unless the host's lambda-functions feature is enabled (upstream: the
  `ottl.functions.enableLambda` feature gate). The grammar always accepts the syntax;
  gating is enforced by the host, not the parser.
- Parameter arity and role (e.g. "index-or-key, then value" for `Filter`) are validated
  per function by the host against its function registry (§10); the grammar only
  constrains the parameter list shape (§3.7).
- `lambdaParam` names are scoped to `lambdaBody`. An inner parameter shadows an outer lambda
  parameter, and a parameter shadows a path context or field of the same name, for the
  duration of the lambda.

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

A `lambda` (`(params) => body`) is not itself an operator in this table — it is a value
production (§3.7) delimited by its own parentheses and `=>`. Its `lambdaBody` is a full
`value`/`booleanExpr`, so operator precedence inside the body follows this same table.

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

1. Accepts every input in the valid suites under `tests/conformance/` (`valid_*.ottl`, `lexical_valid_*.ottl`, `upstream_valid_*.ottl`).
2. Rejects every input in the invalid suites (`lexical_invalid_*.ottl`, `lambda_invalid_*.ottl`, `upstream_invalid_*.ottl`).
3. Produces the diagnostic messages specified in §4 with byte-accurate source positions.
4. Round-trips an AST → text formatter such that re-parsing yields a structurally equal AST (whitespace insensitive).

A _strictly_ conformant implementation additionally reproduces the reference lexer's run-gluing behaviour for names (§2.5).

The reference implementation is the oracle: [`tests/differential`](./tests/differential/README.md) runs the upstream parser, `OTTL.g4` and the Tree-sitter grammar over the conformance corpus, hand-written edge cases, mutations and random derivations from §3, and reports every disagreement. The divergences it tolerates are listed there and in §2.5, §3.4, §4 and §6.

---

## 8. Versioning

This document is versioned independently of the upstream collector. Version increments:

- **Patch** — clarifications, typo fixes, no grammar change.
- **Minor** — additions that all prior conformant inputs continue to parse identically (e.g. adding §6 file grammar).
- **Major** — any change that could reject a previously accepted input.

| Version | Date       | Notes                                                                                                                                                                                                                                                                                                                                                                                             |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0.1     | 2026-05-10 | Initial draft from `OTTL.g4` and [`spec/grammar.go`][upstream-grammar].                                                                                                                                                                                                                                                                                                                           |
| 0.2     | 2026-10-25 | Add experimental lambda expressions (§2.5, §3.7, §4.9, `Lambda` type). Correct §2–§3 to match the reference implementation as verified by differential testing: unsigned numeric tokens with a unary operator, `3.`, even-length bytes, Go string escapes, run-based identifiers (single-run fields and enums), `where` not reserved, keyword word boundaries, optional map commas, single `not`. |

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

- `kind ∈ { "editor", "converter" }`. MUST agree with the casing of `name` per §4.1 (`editor` → `lowerName`, `converter` → `upperName`).
- `name` MUST be a valid `lowerName` or `upperName` per §2.5.
- `sourceRef` is a commit hash / tag of the upstream this registry was generated from, when applicable.

### 10.2 Parameter descriptors

Each parameter has a `name` (valid `lowerName`, §2.5), a `type` (§10.3), and flags:

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
              | 'FunctionRef'                     /* bare upperName argument, §3.2 */
              | 'Lambda'                           /* lambda expression argument, §3.7 */

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
| `*ottl.LambdaExpression[K]`                    | `Lambda`                                      |

`Like` variants are not a separate type; they are a runtime coercion flag (§10.4) on a `Getter<...>`.

`Lambda` is opaque at the type-language level — it does not encode parameter arity, parameter
roles, or the lambda's return type. Those are function-specific constraints documented in the
registry entry's `description` (see `functions/SCHEMA.md`), mirroring how the reference
implementation's `*ottl.LambdaExpression[K]` carries no static arity either. An optional lambda
parameter (e.g. `Find`'s `mapper`) is `Optional<Lambda>`.

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
