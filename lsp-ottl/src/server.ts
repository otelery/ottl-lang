/**
 * OTTL Language Server — scaffold.
 *
 * What's implemented:
 *   - LSP lifecycle (initialize, initialized, shutdown).
 *   - Text document sync (open, change, close) on stdio transport.
 *   - Diagnostics on every change — invokes the Tree-sitter CLI as a
 *     subprocess and reports any ERROR / MISSING nodes as syntax errors.
 *   - Trivial keyword/operator completion (where, and, or, not, true, …).
 *
 * What's deferred:
 *   - Hover / signature help — needs a function registry.
 *   - Go-to-definition — needs a path / context model.
 *   - Semantic tokens — needs full AST traversal (today we only walk for
 *     errors).
 *   - Formatting — needs a printer.
 *   - Native parser binding — we shell out to the `tree-sitter` CLI per
 *     change, which is fine for files but not for high-frequency typing.
 *     A WASM build (web-tree-sitter) is the next step.
 *
 * See ../SPEC.md for the language definition this server validates against.
 */

import {
  createConnection,
  TextDocuments,
  ProposedFeatures,
  InitializeParams,
  TextDocumentSyncKind,
  InitializeResult,
  Diagnostic,
  DiagnosticSeverity,
  CompletionItem,
  CompletionItemKind,
  TextDocumentPositionParams,
} from "vscode-languageserver/node";
import { TextDocument } from "vscode-languageserver-textdocument";
import { spawnSync } from "child_process";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

const connection = createConnection(ProposedFeatures.all);
const documents = new TextDocuments(TextDocument);

// Resolve the Tree-sitter grammar relative to this server. The user can
// override via OTTL_TREE_SITTER_DIR (e.g. when installed as a global tool).
const TS_DIR =
  process.env.OTTL_TREE_SITTER_DIR || path.resolve(__dirname, "..", "..", "tree-sitter-ottl");
const TS_BIN = path.join(TS_DIR, "node_modules", ".bin", "tree-sitter");

connection.onInitialize((_params: InitializeParams): InitializeResult => {
  return {
    capabilities: {
      textDocumentSync: TextDocumentSyncKind.Incremental,
      completionProvider: { resolveProvider: false, triggerCharacters: [".", "("] },
    },
    serverInfo: { name: "ottl-lsp", version: "0.1.0" },
  };
});

connection.onInitialized(() => {
  if (!fs.existsSync(TS_BIN)) {
    connection.window.showWarningMessage(
      `Tree-sitter not found at ${TS_BIN}. Diagnostics are disabled. ` +
        `Set OTTL_TREE_SITTER_DIR or run 'npm install' in tree-sitter-ottl/.`,
    );
  }
});

documents.onDidChangeContent((change) => {
  validate(change.document);
});

interface ParseError {
  line: number; // 0-indexed
  col: number;
  endLine: number;
  endCol: number;
  message: string;
}

// `tree-sitter parse` prints S-expressions including (ERROR ...) and
// (MISSING ...) nodes with [start_row, start_col] - [end_row, end_col]
// positions. We extract those.
const ERROR_NODE_RE = /\(\s*(ERROR|MISSING [^)]*?)\s*\[(\d+),\s*(\d+)\]\s*-\s*\[(\d+),\s*(\d+)\]/g;

function parse(source: string): ParseError[] {
  if (!fs.existsSync(TS_BIN)) return [];
  const tmp = path.join(os.tmpdir(), `ottl-lsp-${process.pid}-${Date.now()}.ottl`);
  fs.writeFileSync(tmp, source);
  try {
    const r = spawnSync(TS_BIN, ["parse", tmp], {
      cwd: TS_DIR,
      encoding: "utf8",
      maxBuffer: 4 * 1024 * 1024,
    });
    const out = (r.stdout || "") + (r.stderr || "");
    const errors: ParseError[] = [];
    let m;
    while ((m = ERROR_NODE_RE.exec(out)) !== null) {
      const kind = m[1].startsWith("MISSING") ? m[1] : "Syntax error";
      errors.push({
        line: +m[2],
        col: +m[3],
        endLine: +m[4],
        endCol: +m[5],
        message: kind,
      });
    }
    return errors;
  } finally {
    try {
      fs.unlinkSync(tmp);
    } catch {}
  }
}

function validate(doc: TextDocument) {
  const diagnostics: Diagnostic[] = parse(doc.getText()).map((e) => ({
    severity: DiagnosticSeverity.Error,
    range: {
      start: { line: e.line, character: e.col },
      end: { line: e.endLine, character: e.endCol },
    },
    message: e.message,
    source: "ottl",
  }));
  connection.sendDiagnostics({ uri: doc.uri, diagnostics });
}

// SPEC §2.2 keywords + literal tokens.
const KEYWORDS = ["where", "and", "or", "not", "true", "false", "nil"];

connection.onCompletion((_pos: TextDocumentPositionParams): CompletionItem[] => {
  return KEYWORDS.map((k) => ({
    label: k,
    kind: CompletionItemKind.Keyword,
  }));
});

documents.listen(connection);
connection.listen();
