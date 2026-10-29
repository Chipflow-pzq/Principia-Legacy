import type { Entry, Index } from "./indexTypes";

export function rankEntries(
  index: Index,
  query: string,
  limit = 8,
  subjects: string[] = [],
): Entry[] {
  // Common field names and eponyms differ from the wording of individual insights.
  // These expand retrieval only; they never create claims or graph relationships.
  query = query
    .replace(/\b(?:Newtonian|classical) mechanics\b/gi, "Newton law")
    .replace(/\bBayesian (?:inference|statistics)\b/gi, "Bayes probability")
    .replace(/\bDarwinian evolution\b/gi, "natural selection");
  const stop = new Set([
    "the",
    "and",
    "for",
    "with",
    "from",
    "what",
    "how",
    "does",
    "research",
    "result",
    "results",
    "into",
    "that",
    "this",
    "its",
    "did",
    "was",
    "were",
    "has",
    "have",
    "had",
    "can",
    "could",
    "would",
    "should",
    "which",
    "where",
    "when",
    "why",
    "their",
    "these",
    "build",
    "built",
    "earlier",
    "later",
    "prior",
    "using",
    "used",
    "based",
    "history",
    "origins",
    "review",
    "mechanism",
    "mechanisms",
    "fundamentals",
    "foundations",
    "limitations",
    "evidence",
  ]);
  const stem = (word: string) =>
    word.replace(/vapour/g, "vapor").replace(/s$/, "");
  const tokens = [
    ...new Set(
      (query.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) || [])
        .filter((w) => !stop.has(w))
        .map(stem),
    ),
  ];
  return matcher(index.entries)(tokens, query, limit, subjects);
}

// Encode the entry number and four field flags into one 32-bit posting. Build
// once per public snapshot; queries visit matching postings rather than parsing
// every explanation again. This index never contains personal research prompts.
const prepared = new WeakMap<Entry[], ReturnType<typeof prepare>>();
function matcher(entries: Entry[]) {
  let match = prepared.get(entries);
  if (!match) {
    match = prepare(entries);
    prepared.set(entries, match);
  }
  return match;
}
export function prepare(entries: Entry[]) {
  const building = new Map<string, number[]>();
  const words = (text: string) =>
    (text.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) || []).map((word) =>
      word.replace(/vapour/g, "vapor").replace(/s$/, ""),
    );
  entries.forEach((entry, number) => {
    const fields = new Map<string, number>();
    const add = (text: string, flag: number) => {
      for (const word of words(text))
        fields.set(word, (fields.get(word) || 0) | flag);
    };
    add(entry.title, 1);
    add(entry.explanation, 2);
    add(String(entry.date.year ?? ""), 2);
    add(entry.attribution.map((a) => a.name).join(" "), 6);
    add(entry.claim, 10);
    for (const [word, flags] of fields) {
      let posting = building.get(word);
      if (!posting) {
        posting = [];
        building.set(word, posting);
      }
      posting.push(number * 16 + flags);
    }
  });
  const postings = new Map<string, Uint32Array>();
  for (const [word, rows] of building)
    postings.set(word, Uint32Array.from(rows));
  building.clear();
  return (
    tokens: string[],
    query: string,
    limit: number,
    subjects: string[],
  ): Entry[] => {
    const found = new Map<
      number,
      { hits: number; claims: number; specific: boolean; score: number }
    >();
    for (const token of tokens)
      for (const encoded of postings.get(token) || []) {
        const number = encoded >>> 4,
          flags = encoded & 15;
        if (subjects.length && !subjects.includes(entries[number].pillar))
          continue;
        let row = found.get(number);
        if (!row) {
          row = { hits: 0, claims: 0, specific: false, score: 0 };
          found.set(number, row);
        }
        row.hits++;
        row.claims += flags & 8 ? 1 : 0;
        row.specific ||= Boolean(flags & 5);
        row.score += flags & 1 ? 5 : 1;
      }
    const threshold = Math.max(
      Math.min(2, tokens.length),
      Math.ceil(tokens.length / 2),
    );
    return [...found]
      .filter(
        ([, row]) =>
          row.hits >= threshold &&
          (row.specific || (tokens.length > 1 && row.claims === tokens.length)),
      )
      .map(([number, row]) => ({
        entry: entries[number],
        score:
          row.score +
          (entries[number].title.toLowerCase().includes(query.toLowerCase())
            ? 8
            : 0),
      }))
      .sort(
        (a, b) =>
          b.score - a.score ||
          (a.entry.date.year ?? 9999) - (b.entry.date.year ?? 9999) ||
          a.entry.id.localeCompare(b.entry.id),
      )
      .slice(0, limit)
      .map((row) => row.entry);
  };
}
