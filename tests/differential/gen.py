#!/usr/bin/env python3
"""Generate differential-test inputs: <mode>\t<base64(input)> lines on stdout.

Sources (all seeded, reproducible):
  corpus    every line of tests/conformance/*.ottl, in every mode
  edge      hand-written edge cases for lexing, numbers, identifiers, maps, keys, lambdas
  mutate    token/char level mutations of corpus lines
  random    random derivations from the SPEC grammar
"""
import argparse, base64, glob, os, random, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODES = ["statement", "condition", "value"]

TOKEN_RE = re.compile(
    r'"(?:\\.|[^\\"])*"|0x[0-9a-fA-F]*|\d*\.\d+(?:[eE][+-]?\d+)?|\d+\.?(?:[eE][+-]?\d+)?|=>|==|!=|<=|>=|[A-Za-z_][A-Za-z0-9_]*|\s+|.',
    re.S)
VOCAB = ['(', ')', '[', ']', '{', '}', ',', '.', ':', '=', '=>', '==', '!=', '<', '>', '<=', '>=', '+', '-', '*', '/',
         'and', 'or', 'not', 'where', 'nil', 'true', 'false', '_', 'x', 'X', 'Set', 'set', 'a_b', 'A_B', '1', '2.5', '.5',
         '3.', '"s"', '0x1f', '0xf', 'attributes', 'resource', 'IsMatch', 'Len', ' ']

