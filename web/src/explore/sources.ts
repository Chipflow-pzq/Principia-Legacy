import { api, type Contribution } from "../types";
import { fetchJSON } from "./network";
import { object, safeURL, text, type ResearchSource } from "./model";

type Entry = Pick<
  Contribution,
  | "id"
  | "revision"
  | "content_hash"
  | "title"
  | "pillar"
  | "kind"
  | "claim"
  | "explanation"
  | "assumptions"
  | "limits"
  | "attribution"
  | "date"
> & { neighbors?: string[] };
type Index = {
  entries: Entry[];
  total: number;
  snapshot_hash: string;
  release_id: string;
};
let indexCache: Index | null = null;
export async function atlasIndex(
  release: string,
  signal: AbortSignal,
  progress: (loaded: number, total: number) => void = () => {},
): Promise<Index> {
  if (indexCache?.release_id === release) {
    progress(indexCache.entries.length, indexCache.total);
    return indexCache;
  }
  const first = await api<Index>(
    "exploration-index",
    { release, offset: 0, limit: 200 },
    signal,
  );
  if (first.total > 10000)
    throw new Error("The local index exceeds this explorer’s supported size.");
  const entries = [...first.entries];
  progress(entries.length, first.total);
  for (let offset = 200; offset < first.total; offset += 200) {
    signal.throwIfAborted();
    const page = await api<Index>(
      "exploration-index",
      { release, offset, limit: 200 },
      signal,
    );
    if (page.snapshot_hash !== first.snapshot_hash)
      throw new Error(
        "The atlas snapshot changed during loading. Please retry.",
      );
    entries.push(...page.entries);
    progress(entries.length, first.total);
  }
  indexCache = { ...first, entries };
  return indexCache;
}
export function localMatches(
  index: Index,
  query: string,
  limit = 8,
  subjects: string[] = [],
): ResearchSource[] {
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
  const words = (value: string) =>
    new Set((value.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) || []).map(stem));
  const tokens = [
    ...new Set(
      (query.toLowerCase().match(/[\p{L}\p{N}]{3,}/gu) || [])
        .filter((w) => !stop.has(w))
        .map(stem),
    ),
  ];
  const scored = index.entries
    .filter((entry) => !subjects.length || subjects.includes(entry.pillar))
    .map((entry) => {
      // Whole words avoid matches such as question-word "did" in "candidate".
      const title = words(entry.title),
        body = words(
          `${entry.claim} ${entry.explanation} ${entry.attribution.map((a) => a.name).join(" ")} ${entry.date.year ?? ""}`,
        );
      const hits = tokens.filter((t) => title.has(t) || body.has(t));
      const attribution = words(entry.attribution.map((a) => a.name).join(" "));
      const claim = words(entry.claim);
      return {
        entry,
        score:
          hits.reduce((s, t) => s + (title.has(t) ? 5 : 1), 0) +
          (entry.title.toLowerCase().includes(query.toLowerCase()) ? 8 : 0),
        hits: hits.length,
        specific:
          tokens.some((t) => title.has(t) || attribution.has(t)) ||
          (tokens.length > 1 && tokens.every((t) => claim.has(t))),
      };
    })
    .filter(
      (v) =>
        v.specific &&
        v.hits >=
          Math.max(Math.min(2, tokens.length), Math.ceil(tokens.length / 2)) &&
        v.score > 0,
    )
    .sort(
      (a, b) =>
        b.score - a.score ||
        (a.entry.date.year ?? 9999) - (b.entry.date.year ?? 9999) ||
        a.entry.id.localeCompare(b.entry.id),
    );
  return scored.slice(0, limit).map(({ entry }) => atlasSource(entry));
}
export function atlasSource(e: Entry): ResearchSource {
  return {
    id: `atlas_${e.id}`,
    title: e.title,
    authors: e.attribution.map((a) => a.name),
    year: e.date.year,
    kind: "atlas",
    passage:
      `${e.claim}\n${e.explanation}\nAssumptions: ${e.assumptions.join("; ")}\nLimitations: ${e.limits.join("; ")}`.slice(
        0,
        4000,
      ),
    url: "",
    atlas_id: e.id,
    revision: e.revision,
    content_hash: e.content_hash,
    atlas_kind: e.kind,
    retrieved_at: new Date().toISOString(),
  };
}

