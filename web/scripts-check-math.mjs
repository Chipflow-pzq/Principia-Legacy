import fs from "node:fs";
import path from "node:path";
import katex from "katex";
import { mathTokens, mathBody, isMath } from "./src/math.ts";
const root = path.resolve("..");
const notation = JSON.parse(fs.readFileSync("src/notation.json", "utf8"));
const fields = [];
const latest = new Map();
let activeRecord;
function walk(v, where) {
  if (typeof v === "string")
    fields.push({ text: notation[v] || v, where, record: activeRecord });
  else if (Array.isArray(v)) v.forEach((x, i) => walk(x, where + "." + i));
  else if (v && typeof v === "object")
    for (const [k, x] of Object.entries(v))
      if (!["id", "content_hash", "curation", "anchors", "target"].includes(k))
        walk(x, where + "." + k);
}
function files(dir) {
  return fs
    .readdirSync(dir, { withFileTypes: true })
    .flatMap((e) =>
      e.isDirectory()
        ? files(path.join(dir, e.name))
        : [path.join(dir, e.name)],
    );
}
for (const file of files(path.join(root, "corpus")).filter((f) =>
  f.endsWith(".jsonl"),
)) {
  for (const line of fs
    .readFileSync(file, "utf8")
    .split("\n")
    .filter(Boolean)) {
    const r = JSON.parse(line);
    activeRecord = { id: r.id, revision: r.revision };
    latest.set(r.id, Math.max(latest.get(r.id) || 0, r.revision));
    if (["contribution", "relation"].includes(r.type))
      walk(r, r.id + "@" + r.revision);
    if (r.type === "review") walk(r.rationale, r.id + ".rationale");
    if (r.type === "source") {
      walk(r.title, r.id + ".title");
      for (const a of r.anchors) walk(a.summary, r.id + ".anchor." + a.id);
    }
  }
}
const failures = [];
const historicalWarnings = [];
let formulas = 0;
for (const { text, where, record } of fields) {
  if (/[\x00-\x08\x0b-\x1f\x7f]/.test(text)) {
    const issue = {
      where,
      record,
      error: "Unexpected control character in explanatory text",
    };
    if (latest.get(record.id) === record.revision) failures.push(issue);
    else historicalWarnings.push(issue);
  }
  for (const s of mathTokens(text)) {
    if (!isMath(s)) continue;
    try {
      katex.renderToString(mathBody(s), {
        throwOnError: true,
        trust: false,
        strict: "ignore",
        maxExpand: 1000,
        maxSize: 20,
      });
      formulas++;
    } catch (e) {
      failures.push({ where, formula: s, error: String(e).slice(0, 250) });
    }
  }
}
fs.writeFileSync(
  path.join(root, "reports/math-validation.json"),
  JSON.stringify(
    {
      formulas,
      failures,
      historicalWarnings,
      note: "Superseded immutable versions remain auditable. Control-character errors in current versions fail this check.",
    },
    null,
    2,
  ) + "\n",
);
console.log(
  JSON.stringify({
    formulas,
    failures: failures.length,
    examples: failures.slice(0, 10),
  }),
);
process.exitCode = failures.length ? 1 : 0;