def corpus():
    """(mode, line) pairs; *_conditions files are conditions, *_value_expr files are values, the rest statements."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "tests", "conformance", "*.ottl"))):
        n = os.path.basename(f)
        mode = "condition" if "condition" in n else "value" if "value_expr" in n else "statement"
        for line in open(f, encoding="utf-8"):
            line = line.rstrip("\n")
            if line.strip() and not line.lstrip().startswith("#"):
                out.append((mode, line))
    return out

def edge_mode(s):
    """statements start with an editor call; everything else is tried as condition and value."""
    return ["statement"] if re.match(r"\s*[a-z]\w*\s*\(", s) else ["condition", "value"]

EDGE = r'''
set(a, 1)
set(a, -1)
set(a, +1)
set(a, - 1)
set(a, --1)
set(a, - -1)
set(a, -(1))
set(a, -(1+2))
set(a, +(1+2))
set(a, -x)
set(a, -Len(x))
set(a, 1 -2)
set(a, 1 - -2)
set(a, 1-2)
set(a, 1+-2)
set(a, 1*-2)
set(a, 1/-2)
set(a, 3.)
set(a, .5)
set(a, -.5)
set(a, 3.e5)
set(a, 3.5e5)
set(a, 3.5E-5)
set(a, 3e5)
set(a, 3.e)
set(a, 1..2)
set(a, 1.2.3)
set(a, 0x)
set(a, 0x1)
set(a, 0xfff)
set(a, 0xFg)
set(a, 0x1f2)
set(a, 00)
set(a, 007)
set(a, 1_000)
set(a, x.y)
set(a, x.y.z)
set(a, x[0])
set(a, x["k"])
set(a, x["k"]["j"])
set(a, x[0][1])
set(a, x[1+1])
set(a, x[-1])
set(a, x[y])
set(a, x[y.z])
set(a, x[Len(y)])
set(a, x[])
set(a, x[1,2])
set(a, x.y[0].z["k"])
set(a, x[0].)
set(a, Len(y)[0])
set(a, Len(y)["k"][1])
set(a, Len(y).z)
set(a, Len(y)[Len(z)])
set(a, set(b, 1))
set(a, set(b, 1)[0])
set(a, Set(b, 1))
set(Set, 1)
set(set, 1)
Set(a, 1)
set()
set(,)
set(a,)
set(,a)
set(a b)
set(a, , b)
set(a=1)
set(a=1, b=2)
set(a, b=2)
set(a=1, b)
set(a==1)
set(a = 1)
set(a =1)
set(A=1)
set(a_b=1)
set(a1=1)
set(1a=1)
set(a, B)
set(a, B_C)
set(a, BC)
set(a, Bc)
set(a, bC)
set(a, b_C)
set(a, B_c)
set(a, B1)
set(a, B_1)
set(a, _B)
set(a, _b)
set(_, 1)
set(_a, 1)
set(a_, 1)
set(a__b, 1)
set(a, _)
set(ab_c, 1)
set(aBc, 1)
set(aBC, 1)
set(a.B, 1)
set(A.b, 1)
set(a.B.c, 1)
set(where, 1)
set(not, 1)
set(and, 1)
set(or, 1)
set(nil, 1)
set(true, 1)
set(false, 1)
set(nilx, 1)
set(xnil, 1)
set(truey, 1)
set(notx, 1)
set(where.x, 1)
set(x.where, 1)
set(x.not, 1)
set(x.nil, 1)
set(x.true, 1)
set(a, nil)
set(a, Nil)
set(a, NIL)
set(a, nil[0])
set(a, true)
set(a, True)
set(a, TRUE)
set(a, tRue)
set(a, truefalse)
set(a, "")
set(a, "x")
set(a, "x\"y")
set(a, "x\\")
set(a, "x\n")
set(a, "x
y")
set(a, "é")
set(a, "é")
set(a, "unterminated)
set(a, 'single')
set(a, `back`)
set(a, "a" "b")
set(a, "a" + "b")
set(a, "a" == "b")
set(a, [])
set(a, [1])
set(a, [1,])
set(a, [,1])
set(a, [1,2])
set(a, [1 2])
set(a, [[]])
set(a, [[1],[2]])
set(a, [{}])
set(a, [nil])
set(a, [x])
set(a, [x.y])
set(a, [(1)])
set(a, [1+2])
set(a, [Len(x)])
set(a, [B])
set(a, [(_) => _])
set(a, [1][0])
set(a, {})
set(a, {"k":1})
set(a, {"k":1,})
set(a, {"k":1,"j":2})
set(a, {"k":1 "j":2})
set(a, {"k":1,,"j":2})
set(a, {,})
set(a, {"k"})
set(a, {"k":})
set(a, {k:1})
set(a, {1:1})
set(a, {"k":{"j":1}})
set(a, {"k":[1,2]})
set(a, {"k":x.y})
set(a, {"k":1+2})
set(a, {"k":Len(x)})
set(a, {"k":nil})
set(a, {"k":(_) => _})
set(a, {"k": 1, "k": 2})
set(a, {"k":1}["k"])
set(a, 1 + 2)
set(a, 1 + 2 * 3)
set(a, (1 + 2) * 3)
set(a, ((1)))
set(a, ())
set(a, (1)
set(a, 1)))
set(a, 1 +)
set(a, + 1)
set(a, 1 * * 2)
set(a, 1 / 0)
set(a, x + y)
set(a, x + Len(y))
set(a, Len(x) + 1)
set(a, "a" + 1)
set(a, (x) + 1)
set(a, (x))
set(a, (x.y))
set(a, (Len(x)))
set(a, (nil))
set(a, ("s"))
set(a, (true))
set(a, (B))
set(a, (0x1f))
set(a, ([1]))
set(a, ({}))
set(a, x == 1)
set(a, 1 == 1)
set(a, x == y == z)
set(a, x < y)
set(a, x and y)
set(a, x or y)
set(a, not x)
set(a, true and false)
set(a, Len(x) > 1)
set(a, (x == 1))
set(a, 1 == 1 and 2 == 2)
set(a, x == 1 or y == 2 and z == 3)
set(a, B == B)
set(a, nil == nil)
set(a, "a" == nil)
set(a, 1 !== 2)
set(a, 1 === 2)
set(a, 1 <> 2)
set(a, 1 =< 2)
set(a, 1 => 2)
set(a, 1 > = 2)
set(a, 1 = = 2)
set(a, 1 ! = 2)
set(a, Fn(1)(2))
set(a, Fn(1)[0](2))
set(a, Fn(B))
set(a, Fn(B, C))
set(a, Fn(B=C))
set(a, Fn(x=B))
set(a, Fn(x=(_) => _))
set(a, Fn(x=1, y=2))
set(a, Fn(1, y=2))
set(a, Fn(x=1, 2))
set(a, Fn(x=B()))
set(a, Fn(B()))
set(a, Fn(b()))
set(a, Fn(b))
set(a, Fn(set(b, 1)))
set(a, Fn(1)(2))
set(a, FN(1))
set(a, FN_(1))
set(a, F1(1))
set(a, F_1(1))
set(a, F_(1))
set(a, _F(1))
set(a, fN(1))
set(a, f(1))
set(a, f_N(1))
set(a, ()=>1)
set(a, F(()=>1))
set(a, F(() => 1))
set(a, F((x) => 1))
set(a, F((x, y) => 1))
set(a, F((_) => 1))
set(a, F((_, _) => 1))
set(a, F((x, x) => 1))
set(a, F((x,) => 1))
set(a, F((,x) => 1))
set(a, F((x y) => 1))
set(a, F((X) => 1))
set(a, F((1) => 1))
set(a, F(("s") => 1))
set(a, F((x.y) => 1))
set(a, F((x[0]) => 1))
set(a, F((F()) => 1))
set(a, F((_x) => 1))
set(a, F((x_) => 1))
set(a, F((__) => 1))
set(a, F((_1) => 1))
set(a, F((nil) => 1))
set(a, F((true) => 1))
set(a, F((where) => 1))
set(a, F((not) => 1))
set(a, F((x) => x))
set(a, F((x) => x.y))
set(a, F((x) => x[0]))
set(a, F((x) => x["k"]))
set(a, F((x) => x == 1))
set(a, F((x) => x == 1 and x == 2))
set(a, F((x) => x == 1 or x == 2))
set(a, F((x) => not x))
set(a, F((x) => not x == 1))
set(a, F((x) => (x == 1)))
set(a, F((x) => (x)))
set(a, F((x) => (x) + 1))
set(a, F((x) => (x + 1)))
set(a, F((x) => x + 1))
set(a, F((x) => x + 1 == 2))
set(a, F((x) => x == 1 + 1))
set(a, F((x) => Len(x)))
set(a, F((x) => Len(x) > 1))
set(a, F((x) => Is(x)))
set(a, F((x) => Is(x) and true))
set(a, F((x) => true))
set(a, F((x) => true and x))
set(a, F((x) => false or x))
set(a, F((x) => nil))
set(a, F((x) => nil == x))
set(a, F((x) => "s"))
set(a, F((x) => "s" == x))
set(a, F((x) => 0x1f))
set(a, F((x) => [x]))
set(a, F((x) => [x, 1]))
set(a, F((x) => {"k": x}))
set(a, F((x) => B))
set(a, F((x) => B == x))
set(a, F((x) => B and x))
set(a, F((x) => -x))
set(a, F((x) => -x == 1))
set(a, F((x) => -(x)))
set(a, F((x) => x))
set(a, F((x) => ))
set(a, F((x) =>))
set(a, F((x) => ,))
set(a, F((x) => 1, 2))
set(a, F((x) => 1, (y) => 2))
set(a, F((x) => (y) => 1))
set(a, F((x) => (y) => y))
set(a, F((x) => () => 1))
set(a, F(() => () => 1))
set(a, F((x) => F((y) => x == y)))
set(a, F((x) => F((y) => x == y) and true))
set(a, F((x) => F(() => 1)))
set(a, F((x) => ((y) => 1)))
set(a, F((x) => ((y) => 1) + 1))
set(a, F((x) => (y) => y == 1))
set(a, F((x) => (y) => y and true))
set(a, F(x => 1))
set(a, F(x, y => 1))
set(a, F(=> 1))
set(a, F(() -> 1))
set(a, F(() = > 1))
set(a, F(()=>1)[0])
set(a, F((x)=>1)["k"])
set(a, F()=>1)
set(a, F(x)=>1)
set(a, (x) => 1)
set(a, (x, y) => 1)
set(a, (x) => x == 1)
set(a, ((x) => 1))
set(a, ((x)) => 1)
set(a, (x) => 1 + 2)
set(a, (x) => 1 + (2))
set(a, (x) =>1)
set(a, (x)=> 1)
set(a, (x)=>1)
set(a, (x)\n=> 1)
set(a, (x) =>\n1)
set(a, (x
) => 1)
set(a, (x) => [1][0])
set(a, F(attr=(x) => 1))
set(a, F(attr = (x) => 1))
set(a, F(attr=() => 1, other=2))
set(a, F(a=() => 1, b=() => 2))
set(a, F(() => 1, () => 2))
set(a, F((x) => G((y) => x)))
set(a, F((x) => G((y) => x), 1))
set(a, F((x) => G((y) => x) == 1))
set(a, F((x) => G(() => 1) + 1))
set(a, F((x) => 1 + G(() => 1)))
set(a, F((x) => x[G(() => 1)]))
set(a, F((x) => x[(y) => 1]))
set(a, x[(y) => 1])
set(a, x[F((y) => 1)])
set(a, [(y) => 1])
set(a, {"k": (y) => 1})
set(a, F((_) => _))
set(a, F((_) => _ == 1))
set(a, F((_, _) => _))
set(a, F((_) => _.x))
set(a, F((_) => _[0]))
set(a, F((_) => _ + 1))
set(a, F((_) => G(_)))
set(a, G(_))
set(a, _ == 1)
set(a, _ + 1)
set(a, [_])
set(a, {"k": _})
set(a, x._)
set(a, _.x)
set(a, _[0])
set(a, F(_=1))
set(a, F(x=_))
set(set(a, 1), 2)
set(a, 1) where true
set(a, 1) where x
set(a, 1) where x == 1
set(a, 1) where not x
set(a, 1) where (x)
set(a, 1) where Is(x)
set(a, 1) where Is(x) and y
set(a, 1) where x == 1 and y == 2 or z
set(a, 1) where
set(a, 1) where where true
set(a, 1) where 1
set(a, 1) where "s"
set(a, 1) where nil
set(a, 1) where x.y
set(a, 1) where x + 1
set(a, 1) where F((x) => x)
set(a, 1) where F((x) => x) == 1
set(a, 1) where (x) => x
set(a, 1) where Is(x)[0]
set(a, 1) where Is(x)[0] == 1
set(a, 1) where true true
set(a, 1) where x == y == z
set(a, 1) where not not x
set(a, 1) where not (not x)
set(a, 1) where not x and y
set(a, 1) where not (x and y)
set(a, 1)where true
set(a, 1) where(true)
set(a, 1) where(x == 1)
set(a, 1) wherex
set(a, 1)  where  true
set(a, 1)
where true
set(a, 1) where true
 and false
set(a, 1) or true
set(a, 1) and true
set(a, 1) == 1
set(a, 1);
set(a, 1); set(b, 2)
set(a, 1) // comment
set(a, 1) /* c */
// c
set(a, /* c */ 1)
set(a, "// not comment")
set(a, "/* not */")
set(a, 1 / 2)
set(a, 1 // 2)
set(a, 1 /* 2 */)
set(a, x/*c*/y)
 set(a, 1)
set(a, 1) 
	set(a, 1)	
set(a, 1)\n
set(a,1)
set(a,1)where true
set (a, 1)
set( a , 1 )
set(a ,1)
set(a, 1)(
set(a, 1))
set(a, 1
set a, 1
set(a, 1)extra
set(a, 1) extra
set(a, 1) where true extra
set(a, 1) set(b, 2)
setx(a, 1)
set_x(a, 1)
set1(a, 1)
s(a, 1)
s_(a, 1)
_s(a, 1)
a(a, 1)
aB(a, 1)
ab_C(a, 1)
ab_c_(a, 1)
ab1_c2(a, 1)
Ab(a, 1)
A(a, 1)
Func()
func()
Func(1)
x
x.y
1
"s"
nil
true
x == 1
x == 1 and y == 2
(x)
(x == 1)
((x == 1))
(x == 1) and (y == 2)
not x
not (x)
not Is(x)
Is(x)
Is(x) and Is(y)
Is(x) or Is(y)
Is(x)[0]
Is(x)[0] == 1
Is(x) == 1
1 == Is(x)
x == Is(x)
Is(x) == Is(y)
true
false
true and false
true or false
not true
not not true
(true)
((true))
(true) and (false)
x.y == nil
x.y != nil
nil == x.y
nil == nil
1 == 1
1.0 == 1
1 == 1.0
"a" == "a"
x < 1
x <= 1
x > 1
x >= 1
x != 1
x = 1
x === 1
x < y < z
x == (y == z)
(x == y) == z
-1 == x
- 1 == x
x == -1
x == - 1
x == --1
x + 1 == y
x == y + 1
x * 2 == y / 2
(x + 1) * 2 == y
(x + 1) == (y - 1)
Len(x) + 1 == 2
Len(x) == 1 + 1
F((x) => x)
F((x) => x) == 1
F((x) => x == 1)
(x) => x
(x) => x == 1
F((x) => x == 1) and true
true and F((x) => x == 1)
not F((x) => x == 1)
F(() => true)
F(() => true) and G(() => false)
x == F((y) => y)
F((y) => y) == x
x == F((y) => y == 1)
(F((y) => y))
(F((y) => y)) == 1
[1] == [1]
{"k":1} == {"k":1}
x == [1]
x == {"k":1}
x == B
B == x
B == B
B
B_C
b
'''.strip("\n").split("\n")

# `\n` in the table above stands for a real newline
EDGE = [e.replace("\\n", "\n") for e in EDGE]

def tokens(s):
    return TOKEN_RE.findall(s)

def mutate(line, rng):
    toks = tokens(line)
    if not toks:
        return line
    k = rng.choice(["del", "dup", "swap", "repl", "ins", "chardel", "charins", "trunc", "space"])
    i = rng.randrange(len(toks))
    if k == "del":
        del toks[i]
    elif k == "dup":
        toks.insert(i, toks[i])
    elif k == "swap" and len(toks) > 1:
        j = min(i + 1, len(toks) - 1)
        toks[i], toks[j] = toks[j], toks[i]
    elif k == "repl":
        toks[i] = rng.choice(VOCAB)
    elif k == "ins":
        toks.insert(i, rng.choice(VOCAB))
    elif k == "chardel":
        s = "".join(toks)
        if s:
            p = rng.randrange(len(s)); return s[:p] + s[p + 1:]
    elif k == "charins":
        s = "".join(toks)
        p = rng.randrange(len(s) + 1); return s[:p] + rng.choice('()[]{},.:=<>!+-*/_"0aA ') + s[p:]
    elif k == "trunc":
        return "".join(toks[: max(1, i)])
    elif k == "space":
        toks.insert(i, " ")
    return "".join(toks)

# ---- random derivation from SPEC ------------------------------------------------
LOWER = ["a", "b", "x", "attributes", "resource", "span", "log", "name", "a_b", "a1", "aB", "key", "body", "v", "k"]
UPPER = ["Len", "IsMatch", "Concat", "Int", "String", "Is", "F", "G", "Foo_Bar", "FOO", "A1", "Format"]
ENUMS = ["B", "SPAN_KIND_SERVER", "METRIC_DATA_TYPE_SUM", "X1"]
EDITORS = ["set", "delete_key", "keep_keys", "a_b", "x1"]

class Gen:
    def __init__(self, rng):
        self.r = rng
        self.params = []

    def pick(self, xs): return self.r.choice(xs)
    def ws(self): return self.pick(["", "", "", " ", "  ", "\n"])

    def number(self):
        return self.pick(["0", "1", "42", "007", "1.5", ".5", "3.", "1.5e3", "2.e2", ".5E-2", "-1", "+2", "-1.5", "-.5",
                          "1e3", "0.0", "1.2.3"])

    def literal(self):
        return self.pick([self.number, lambda: self.pick(['"s"', '""', '"a b"', '"q\\"q"', '"\\\\"', '"é"']),
                          lambda: self.pick(["0x1f", "0xAB", "0xabc", "0x"]), lambda: self.pick(["true", "false"]), lambda: "nil"])()

    def ident_path(self):
        parts = []
        for _ in range(self.r.randint(1, 3)):
            seg = self.pick(LOWER + self.params) if self.r.random() < 0.8 else self.pick(["where", "not", "nilx", "x_"])
            for _ in range(self.r.choice([0, 0, 0, 1, 2])):
                seg += "[" + self.key() + "]"
            parts.append(seg)
        return ".".join(parts)

    def key(self):
        return self.pick([lambda: self.pick(['"k"', '"a b"']), lambda: str(self.r.randint(0, 3)), lambda: self.math(1),
                          lambda: self.ident_path(), lambda: self.call(1)])()

    def args(self, d):
        n = self.r.choice([0, 1, 1, 2, 3])
        out = []
        named = False
        for _ in range(n):
            if self.r.random() < 0.25:
                named = True
            a = self.arg(d)
            out.append((self.pick(LOWER) + self.pick(["=", " = ", "= "]) + a) if named else a)
        return (self.pick([",", ", ", " , "])).join(out)

    def arg(self, d):
        if self.r.random() < 0.1:
            return self.pick(UPPER + ENUMS)
        return self.value(d)

    def call(self, d):
        s = self.pick(UPPER) + "(" + self.ws() + self.args(d) + self.ws() + ")"
        for _ in range(self.r.choice([0, 0, 0, 1])):
            s += "[" + self.key() + "]"
        return s

    def lam(self, d):
        n = self.r.choice([0, 1, 1, 2, 3])
        ps = [self.pick(["_", "_", "x", "y", "k", "v", "a1", "X", "x_"]) for _ in range(n)]
        sep = self.pick([",", ", "])
        old = self.params
        self.params = old + [p for p in ps if p != "_"]
        if self.r.random() < 0.5:
            body = self.value(d + 1)
        else:
            body = self.boolexpr(d + 1)
        self.params = old
        return "(" + sep.join(ps) + ")" + self.pick([" => ", "=>", " =>", "=> "]) + body

    def math(self, d):
        atoms = [self.number, self.ident_path, lambda: self.call(d + 1), lambda: "(" + self.math(d + 1) + ")",
                 lambda: self.pick(["-", "+", ""]) + "(" + self.math(d + 1) + ")"]
        if d > 3:
            atoms = atoms[:3]
        s = self.pick(atoms)()
        for _ in range(self.r.choice([0, 0, 1, 2])):
            s += self.pick(["+", "-", "*", "/", " + ", " - ", " * ", " / ", " -", " +"]) + self.pick(atoms)()
        return s

    def value(self, d=0):
        if d > 4:
            return self.literal()
        c = self.r.random()
        if c < 0.18: return self.literal()
        if c < 0.38: return self.ident_path()
        if c < 0.55: return self.call(d + 1)
        if c < 0.65: return self.math(d + 1)
        if c < 0.72: return self.pick(ENUMS)
        if c < 0.80: return "[" + self.pick([",", ", "]).join(self.value(d + 1) for _ in range(self.r.randint(0, 3))) + self.pick(["", "", ","]) + "]"
        if c < 0.88:
            items = [self.pick(['"k"', '"j"']) + self.pick([":", ": ", " : "]) + self.value(d + 1) for _ in range(self.r.randint(0, 3))]
            return "{" + self.pick([",", ", ", " "]).join(items) + self.pick(["", "", ","]) + "}"
        if c < 0.97: return self.lam(d)
        return "(" + self.value(d + 1) + ")"

    def comparison(self, d):
        return self.value(d + 1) + self.pick([" == ", " != ", " < ", " <= ", " > ", " >= ", "==", " = "]) + self.value(d + 1)

    def boolatom(self, d):
        c = self.r.random()
        if c < 0.4: return self.comparison(d)
        if c < 0.55: return self.pick(["true", "false"])
        if c < 0.8: return self.call(d + 1)
        if c < 0.9 and d < 3: return "(" + self.boolexpr(d + 1) + ")"
        return self.value(d + 1)

    def boolexpr(self, d=0):
        s = self.pick(["", "", "not ", "not "]) + self.boolatom(d)
        for _ in range(self.r.choice([0, 0, 1, 2])):
            s += self.pick([" and ", " or "]) + self.pick(["", "not "]) + self.boolatom(d)
        return s

    def statement(self):
        s = self.pick(EDITORS) + "(" + self.ws() + self.args(0) + self.ws() + ")"
        if self.r.random() < 0.4:
            s += self.pick([" where ", " where", " where  "]) + self.boolexpr()
        return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--mutations", type=int, default=3, help="mutants per corpus line")
    ap.add_argument("--random", type=int, default=5000, help="random derivations per mode")
    ap.add_argument("--modes", default=",".join(MODES))
    a = ap.parse_args()
    rng = random.Random(a.seed)
    modes = a.modes.split(",")
    seen = set()
    def emit(mode, s):
        if (mode, s) in seen:
            return
        seen.add((mode, s))
        sys.stdout.write(mode + "\t" + base64.b64encode(s.encode("utf-8")).decode() + "\n")
    base = corpus()
    for m, s in base:
        if m in modes: emit(m, s)
    for s in EDGE:
        for m in edge_mode(s):
            if m in modes: emit(m, s)
    for mode, s in base:
        if mode not in modes: continue
        for _ in range(a.mutations):
            emit(mode, mutate(s, rng))
    g = Gen(rng)
    for _ in range(a.random):
        if "statement" in modes: emit("statement", g.statement())
        if "condition" in modes: emit("condition", g.boolexpr())
        if "value" in modes: emit("value", g.value())
    # mutate a slice of the random ones too
    for _ in range(a.random // 2):
        s = g.statement()
        for _ in range(rng.randint(1, 3)):
            s = mutate(s, rng)
        if "statement" in modes: emit("statement", s)

if __name__ == "__main__":
    main()
