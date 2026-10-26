/**
 * OpenTelemetry Transformation Language — Tree-sitter grammar
 *
 * Implements ../SPEC.md §3 (syntactic). Semantic constraints (§4) are
 * surfaced as parse-time choices where possible, otherwise left to the
 * host (LSP, formatter).
 *
 * Lexical model (SPEC §2.5): like upstream, identifiers are lowercase and
 * uppercase *runs*. Editor, converter and argument names glue runs together
 * (whitespace between runs is skipped); path fields, path contexts, lambda
 * parameters and enums are a single run.
 *
 * Generation:
 *   npx tree-sitter generate
 *   npx tree-sitter test
 */

const HEX = "[0-9a-fA-F]";

// Upstream lexes `not`, `and`, `or`, `nil`, `true` and `false` as keyword tokens
// (with `\b` boundaries), so a lowercase run equal to one of them is never an
// identifier. Tree-sitter regexes have no lookahead, so build "[a-z][a-z0-9_]*
// except these exact words" as an explicit prefix-tree regex.
const KEYWORDS = ["not", "and", "or", "nil", "true", "false"];
const RUN_CHARS = "abcdefghijklmnopqrstuvwxyz0123456789_".split("");
function runExcept(words) {
  const trie = {};
  for (const w of words) {
    let n = trie;
    for (const c of w) n = n[c] = n[c] || {};
    n.$ = true;
  }
  const node = (n, root) => {
    const kids = Object.keys(n).filter((k) => k !== "$");
    const first = root ? RUN_CHARS.slice(0, 26) : RUN_CHARS;
    const others = first.filter((c) => !kids.includes(c)).join("");
    const alts = [];
    if (!root && !n.$) alts.push("");
    if (others) alts.push(`[${others}][a-z0-9_]*`);
    for (const k of kids) alts.push(`${k}${node(n[k], false)}`);
    return `(${alts.join("|")})`;
  };
  return new RegExp(node(trie, true));
}

