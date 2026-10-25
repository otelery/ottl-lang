grammar OTTL;

/*
 * OpenTelemetry Transformation Language (OTTL) — ANTLR4 grammar.
 *
 * Specification:  ../SPEC.md
 * Reference impl: ../spec/grammar.go (Participle, upstream)
 *
 * Conformance: this grammar implements SPEC.md §3 (syntactic) and the parts
 * of §4 (semantic) that can be enforced at parse time. The remaining §4
 * constraints (math type rules, comparison rules, argument ordering) are
 * enforced post-parse by the host.
 *
 * Divergences from spec/grammar.go (the upstream Participle grammar):
 *   1. Identifiers are tokenized as a single mixed-case token (SPEC §2.5
 *      alternative), not as concatenated lower/upper runs. Same accepted
 *      language; token stream differs.
 *   2. `editor` does NOT permit trailing keys — SPEC §4.5 says new
 *      implementations MUST reject this at the grammar level. Upstream
 *      accepts it and rejects post-parse for backwards compatibility.
 *   3. Adds a `file` entry rule for multi-statement parsing (SPEC §6.1).
 *   4. Skips `//` and `/_*_/` comments (SPEC §6.2 extension). Files that
 *      contain comments must be preprocessed before being passed to the
 *      upstream parser.
 *
 * Generation:
 *   antlr  -Dlanguage=Java   OTTL.g4
 *   antlr  -Dlanguage=Go     OTTL.g4
 *   antlr  -Dlanguage=Python3 OTTL.g4
 *   antlr  -Dlanguage=JavaScript OTTL.g4
 */

// ===============================================
// Parser Rules
// ===============================================

// SPEC §6.1 — file of statements (LSP, formatters, validators)
file
    : (statement statementSep)* statement? EOF
    ;

statementSep
    : SEMI
    ;

// SPEC §3.1 — single statement (transform/route processors)
statement
    : editor whereClause? EOF
    ;

// SPEC §3.1 — bare condition (filter processor)
condition
    : booleanExpr EOF
    ;

// SPEC §3.2
whereClause
    : WHERE booleanExpr
    ;

// -----------------------------------------------
// Editors and Converters (SPEC §3.2, §4.1, §4.5)
// -----------------------------------------------

// Editor: lowercase first letter, no trailing keys (SPEC §4.5).
editor
    : LOWER_ID LPAREN arguments? RPAREN
    ;

// Converter: uppercase first letter, optional trailing keys.
converter
    : UPPER_ID LPAREN arguments? RPAREN keys?
    ;

arguments
    : argument (COMMA argument)*
    ;

// Named (`name=value`) or positional. The bare UPPER_ID alternative
// allows passing a converter/enum reference by name (SPEC §3.2).
argument
    : (LOWER_ID EQUAL)? value
    | (LOWER_ID EQUAL)? UPPER_ID
    ;

// -----------------------------------------------
// Values (SPEC §3.3)
// -----------------------------------------------

value
    : NIL
    | lambda
    | mathExprLiteral
    | mathExpression
    | BYTES
    | STRING
    | BOOLEAN
    | enumValue
    | mapValue
    | listValue
    ;

// -----------------------------------------------
// Lambda expressions (SPEC §3.7)
// -----------------------------------------------

// Experimental (alpha upstream). Syntactically a lambda is a `value`; hosts
// accept it only as an argument of a Lambda-typed parameter. A lambda body
// that is itself another lambda is rejected post-parse (SPEC §4.9).
// Whether lambda arguments are accepted at all is gated by the host feature
// flag `ottl.functions.enableLambda` (SPEC §4) — the grammar always accepts
// the syntax.
lambda
    : LPAREN (lambdaParam (COMMA lambdaParam)*)? RPAREN ARROW lambdaBody
    ;

lambdaParam
    : LOWER_ID
    | UNDERSCORE
    ;

// `value` is tried before `booleanExpr` so that e.g. `v * 2` parses as a
// math value while `v == "prod"` falls back to a boolean expression.
lambdaBody
    : value
    | booleanExpr
    ;

// SPEC §4.2: UPPER_ID without `(` is an enum. Disambiguation is left to
// ANTLR adaptive prediction; the converter alternative inside
// mathExprLiteral wins when LPAREN follows.
enumValue
    : UPPER_ID
    ;

// -----------------------------------------------
// Paths and Keys (SPEC §3.4)
// -----------------------------------------------

