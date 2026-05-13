# OTTL Internal Architecture & Execution Flow

This document serves as a roadmap for Go developers contributing to the OpenTelemetry Transformation Language (OTTL). It assumes a basic understanding of compiler theory (specifically Abstract Syntax Trees) and focuses on how OTTL implements its execution pipeline across the codebase.

All file references below are relative to [`pkg/ottl`][upstream-pkg] in
[`open-telemetry/opentelemetry-collector-contrib`][upstream-repo].

The OTTL lifecycle is divided into three distinct phases:

1. **Lexing** (Tokenizing the user's configuration string)

2. **Parsing & AST** (Building the execution tree)

3. **Execution & Evaluation** (Applying the tree to telemetry data)

---

## 1: Lexing

Before OTTL can parse a statement, the raw string (e.g., `set(attributes["foo"], "bar")`) must be broken down into recognizable tokens. OTTL relies on the [`alecthomas/participle/v2/lexer`](https://github.com/alecthomas/participle) library for this phase.

**Where to look:**

- [`pkg/ottl/grammar.go`][upstream-grammar]: Contains the struct tags and regex definitions that dictate the basic token vocabulary of OTTL.
- [`pkg/ottl/lexer_test.go`][upstream-lexer-test]: Contains the validation tests for the underlying Participle lexer.

## 2: Parsing & The AST

Once tokenized, the stream is converted into an Abstract Syntax Tree (AST). This phase enforces the grammar rules of the language.

**Where to look:**

- [`pkg/ottl/grammar.go`][upstream-grammar]: Defines the Go structs that represent the hierarchy of the AST.
- [`pkg/ottl/parser.go`][upstream-parser]: Contains the parser initialization and the core parsing functions (e.g., `ParseStatements`).

**Key Data Structures:**

- `parsedStatement`: The root of the tree. It dictates that a statement generally consists of an action (an `Editor` or function) and an optional condition (`WhereClause`).
- `Editor` / `Converter`: These structs represent the actual function calls (e.g., `set`, `replace_all`) and their parsed arguments.
- `Path`: Represents the dot-notation paths users write to target telemetry fields (e.g., `resource.attributes["host.name"]`).

## 3: Execution & Evaluation

There is no single "Evaluator" engine in OTTL. Instead, execution triggers recursively across the AST nodes.

**Where to look:**

- [`pkg/ottl/parser.go`][upstream-parser]: Contains the `Execute()` methods attached to the `Statement` structs, which orchestrate the evaluation of the `WhereClause` and the execution of the main function.
- [`pkg/ottl/contexts/ottllog/log.go`][upstream-ottllog]: Contains the implementation of the log-specific `TransformContext`.
- [`pkg/ottl/contexts/internal/ctxlog/log.go`][upstream-ctxlog]: Contains the signal-specific path resolution logic.

**Key Concepts:**

- **The `TransformContext`:** To evaluate a statement, the engine needs state. The `TransformContext` interface wraps the actual OpenTelemetry payload (e.g., a `plog.LogRecord` or `pmetric.Metric`) being processed at that exact microsecond.
- **Dynamic Resolution (`PathGetSetter`):** When the AST requests a value like `attributes["foo"]`, OTTL uses the `PathGetSetter` interface to dynamically route that string request to the Go getter/setter for that specific telemetry signal.

---

[upstream-repo]: https://github.com/open-telemetry/opentelemetry-collector-contrib
[upstream-pkg]: https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/pkg/ottl
[upstream-grammar]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/grammar.go
[upstream-parser]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/parser.go
[upstream-lexer-test]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/lexer_test.go
[upstream-ottllog]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/contexts/ottllog/log.go
[upstream-ctxlog]: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/contexts/internal/ctxlog/log.go
