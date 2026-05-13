# OTTL Function Registry — Schema

Normative companion to [`SPEC.md` §10](../SPEC.md#10-function-signature-schema). This document defines the on-disk shape of a function-registry document and shows worked examples.

A **registry** describes the editors and converters a particular host (a processor, a connector, or the base `ottlfuncs` library) makes available. Tooling (LSP completion, hover, signature help) loads one or more registries and merges them.

## File format

YAML (canonical) or JSON. UTF-8. One registry per file.

### Top level

```yaml
schemaVersion: "1" # version of this schema (§10)
name: ottlfuncs # registry id (kebab- or snake_case)
version: "0.0.0+commit.abcd1234" # version of the registry itself
ottlSpecVersion: "0.1" # SPEC.md version it targets (§8)
sourceRef: # optional provenance
  repo: github.com/open-telemetry/opentelemetry-collector-contrib
  path: pkg/ottl/ottlfuncs
  commit: <40-hex>
extends: [] # optional list of registry ids this overlays
notes: | # optional human-readable summary
  Free-text caveats about scope / subset rules.
restrictsBase:
  false # optional — true if this registry restricts the
  # base instead of (or in addition to) extending it.
exposedFromBase: # optional — when restrictsBase=true, lists what
  # is exposed from the base. Tooling treats every
  # base entry NOT listed as unavailable.
  converters: <group-name> | [<name>, ...]
  editors: [<name>, ...]
  spanContextExtras: [<name>, ...] # context-conditional exposures
functions: [...] # entries added by this registry (always)
```

### Function entry

```yaml
- name: append # LOWER_ID or UPPER_ID per SPEC §2.5
  kind: editor # "editor" | "converter"
  parameters: [...]
  returnType: Any # SPEC §10.3 type expression
  description: |
    Appends single or multiple values to target.
  examples:
    - 'append(attributes["tags"], value="prod")'
  since: "v0.95.0" # optional — upstream tag where added
  deprecated: false # optional
  contexts: # optional — host contexts (per SPEC §3.4 path
    # context) in which this function is registered.
    # Absence means "all contexts the registry covers".
    - metric
    - span
```

### Parameter descriptor

```yaml
- name: target # LOWER_ID per SPEC §2.5
  type: Setter<Any> # SPEC §10.3
  target: true # editor lvalue marker; ≤1 per entry
  optional: false
  variadic: false
  coerce: false # §10.4 — true for *LikeGetter inputs
  description: |
    The field to append to.
```

## Worked example — `append` (editor)

Upstream source:

```go
type AppendArguments[K any] struct {
    Target ottl.GetSetter[K]
    Value  ottl.Optional[ottl.Getter[K]]
    Values ottl.Optional[[]ottl.Getter[K]]
}
NewFactory("append", &AppendArguments[K]{}, ...)
```

Registry entry:

```yaml
- name: append
  kind: editor
  returnType: Any
  parameters:
    - name: target
      type: Setter<Any>
      target: true
    - name: value
      type: Optional<Getter<Any>>
      optional: true
    - name: values
      type: Optional<List<Getter<Any>>>
      optional: true
  description: |
    Appends scalar or list values to target. At least one of `value` or
    `values` must be supplied.
  examples:
    - 'append(attributes["tags"], value="prod")'
    - 'append(attributes["tags"], values=["a", "b"])'
```

## Worked example — `Concat` (converter)

Upstream source:

```go
type ConcatArguments[K any] struct {
    Vals      []ottl.StringLikeGetter[K]
    Delimiter ottl.StringGetter[K]
}
NewFactory("Concat", &ConcatArguments[K]{}, ...)
```

Registry entry:

```yaml
- name: Concat
  kind: converter
  returnType: String
  parameters:
    - name: vals
      type: List<Getter<String>>
      variadic: false # consumed as a list literal, not varargs
      coerce: true # StringLikeGetter
    - name: delimiter
      type: Getter<String>
  examples:
    - 'Concat([attributes["a"], attributes["b"]], "-")'
```

## Overlay / extension registries

Processor-specific registries declare `extends: [ottlfuncs]` and list only the functions they add (or override). Tooling resolves a flat function table by left-to-right merge, last-write-wins per `name`. See:

- [`ottlfuncs.yaml`](./ottlfuncs.yaml) — base catalog (to be extracted)
- [`transformprocessor.yaml`](./transformprocessor.yaml) — adds 14 metric editors/converters + 1 trace editor
- [`filterprocessor.yaml`](./filterprocessor.yaml) — adds `HasAttrOnDatapoint`, `HasAttrKeyOnDatapoint`; only converters
- [`routingconnector.yaml`](./routingconnector.yaml) — restricts the base to standard converters + `delete_key`/`delete_matching_keys`, adds `route`

## Mapping cheatsheet (Go → §10.3)

| Go declaration                                     | §10.3 form                                            |
| -------------------------------------------------- | ----------------------------------------------------- |
| `ottl.GetSetter[K]` _(target field)_               | `Setter<Any>` + `target: true`                        |
| `ottl.Getter[K]`                                   | `Getter<Any>`                                         |
| `ottl.StringGetter[K]`                             | `Getter<String>`                                      |
| `ottl.StringLikeGetter[K]`                         | `Getter<String>` + `coerce: true`                     |
| `ottl.IntGetter[K]` / `IntLikeGetter`              | `Getter<Int>` (+ coerce)                              |
| `ottl.FloatGetter[K]` / `FloatLikeGetter`          | `Getter<Float>` (+ coerce)                            |
| `ottl.BoolGetter[K]`                               | `Getter<Bool>`                                        |
| `ottl.ByteSliceLikeGetter[K]`                      | `Getter<Bytes>` + `coerce: true`                      |
| `ottl.PMapGetter[K]`                               | `Getter<PMap>`                                        |
| `ottl.PSliceGetter[K]`                             | `Getter<PSlice>`                                      |
| `ottl.TimeGetter[K]`                               | `Getter<Time>`                                        |
| `ottl.DurationGetter[K]`                           | `Getter<Duration>`                                    |
| `ottl.FunctionGetter[K]`                           | `FunctionRef`                                         |
| `ottl.Optional[T]`                                 | `Optional<T'>`                                        |
| `[]T` _(field type)_                               | `List<T'>` _(or `variadic: true` if positional tail)_ |
| `string` / `int64` / `float64` / `bool` / `[]byte` | `String` / `Int` / `Float` / `Bool` / `Bytes`         |

## Extraction

The intended source of truth for the upstream catalog is the Go AST of `pkg/ottlfuncs/func_*.go`. A future `functions/extract.go` walks each file, locates `<Name>Arguments[K]` structs and `NewFactory(...)` calls, applies the table above, and emits `ottlfuncs.yaml`. Hand-edited overlays (this directory) cover processor-specific additions.
