#!/usr/bin/env python3
"""Differential parser test: upstream Participle (oracle) vs ANTLR vs Tree-sitter.

  tests/differential/run.py [--upstream DIR] [--ref REF] [--seed N] [--random N] [--mutations N] [--report FILE]

Needs: go, java + javac + ANTLR jar (make build), node + tree-sitter-ottl deps.
Exit status is 1 when any *unexpected* disagreement with upstream remains.
"""
import argparse, base64, collections, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CACHE = os.path.join(ROOT, "build", "differential")
UPSTREAM_GIT = "https://github.com/open-telemetry/opentelemetry-collector-contrib.git"

def sh(cmd, **kw):
    r = subprocess.run(cmd, text=True, capture_output=True, **kw)
    if r.returncode != 0 and not kw.get("check") is False:
        pass
    return r

def b64d(s): return base64.b64decode(s).decode("utf-8", "replace")

def fetch_upstream(path, ref):
    if path:
        return path
    d = os.path.join(CACHE, "contrib")
    if not os.path.isdir(d):
        os.makedirs(CACHE, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", UPSTREAM_GIT, d], check=True)
        subprocess.run(["git", "-C", d, "sparse-checkout", "set", "pkg/ottl"], check=True)
    if ref:
        subprocess.run(["git", "-C", d, "fetch", "-q", "--depth", "1", "origin", ref], check=True)
        subprocess.run(["git", "-C", d, "checkout", "-q", "FETCH_HEAD"], check=True)
    return d

def run_go(up, infile, outfile):
    """Build a test-free copy of pkg/ottl (its own tests need unrelated sibling modules) plus our driver."""
    src = os.path.join(up, "pkg", "ottl")
    work = os.path.join(CACHE, "ottl-work")
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(src, work, ignore=shutil.ignore_patterns("*_test.go", "e2e", "contexts", "ottlfuncs", "xottl", "testdata"))
    shutil.copy(os.path.join(HERE, "go", "zz_diff_test.go"), os.path.join(work, "zz_diff_test.go"))
    env = dict(os.environ, DIFF_IN=infile, DIFF_OUT=outfile)
    r = subprocess.run(["go", "test", "-count=1", "-run", "TestZZDifferential", "."], cwd=work, env=env, text=True, capture_output=True)
    if r.returncode != 0:
        sys.exit("go oracle failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])

def antlr_jar():
    import glob
    j = os.environ.get("ANTLR_JAR")
    if j and os.path.isfile(j): return j
    wrapper = shutil.which("antlr")
    if wrapper:
        m = re.search(r"/[^ \"']*antlr-[0-9.]+-complete\.jar", open(wrapper, errors="ignore").read())
        if m and os.path.isfile(m.group(0)): return m.group(0)
    for pat in ("/usr/local/lib/antlr-*-complete.jar", "/usr/share/java/antlr-*-complete.jar",
                "/opt/homebrew/Cellar/antlr/*/libexec/antlr-*-complete.jar",
                "/home/linuxbrew/.linuxbrew/Cellar/antlr/*/antlr-*-complete.jar",
                os.path.expanduser("~/.local/share/antlr/antlr-*-complete.jar")):
        hits = glob.glob(pat)
        if hits: return hits[0]
    sys.exit("ANTLR jar not found; set ANTLR_JAR")

def run_antlr(infile, outfile):
    jar = antlr_jar()
    build = os.path.join(ROOT, "build", "java")
    d = os.path.join(CACHE, "java")
    os.makedirs(d, exist_ok=True)
    cp = f"{jar}:{build}"
    r = subprocess.run(["javac", "-cp", cp, "-d", d, os.path.join(HERE, "java", "Diff.java")], text=True, capture_output=True)
    if r.returncode: sys.exit("javac failed:\n" + r.stderr)
    r = subprocess.run(["java", "-cp", f"{d}:{cp}", "Diff", infile, outfile], text=True, capture_output=True)
    if r.returncode: sys.exit("antlr driver failed:\n" + r.stderr[-3000:])

def wrap_ts(mode, s):
    return {"condition": "@@c ", "value": "@@v "}.get(mode, "") + s

def build_ts_variant():
    """Tree-sitter has a single start rule; add test-only `@@c` / `@@v` entry points to a private copy."""
    src = os.path.join(ROOT, "tree-sitter-ottl")
    d = os.path.join(CACHE, "ts")
    os.makedirs(d, exist_ok=True)
    g = open(os.path.join(src, "grammar.js")).read()
    old = 'source_file: ($) => seq(repeat(seq($.statement, ";")), optional($.statement)),'
    if old not in g: sys.exit("tree-sitter grammar.js: source_file rule changed, update build_ts_variant()")
    g = g.replace(old, 'source_file: ($) => choice(seq(repeat(seq($.statement, ";")), optional($.statement)), '
                       'seq("@@c", $.boolean_expr), seq("@@v", $._value)),')
    open(os.path.join(d, "grammar.js"), "w").write(g)
    exe = os.path.join(src, "node_modules", ".bin", "tree-sitter")
    r = subprocess.run([exe, "generate"], cwd=d, text=True, capture_output=True)
    if r.returncode: sys.exit("tree-sitter generate failed:\n" + r.stderr[-3000:])
    return d, exe

def run_ts(rows, outfile, chunk=3000):
    ts, exe = build_ts_variant()
    res = [None] * len(rows)
    with tempfile.TemporaryDirectory() as td:
        for lo in range(0, len(rows), chunk):
            part = rows[lo:lo + chunk]
            paths = []
            for i, (mode, s) in enumerate(part):
                p = os.path.join(td, f"{lo + i}.ottl")
                with open(p, "w", encoding="utf-8", newline="") as f: f.write(wrap_ts(mode, s))
                paths.append(p)
            pf = os.path.join(td, "paths.txt")
            open(pf, "w").write("\n".join(paths) + "\n")
            r = subprocess.run([exe, "parse", "-q", "-j", "--paths", pf], cwd=ts, text=True, capture_output=True)
            txt = r.stdout
            start = txt.find("{")
            try: summ = json.loads(txt[start:])["parse_summaries"]
            except Exception: sys.exit("tree-sitter output not parseable:\n" + (r.stdout + r.stderr)[-2000:])
            for sm in summ:
                idx = int(os.path.basename(sm["file"]).split(".")[0])
                res[idx] = "OK" if sm.get("successful") else "ERR"
            for p in paths: os.remove(p)
    with open(outfile, "w") as f:
        for r in res: f.write((r or "ERR") + "\n")

import re
def reason(err):
    e = re.sub(r"^\d+:\d+: ", "", err)
    e = re.sub(r"near `.*?`", "near `…`", e)
    e = re.sub(r"but got .*", "but got …", e)
    e = re.sub(r"got '.*?'", "got '…'", e)
    return e[:110]

def classify(s, err="", mode_hint=""):
    """Known, documented divergences that are not bugs (SPEC §6)."""
    if any(m in err for m in ("must start with", "only paths and converters may be indexed", "lambda body cannot")):
        return "post-parse semantic check (SPEC §4)"
    if ";" in s.replace('"', "") and s.count(";"): return "file-grammar `;` (SPEC §6.1)"
    q = re.sub(r'"(?:\\.|[^\\"])*"', '""', s)   # strip string literals for the heuristics below
    if re.search(r"[a-z0-9_]\s+[A-Z]|[A-Z0-9_]\s+[a-z]", q) and "upstream-accepts" == mode_hint:
        return "identifier-run gluing (upstream quirk)"
    if "=>" in s and mode_hint != "upstream-accepts": return "lambda body greediness (lookahead vs adaptive parsing)"
    if re.search(r"(?<![A-Za-z0-9_.])(and|or|not|nil|true|false)[a-zA-Z0-9_]|[A-Za-z0-9_](not|and|or|nil|true|false)(?![a-z0-9_])", q): return "keyword without word boundary (`\\b` in upstream lexer)"
    if re.search(r"\[\s*\d+\s*[-+*/]", q): return "integer-led key expression (upstream quirk)"
    if "//" in s or "/*" in s: return "comments extension (SPEC §6.2)"
    if not s.strip(): return "empty file (SPEC §6.1)"
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream"); ap.add_argument("--ref")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--random", type=int, default=5000)
    ap.add_argument("--mutations", type=int, default=3)
    ap.add_argument("--modes", default="statement,condition,value")
    ap.add_argument("--report", default=os.path.join(CACHE, "report.md"))
    ap.add_argument("--max-examples", type=int, default=6)
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)

    up = fetch_upstream(a.upstream, a.ref)
    sha = subprocess.run(["git", "-C", up, "rev-parse", "--short", "HEAD"], text=True, capture_output=True).stdout.strip()
    infile = os.path.join(CACHE, "inputs.tsv")
    with open(infile, "w") as f:
        subprocess.run([sys.executable, os.path.join(HERE, "gen.py"), "--seed", str(a.seed), "--random", str(a.random),
                        "--mutations", str(a.mutations), "--modes", a.modes], stdout=f, check=True)
    rows = []
    for line in open(infile):
        mode, enc = line.rstrip("\n").split("\t")
        rows.append((mode, b64d(enc)))
    print(f"{len(rows)} inputs; upstream {sha}", file=sys.stderr)

    go_out, ja_out, ts_out = (os.path.join(CACHE, n) for n in ("go.out", "antlr.out", "ts.out"))
    print("running upstream Participle ...", file=sys.stderr); run_go(up, infile, go_out)
    print("running ANTLR ...", file=sys.stderr); run_antlr(infile, ja_out)
    print("running Tree-sitter ...", file=sys.stderr); run_ts(rows, ts_out)

    def load(p): return [l.rstrip("\n") for l in open(p)]
    go, ja, ts = load(go_out), load(ja_out), load(ts_out)
    assert len(go) == len(ja) == len(ts) == len(rows), (len(go), len(ja), len(ts), len(rows))

    groups = collections.defaultdict(list)   # (kind, mode, expected-tag) -> [(input, goErr)]
    agree = 0
    for (mode, s), g, j, t in zip(rows, go, ja, ts):
        gv, jv, tv = g.split("\t")[0], j.split("\t")[0], t.split("\t")[0]
        if gv == jv == tv:
            agree += 1; continue
        kind = []
        if jv != gv: kind.append("antlr " + ("accepts" if jv == "OK" else "rejects") + " but upstream " + ("accepts" if gv == "OK" else "rejects"))
        if tv != gv: kind.append("tree-sitter " + ("accepts" if tv == "OK" else "rejects") + " but upstream " + ("accepts" if gv == "OK" else "rejects"))
        goerr = b64d(g.split("\t")[1]) if "\t" in g else ""
        for k in kind:
            groups[(k, mode, classify(s, goerr, 'upstream-accepts' if gv == 'OK' else ''), reason(goerr) if gv != 'OK' else '')].append((s, goerr))

    unexpected = sum(len(v) for (k, m, c, r), v in groups.items() if c is None)
    expected = sum(len(v) for (k, m, c, r), v in groups.items() if c is not None)
    lines = [f"# Differential report", "", f"- upstream: `{sha}`  inputs: {len(rows)}  seed: {a.seed}",
             f"- all three agree: **{agree}**; unexpected disagreement entries: **{unexpected}**; expected (SPEC §6 extensions): {expected}", ""]
    for (k, m, c, r), v in sorted(groups.items(), key=lambda kv: (kv[0][2] is not None, -len(kv[1]))):
        tag = f" _(expected: {c})_" if c else ""
        lines.append(f"## {k} — mode `{m}` — {len(v)} input(s){tag}" + (f"\n_upstream: {r}_" if r else ""))
        v = sorted(v, key=lambda x: (len(x[0]), x[0]))
        for s, e in v[: a.max_examples]:
            lines.append(f"- `{s!r}`")
        lines.append("")
    open(a.report, "w").write("\n".join(lines))
    print("\n".join(lines[:4]))
    print(f"report: {a.report}")
    sys.exit(1 if unexpected else 0)

if __name__ == "__main__":
    main()
