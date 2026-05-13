/**
 * OpenTelemetry Transformation Language — Tree-sitter grammar
 *
 * Implements ../SPEC.md §3 (syntactic). Semantic constraints (§4) are
 * surfaced as parse-time choices where possible, otherwise left to the
 * host (LSP, formatter).
 *
 * Generation:
 *   npx tree-sitter generate
 *   npx tree-sitter test
 */

module.exports = grammar({
  name: "ottl",

  extras: ($) => [/\s/, $.line_comment, $.block_comment],

  word: ($) => $.lower_id,

  // SPEC §5 — operator precedence (lowest to highest)
  precedences: () => [["or", "and", "not", "comparison", "additive", "multiplicative"]],

  // GLR conflicts: a converter can appear both as a boolean atom (returning
  // bool) and as a math atom (returning numeric). The host's function
  // registry resolves which.
  conflicts: ($) => [
    [$._boolean_atom, $._math_atom],
    [$.boolean_expr, $.math_expression],
    [$._key_value, $._math_atom],
    [$._key_value, $.math_expression],
  ],

  rules: {
    // Entry point: a file is a `;`-separated list of statements (§6.1).
    source_file: ($) => seq(repeat(seq($.statement, ";")), optional($.statement)),

    // SPEC §3.1
    statement: ($) => seq($.editor, optional($.where_clause)),
    where_clause: ($) => seq("where", $.boolean_expr),

    // SPEC §3.2
    editor: ($) => seq(field("name", $.lower_id), "(", optional($.arguments), ")"),
    converter: ($) =>
      seq(field("name", $.upper_id), "(", optional($.arguments), ")", optional($.keys)),

    arguments: ($) => seq($.argument, repeat(seq(",", $.argument))),
    // A bare UPPER_ID argument (e.g. `aggregate(metrics, Sum)`) is parsed as
    // an `enum_value` and reinterpreted by the host as a function reference
    // when the function's parameter type demands one (SPEC §3.2).
    argument: ($) => seq(optional(seq(field("name", $.lower_id), "=")), $._value),

    // SPEC §3.3 — `_value` is hidden; expose specific kinds in the AST.
    _value: ($) =>
      choice(
        $.nil,
        $.math_expression,
        $.bytes,
        $.string,
        $.boolean,
        $.enum_value,
        $.map_value,
        $.list_value,
      ),

    nil: () => "nil",
    boolean: () => choice("true", "false"),
    enum_value: ($) => $.upper_id,

    list_value: ($) => seq("[", optional(seq($._value, repeat(seq(",", $._value)))), "]"),
    map_value: ($) =>
      seq("{", optional(seq($.map_item, repeat(seq(",", $.map_item)), optional(","))), "}"),
    map_item: ($) => seq(field("key", $.string), ":", field("value", $._value)),

    // SPEC §3.4 — the first segment is interpreted by the host as a context
    // identifier when there is more than one segment.
    path: ($) => prec.left(seq($.field, repeat(seq(".", $.field)))),
    field: ($) => seq($.lower_id, optional($.keys)),
    keys: ($) => repeat1($.key),
    key: ($) => seq("[", $._key_value, "]"),
    _key_value: ($) => choice($.string, $.int, $.math_expression),

    // SPEC §3.5
    math_expression: ($) =>
      choice(
        $._math_atom,
        prec.left("additive", seq($.math_expression, choice("+", "-"), $.math_expression)),
        prec.left("multiplicative", seq($.math_expression, choice("*", "/"), $.math_expression)),
      ),
    _math_atom: ($) =>
      choice($.editor, $.converter, $.float, $.int, $.path, seq("(", $.math_expression, ")")),

    // SPEC §3.6
    boolean_expr: ($) =>
      choice(
        $._boolean_atom,
        prec.left("or", seq($.boolean_expr, "or", $.boolean_expr)),
        prec.left("and", seq($.boolean_expr, "and", $.boolean_expr)),
        prec("not", seq("not", $.boolean_expr)),
      ),
    _boolean_atom: ($) =>
      choice($.comparison, $.boolean, $.converter, seq("(", $.boolean_expr, ")")),
    comparison: ($) =>
      prec.left("comparison", seq($._value, field("op", $.comparison_op), $._value)),
    comparison_op: () => choice("==", "!=", "<=", ">=", "<", ">"),

    // SPEC §2 — terminals
    string: () => /"(\\.|[^\\"])*"/,
    bytes: () => /0x[0-9a-fA-F]+/,
    float: () => /[+-]?\d*\.\d+([eE][+-]?\d+)?/,
    int: () => /[+-]?\d+/,
    upper_id: () => /[A-Z][a-zA-Z0-9_]*/,
    lower_id: () => /[a-z][a-zA-Z0-9_]*/,

    // SPEC §6.2 (extension) — hosts may strip these before passing to upstream.
    line_comment: () => token(seq("//", /[^\r\n]*/)),
    block_comment: () => token(seq("/*", /[^*]*\*+([^/*][^*]*\*+)*/, "/")),
  },
});