module.exports = grammar({
  name: "ottl",

  extras: ($) => [/\s/, $.line_comment, $.block_comment],

  word: ($) => $.lower_run,

  // SPEC §5 — operator precedence (lowest to highest)
  precedences: () => [["or", "and", "comparison", "additive", "multiplicative"]],

  // GLR conflicts: a converter can appear both as a boolean atom (returning
  // bool) and as a math atom (returning numeric). The host's function
  // registry resolves which. `lambda_body` (SPEC §3.7) is likewise ambiguous
  // between `_value` and `boolean_expr` until enough of the body is seen.
  conflicts: ($) => [
    [$._boolean_atom, $._math_atom],
    [$._key_value, $._math_atom],
    [$._value, $._boolean_atom],
    [$.lambda_body, $.comparison],
    [$.lambda_body, $.boolean_expr],
    // `(v)` is ambiguous between a lambda's single-parameter list and a
    // parenthesized math expression until `=>` (or its absence) is seen.
    [$.lambda_param, $.field],
    // `Foo` as an enum value vs the start of a glued converter / function name.
    [$.enum_value, $.upper_name],
    [$.function_ref],
  ],

  rules: {
    // Entry point: a file is a `;`-separated list of statements (§6.1).
    source_file: ($) => seq(repeat(seq($.statement, ";")), optional($.statement)),

    // SPEC §3.1
    statement: ($) => seq($.editor, optional($.where_clause)),
    where_clause: ($) => seq("where", $.boolean_expr),

    // SPEC §3.2
    editor: ($) => seq(field("name", $.lower_name), "(", optional($.arguments), ")"),
    converter: ($) =>
      seq(field("name", $.upper_name), "(", optional($.arguments), ")", optional($.keys)),

    arguments: ($) => seq($.argument, repeat(seq(",", $.argument))),
    // A bare upper-case name argument (e.g. `aggregate(metrics, Sum)`) is an
    // `enum_value`, or a `function_ref` when it is a mixed-case name; the host
    // reinterprets either as a function reference when the parameter type
    // demands one (SPEC §3.2).
    argument: ($) =>
      seq(
        optional(seq(field("name", $.lower_name), "=")),
        choice($._value, $.function_ref),
      ),
    // Upstream tries `value` first and does not backtrack: a reference needs a
    // lowercase run after the first uppercase run (otherwise it is an enum).
    function_ref: ($) =>
      seq(
        $.upper_run,
        choice($.lower_run, "where"),
        repeat(choice($.lower_run, $.upper_run, "where")),
      ),

    // SPEC §3.3 — `_value` is hidden; expose specific kinds in the AST.
    _value: ($) =>
      choice(
        $.nil,
        $.lambda_expr,
        $.math_expression,
        $.bytes,
        $.string,
        $.boolean,
        $.enum_value,
        $.map_value,
        $.list_value,
      ),

    // SPEC §3.7 — experimental (alpha upstream). `(` is shared with parenthesized
    // math; the `=>` after `)` disambiguates.
    lambda_expr: ($) =>
      seq(
        "(",
        optional(seq($.lambda_param, repeat(seq(",", $.lambda_param)))),
        ")",
        "=>",
        $.lambda_body,
      ),
    lambda_param: ($) => choice($._field_name, $.blank),
    lambda_body: ($) => choice($._value, $.boolean_expr),
    blank: () => "_",

    nil: () => "nil",
    boolean: () => choice("true", "false"),
    // An all-caps run; a mixed-case name is only valid as a call or function_ref.
    enum_value: ($) => $.upper_run,

    list_value: ($) => seq("[", optional(seq($._value, repeat(seq(",", $._value)))), "]"),
    // Upstream: `'{' (@@ ','?)* '}'` — the comma after each item is optional.
    map_value: ($) => seq("{", repeat(seq($.map_item, optional(","))), "}"),
    map_item: ($) => seq(field("key", $.string), ":", field("value", $._value)),

    // SPEC §3.4 — the first segment is interpreted by the host as a context
    // identifier when there is more than one segment.
    path: ($) => prec.left(seq($.field, repeat(seq(".", $.field)))),
    field: ($) => seq($._field_name, optional($.keys)),
    _field_name: ($) => choice($.lower_run, "where"),
    keys: ($) => repeat1($.key),
    key: ($) => seq("[", $._key_value, "]"),
    _key_value: ($) => choice($.string, $.int, $.math_expression),

    // SPEC §3.5 — a single optional unary sign per operand.
    math_expression: ($) =>
      choice(
        $._math_operand,
        prec.left("additive", seq($.math_expression, choice("+", "-"), $.math_expression)),
        prec.left("multiplicative", seq($.math_expression, choice("*", "/"), $.math_expression)),
      ),
    _math_operand: ($) => choice($._math_atom, $.unary_expression),
    unary_expression: ($) => seq(choice("+", "-"), $._math_atom),
    _math_atom: ($) =>
      choice($.editor, $.converter, $.float, $.int, $.path, seq("(", $.math_expression, ")")),

    // SPEC §3.6 — `not` applies to a single boolean atom (no `not not`).
    boolean_expr: ($) =>
      choice(
        $._boolean_operand,
        prec.left("or", seq($.boolean_expr, "or", $.boolean_expr)),
        prec.left("and", seq($.boolean_expr, "and", $.boolean_expr)),
      ),
    _boolean_operand: ($) => choice($._boolean_atom, $.not_expr),
    not_expr: ($) => seq("not", $._boolean_atom),
    _boolean_atom: ($) =>
      choice($.comparison, $.boolean, $.converter, seq("(", $.boolean_expr, ")")),
    comparison: ($) =>
      prec.left("comparison", seq($._value, field("op", $.comparison_op), $._value)),
    comparison_op: () => choice("==", "!=", "<=", ">=", "<", ">"),

    // SPEC §2 — terminals
    // Go interpreted-string escapes only (upstream unquotes strings).
    string: () =>
      new RegExp(
        `"(\\\\(["\\\\abfnrtv]|x${HEX}{2}|[0-3][0-7]{2}|u([0-9a-cA-CeEfF]${HEX}{3}|[dD][0-7]${HEX}{2})|U00(10|0${HEX})${HEX}{4})|[^\\\\"])*"`,
      ),
    bytes: () => new RegExp(`0x(${HEX}{2})+`),
    float: () => /(\d+\.\d*|\d*\.\d+)([eE][+-]?\d+)?/,
    int: () => /\d+/,
    upper_run: () => /[A-Z][A-Z0-9_]*/,
    lower_run: () => runExcept(KEYWORDS),
    // Names glue runs together; whitespace between runs is skipped (upstream quirk).
    lower_name: ($) =>
      seq(choice($.lower_run, "where"), repeat(choice($.lower_run, $.upper_run, "where"))),
    upper_name: ($) => seq($.upper_run, repeat(choice($.lower_run, $.upper_run, "where"))),

    // SPEC §6.2 (extension) — hosts may strip these before passing to upstream.
    line_comment: () => token(seq("//", /[^\r\n]*/)),
    block_comment: () => token(seq("/*", /[^*]*\*+([^/*][^*]*\*+)*/, "/")),
  },
});
