#!/usr/bin/env node
// Conformance harness for the Tree-sitter OTTL grammar.
//
// Usage: node test-conformance.js <file.ottl> [--expect-fail] [--entry=statement|condition]
//
// We always parse as `source_file`, prefixing condition tests with a synthetic
// `_w_=true where ` wrapper so they reach the boolean_expr branch. (Cheap,
// avoids a second entry-point grammar.)

const fs = require("fs");
const path = require("path");
const Parser = require("tree-sitter");

let language;
try {
  language = require("./bindings/node");
} catch (e) {
  // Fallback: load the .so directly via tree-sitter cli is also fine, but
  // easier to require the bindings. Throw if missing.
  console.error("Run `npx tree-sitter generate` first.");
  process.exit(2);
}

const parser = new Parser();
parser.setLanguage(language);

const args = process.argv.slice(2);
let file = null;
let expectFail = false;
let entry = "statement";
for (const a of args) {
  if (a === "--expect-fail") expectFail = true;
  else if (a.startsWith("--entry=")) entry = a.slice(8);
  else if (!file) file = a;
}
if (!file) {
  console.error("usage: test-conformance.js <file> [--expect-fail] [--entry=...]");
  process.exit(2);
}

const wrap = (line) => (entry === "condition" ? `set(_x, true) where ${line}` : line);

let total = 0,
  pass = 0;
const failures = [];

for (const raw of fs.readFileSync(file, "utf8").split("\n")) {
  const line = raw.replace(/\r$/, "");
  if (!line.trim() || line.trim().startsWith("#")) continue;
  total++;
  const tree = parser.parse(wrap(line));
  const ok = !tree.rootNode.hasError;
  const wantOk = !expectFail;
  if (ok === wantOk) pass++;
  else failures.push(line);
}

console.log(
  `${path.basename(file)}: ${pass}/${total} passed (entry=${entry}, expect-fail=${expectFail})`,
);
for (const f of failures) console.log(`  FAIL: ${f}`);
process.exit(failures.length ? 1 : 0);