path
    : LOWER_ID DOT field (DOT field)*    // with context
    | field (DOT field)*                  // without context
    ;

field
    : LOWER_ID keys?
    ;

keys
    : key+
    ;

key
    : LBRACKET keyValue RBRACKET
    ;

keyValue
    : STRING
    | INT
    | mathExpression
    | mathExprLiteral
    ;

// -----------------------------------------------
// Lists and Maps (SPEC §3.3)
// -----------------------------------------------

listValue
    : LBRACKET (value (COMMA value)*)? RBRACKET
    ;

mapValue
    : LBRACE (mapItem (COMMA mapItem)* COMMA?)? RBRACE
    ;

mapItem
    : STRING COLON value
    ;

// -----------------------------------------------
// Math Expressions (SPEC §3.5, §5)
// -----------------------------------------------

mathExpression
    : addSubTerm ((PLUS | MINUS) addSubTerm)*
    ;

addSubTerm
    : mathValue ((MULT | DIV) mathValue)*
    ;

mathValue
    : mathExprLiteral
    | LPAREN mathExpression RPAREN
    ;

// SPEC §4.4: `editor` is included here so that the parser can issue a
// precise diagnostic (`converter names must start with an uppercase
// letter ...`) rather than a generic syntax error. Implementations
// MUST reject `editor` occurring inside a value.
mathExprLiteral
    : editor
    | converter
    | FLOAT
    | INT
    | path
    ;

// -----------------------------------------------
// Boolean Expressions (SPEC §3.6, §5)
// -----------------------------------------------

booleanExpr
    : orTerm (OR orTerm)*
    ;

orTerm
    : andTerm (AND andTerm)*
    ;

andTerm
    : NOT? booleanValue
    ;

booleanValue
    : comparison
    | BOOLEAN
    | converter
    | LPAREN booleanExpr RPAREN
    ;

// SPEC §5: comparisons are non-associative — `a == b == c` is rejected
// by the grammar shape (`comparison` is not recursive).
comparison
    : value comparisonOp value
    ;

comparisonOp
    : EQ | NEQ | LTE | GTE | LT | GT
    ;


// ===============================================
// Lexer Rules (SPEC §2)
// ===============================================

// Keywords (SPEC §2.2) — must precede identifiers.
WHERE   : 'where' ;
NOT     : 'not' ;
AND     : 'and' ;
OR      : 'or' ;
NIL     : 'nil' ;
BOOLEAN : 'true' | 'false' ;

// Literals (SPEC §2.3) — order matters: BYTES before INT (0x prefix),
// FLOAT before INT (decimal point).
BYTES   : '0x' [a-fA-F0-9]+ ;
FLOAT   : SIGN? DIGIT* '.' DIGIT+ ([eE] SIGN? DIGIT+)? ;
INT     : SIGN? DIGIT+ ;
STRING  : '"' ( '\\' . | ~[\\"] )* '"' ;

// Operators (SPEC §2.4) — multi-char before single-char.
EQ      : '==' ;
NEQ     : '!=' ;
LTE     : '<=' ;
GTE     : '>=' ;
LT      : '<' ;
GT      : '>' ;
PLUS    : '+' ;
MINUS   : '-' ;
MULT    : '*' ;
DIV     : '/' ;
ARROW   : '=>' ;
EQUAL   : '=' ;

LPAREN   : '(' ;
RPAREN   : ')' ;
LBRACE   : '{' ;
RBRACE   : '}' ;
LBRACKET : '[' ;
RBRACKET : ']' ;
DOT      : '.' ;
COMMA    : ',' ;
COLON    : ':' ;
SEMI     : ';' ;

// Identifiers (SPEC §2.5) — single-token mixed-case strategy.
UPPER_ID : [A-Z] [a-zA-Z0-9_]* ;
LOWER_ID : [a-z] [a-zA-Z0-9_]* ;

// Blank lambda parameter (SPEC §3.7) — standalone underscore only; `_` as
// part of an identifier is absorbed by UPPER_ID/LOWER_ID above.
UNDERSCORE : '_' ;

// Whitespace and comments (SPEC §6.2 extension) — skipped.
WS            : [ \t\r\n]+ -> skip ;
LINE_COMMENT  : '//' ~[\r\n]*       -> skip ;
BLOCK_COMMENT : '/*' .*? '*/'       -> skip ;

// Fragments
fragment SIGN  : [+\-] ;
fragment DIGIT : [0-9] ;