/** A small cross-subject catalog of existing principles, never generated evidence. */
export function foundationCatalog(index: Index) {
  const families = [
    /^Newton.s (?:first|second|third) law/i,
    /work.energy theorem/i,
    /conservation of (?:mechanical )?energy/i,
    /conservation of momentum/i,
    /(?:first|second) law (?:of|as)/i,
    /(?:entropy|energy) as/i,
    /Bayes.? (?:theorem|rule)|conditional probability/i,
    /information.*entropy|entropy.*information/i,
    /(?:Church.Turing|universal Turing|Turing machine)/i,
    /fundamental theorem of calculus|derivative as/i,
    /natural selection|heritable variation/i,
    /base.pair|complementary.*DNA|genetic code|central dogma/i,
    /(?:mass action|chemical equilibrium|activation energy)/i,
    /(?:comparative advantage|opportunity cost)/i,
    /(?:supply and demand|competitive equilibrium)/i,
  ];
  const candidates = families.flatMap((pattern) =>
    index.entries
      .filter(
        (e) =>
          pattern.test(e.title) && !/problem.solving|motivating/i.test(e.title),
      )
      .sort(
        (a, b) =>
          Number(a.kind === "empirical_finding") -
            Number(b.kind === "empirical_finding") ||
          a.title.length - b.title.length,
      )
      .slice(0, 2),
  );
  return [...new Map(candidates.map((e) => [e.id, e])).values()].map((e) => ({
    id: e.id,
    title: e.title,
    claim: e.claim.slice(0, 260),
    subject: e.pillar,
  }));
}
/** Follow public atlas adjacency locally, without sending research interests to the server. */
export function relatedMatches(
  index: Index,
  seeds: ResearchSource[],
  query: string,
  limit = 6,
): ResearchSource[] {
  const seedIds = new Set(seeds.map((s) => s.atlas_id));
  const candidates = new Set(
    index.entries
      .filter((e) => seedIds.has(e.id))
      .flatMap((e) => e.neighbors || []),
  );
  const words = query.toLowerCase().match(/[\p{L}\p{N}]{4,}/gu) || [];
  const score = (e: Entry) =>
    words.reduce(
      (n, w) =>
        n +
        Number(
          `${e.title} ${e.claim} ${e.explanation}`
            .toLowerCase()
            .includes(w.replace(/s$/, "")),
        ),
      0,
    );
  return index.entries
    .filter((e) => candidates.has(e.id) && !seedIds.has(e.id))
    .map((e) => ({ e, score: score(e) }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score || a.e.id.localeCompare(b.e.id))
    .slice(0, limit)
    .map(({ e }) => ({ ...atlasSource(e), search_group: "atlas connections" }));
}
function plain(value: unknown): string {
  // DOMParser is deliberately avoided: source markup cannot trigger image loads.
  return text(value, 16000)
    .replace(/<[^>]*>/g, " ")
    .replace(
      /&(lt|gt|amp|quot|apos);/g,
      (_, name: string) =>
        ({ lt: "<", gt: ">", amp: "&", quot: '"', apos: "'" })[name] || " ",
    )
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 4000);
}
function doi(value: unknown) {
  const d = text(value, 300);
  return /^10\.\d{4,9}\/\S+$/i.test(d) ? d.toLowerCase() : "";
}
/** Bibliographic search is noisy, especially for cross-field homonyms. */
export function rankLiterature(
  sources: ResearchSource[],
  query: string,
): ResearchSource[] {
  const generic = new Set([
    "the",
    "and",
    "for",
    "with",
    "from",
    "review",
    "fundamentals",
    "principles",
    "mechanism",
    "mechanisms",
    "physical",
    "theory",
  ]);
  const terms = [
    ...new Set(
      (
        query
          .toLowerCase()
          .replace(/vapour/g, "vapor")
          .match(/[\p{L}\p{N}]{3,}/gu) || []
      )
        .filter((t) => !generic.has(t))
        .map((t) => t.replace(/s$/, "")),
    ),
  ];
  if (!terms.length) return sources;
  return sources
    .map((s) => {
      const title = s.title.toLowerCase().replace(/vapour/g, "vapor");
      const body = `${title} ${s.passage.toLowerCase()}`;
      const matches = terms.filter((t) => body.includes(t));
      return {
        s,
        hits: matches.length,
        score: matches.reduce((n, t) => n + (title.includes(t) ? 3 : 1), 0),
      };
    })
    .filter((x) => x.hits >= Math.min(3, Math.ceil(terms.length / 2)))
    .sort((a, b) => b.score - a.score)
    .map((x) => x.s);
}
function fromCrossref(value: unknown): ResearchSource | null {
  const w = object(value),
    d = doi(w.DOI);
  if (!d) return null;
  const abstract = plain(w.abstract);
  // Some reference works deposit a license/citation notice as their abstract.
  // It is useful bibliographic metadata, but contains no inspectable definition.
  const passage =
    /^\s*(?:cite this|citation:|this entry (?:is|was) (?:from|published)|this (?:article|entry) (?:is )?licensed)/i.test(
      abstract,
    ) ||
    (/IUPAC Compendium of Chemical Terminology/i.test(abstract) &&
      /Creative Commons|licensed|ISBN|https?:/i.test(abstract) &&
      abstract.length < 1200)
      ? ""
      : abstract;
  const dates = object(w.published)["date-parts"];
  const year =
    Array.isArray(dates) && Array.isArray(dates[0])
      ? Number(dates[0][0])
      : null;
  return {
    id: "",
    title: plain(Array.isArray(w.title) ? w.title[0] : ""),
    url: `https://doi.org/${encodeURI(d)}`,
    authors: (Array.isArray(w.author) ? w.author : []).slice(0, 30).map((a) => {
      const p = object(a);
      return `${text(p.given, 80)} ${text(p.family, 80)}`.trim();
    }),
    year: Number.isInteger(year) ? year : null,
    kind: passage ? "abstract" : "metadata",
    passage,
    doi: d,
    references: (Array.isArray(w.reference) ? w.reference : [])
      .map((r) => doi(object(r).DOI))
      .filter(Boolean)
      .slice(0, 15),
    retrieved_at: new Date().toISOString(),
  };
}
export function fromEuropePMC(value: unknown): ResearchSource | null {
  const w = object(value),
    d = doi(w.doi),
    pmid = text(w.pmid, 40),
    source = text(w.source, 10),
    id = text(w.id, 60);
  const url = d
    ? `https://doi.org/${encodeURI(d)}`
    : pmid && /^\d+$/.test(pmid)
      ? `https://europepmc.org/article/MED/${pmid}`
      : /^[A-Z]+$/.test(source) && /^[\w.-]+$/.test(id)
        ? `https://europepmc.org/article/${source}/${id}`
        : "";
  if (!safeURL(url)) return null;
  const passage = plain(w.abstractText);
  return {
    id: "",
    title: plain(w.title),
    url,
    doi: d || undefined,
    ...(/^PMC[0-9]+$/.test(String(w.pmcid)) ? { pmcid: String(w.pmcid) } : {}),
    authors: text(w.authorString, 2000).split(", ").slice(0, 30),
    year: /^\d{4}$/.test(String(w.pubYear)) ? Number(w.pubYear) : null,
    kind: passage ? "abstract" : "metadata",
    passage,
    retrieved_at: new Date().toISOString(),
  };
}
export async function searchLiterature(
  query: string,
  signal: AbortSignal,
  progress: (service: string, found: ResearchSource[]) => void = () => {},
): Promise<{ sources: ResearchSource[]; gaps: string[] }> {
  // Rank bibliographic matches with inspectable abstracts; a metadata-only
  // first page should not crowd older explanatory papers out of the source pool.
  const crossref = new URLSearchParams({
    "query.bibliographic": query,
    filter: "has-abstract:true",
    rows: "10",
  });
  const pmc = new URLSearchParams({
    query,
    format: "json",
    pageSize: "7",
    resultType: "core",
  });
  const tasks = [
    fetchJSON(`https://api.crossref.org/works?${crossref}`, {}, signal).then(
      (v) => {
        const m = object(object(v).message);
        const found = (Array.isArray(m.items) ? m.items : [])
          .map(fromCrossref)
          .filter((s): s is ResearchSource => !!s);
        progress("Crossref", found);
        return found;
      },
    ),
    fetchJSON(
      `https://www.ebi.ac.uk/europepmc/webservices/rest/search?${pmc}`,
      {},
      signal,
    ).then((v) => {
      const m = object(object(v).resultList);
      const found = (Array.isArray(m.result) ? m.result : [])
        .map(fromEuropePMC)
        .filter((s): s is ResearchSource => !!s);
      progress("Europe PMC", found);
      return found;
    }),
  ];
  const results = await Promise.allSettled(tasks),
    sources: ResearchSource[] = [],
    gaps: string[] = [];
  signal.throwIfAborted();
  results.forEach((r, i) => {
    if (r.status === "fulfilled")
      sources.push(...r.value.filter((s): s is ResearchSource => !!s));
    else
      gaps.push(
        `${i ? "Europe PMC" : "Crossref"} could not be searched for “${query}”. No evidence was inferred from the missing response.`,
      );
  });
  return { sources, gaps };
}
export async function referenceSources(
  references: string[],
  signal: AbortSignal,
  progress: (source: ResearchSource | null) => void = () => {},
) {
  const found: ResearchSource[] = [];
  const pending = [...new Set(references.map(doi).filter(Boolean))].slice(0, 4);
  async function worker() {
    while (pending.length) {
      const d = pending.shift()!;
      try {
        const result = await fetchJSON(
          `https://api.crossref.org/works/${encodeURIComponent(d)}`,
          {},
          signal,
        );
        const source = fromCrossref(object(result).message);
        if (source) found.push(source);
        progress(source);
      } catch {
        signal.throwIfAborted();
        progress(null);
      }
    }
  }
  await Promise.all([worker(), worker()]);
  return found;
}
export function mergeSources(
  previous: ResearchSource[],
  incoming: ResearchSource[],
): ResearchSource[] {
  const all = previous.map((s) => ({ ...s }));
  let sequence = Math.max(
    0,
    ...all.map((s) => Number(s.id.match(/^source_(\d+)$/)?.[1]) || 0),
  );
  for (const s of incoming) {
    const existing = all.find((x) =>
      s.atlas_id
        ? x.atlas_id === s.atlas_id
        : (s.doi && x.doi === s.doi) || x.url === s.url,
    );
    if (existing) {
      // Before drafting, a targeted explanatory lookup can improve the passage
      // and category of an initial broad overview without changing its identity.
      if (s.kind === "reference_excerpt") {
        existing.passage = s.passage;
        existing.search_group = s.search_group;
      }
      if (s.pmcid) existing.pmcid = s.pmcid;
      if (s.license) existing.license = s.license;
      if (s.passage && (!existing.passage || s.kind === "article_excerpt")) {
        existing.passage = s.passage;
        existing.kind = s.kind;
        if (s.kind === "article_excerpt")
          existing.search_group = s.search_group;
      }
      existing.references = [
        ...new Set([...(existing.references || []), ...(s.references || [])]),
      ];
    } else {
      const entry = { ...s, id: s.id || `source_${++sequence}` };
      if (all.length < 60) all.push(entry);
      else if (s.passage) {
        // Later searches for alternatives must not lose their passages to a
        // full pool of metadata-only records from the first search.
        let replace = all.length - 1;
        while (replace >= 0 && all[replace].passage) replace--;
        if (replace < 0 && s.kind === "atlas") {
          // A foundation found in a follow-up must not be crowded out by a
          // full first page of paper abstracts. No draft exists at this stage.
          replace = all
            .map((existing) => existing.kind !== "atlas")
            .lastIndexOf(true);
        }
        if (replace < 0 && s.search_group) {
          const counts = new Map<string, number>();
          for (const old of all) {
            const key = old.search_group || "initial";
            counts.set(key, (counts.get(key) || 0) + 1);
          }
          if ((counts.get(s.search_group) || 0) < 4)
            replace = all
              .map(
                (old) =>
                  old.kind !== "atlas" &&
                  (counts.get(old.search_group || "initial") || 0) > 4,
              )
              .lastIndexOf(true);
        }
        if (
          replace < 0 &&
          ["article_excerpt", "reference_excerpt"].includes(s.kind)
        ) {
          // Successfully acquired full explanations outrank a crowded pool of
          // abstracts. Otherwise a later study can disappear without any gap,
          // despite having been downloaded and passed the rights check.
          replace = all
            .map((old) => old.kind === "abstract" || old.kind === "metadata")
            .lastIndexOf(true);
        }
        if (replace >= 0) all[replace] = entry;
      }
    }
  }
  return all;
}
