import { fetchJSON } from "./network";
import { object, text, type ResearchSource } from "./model";
import { sourceCautions } from "./sourceQuality";

const API = "https://en.wikipedia.org/w/api.php";
const LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/";

/** Select complete paragraphs, retaining their wording and original order. */
export function referencePassages(
  extract: string,
  concepts: string[],
  limit = 7000,
) {
  const terms = [
    ...new Set(
      concepts
        .join(" ")
        .toLowerCase()
        .match(/[\p{L}\p{N}]{4,}/gu) || [],
    ),
  ];
  const paragraphs = extract
    .replace(/^\s*={2,}[^\n]*={2,}\s*$/gm, "\n\n")
    .split(/\n\s*\n/)
    .map((value, i) => ({
      value: value.replace(/\s+/g, " ").trim(),
      i,
    }))
    .filter((p) => p.value.length >= 60 && !/^==/.test(p.value));
  const weights = terms.map((term) => ({
    term,
    weight:
      1 +
      Math.log(
        1 +
          paragraphs.length /
            Math.max(
              1,
              paragraphs.filter((p) => p.value.toLowerCase().includes(term))
                .length,
            ),
      ),
  }));
  const ranked = paragraphs.map((p) => ({
    ...p,
    score:
      (p.i === 0 ? 6 : p.i < 3 ? 2 : 0) +
      weights.reduce(
        (score, { term, weight }) =>
          score + (p.value.toLowerCase().includes(term) ? weight : 0),
        0,
      ),
  }));
  const chosen = new Set<number>();
  let size = 0;
  for (const p of ranked.sort((a, b) => b.score - a.score || a.i - b.i)) {
    if (size + p.value.length + 2 > limit) continue;
    chosen.add(p.i);
    size += p.value.length + 2;
  }
  return paragraphs
    .filter((p) => chosen.has(p.i))
    .map((p) => p.value)
    .join("\n\n");
}

/** General reference works complement specialized papers; they are explicitly secondary evidence. */
export async function referenceExplanations(
  topic: string,
  foundations: string[],
  signal: AbortSignal,
  mechanism = "",
  question = topic,
  explanatoryConcepts: string[] = [],
  context: { endpoint?: string; subjects?: string[] } = {},
): Promise<{ sources: ResearchSource[]; gaps: string[] }> {
  const sources: ResearchSource[] = [],
    gaps: string[] = [];
  // The technology, an enabling mechanism, proposed general foundations and,
  // when different, the user's qualified request. All requests go directly
  // to a fixed public API; neither the atlas server nor source URLs receive them.
  const proposedRoots = [...new Set(foundations.filter(Boolean))].slice(0, 5);
  // A plan may name a broad field as topic while giving the precise technology
  // in its endpoint heading. Retrieve both; never discard the user's qualifier.
  // This is an additional search hypothesis, not evidence of equivalence.
  const heading = context.endpoint?.includes(":")
    ? context.endpoint
        .split(":", 1)[0]
        .trim()
        .replace(/\s*\([^)]*\)\s*$/, "")
    : "";
  const preciseTopic =
    heading && heading.length <= 120 && heading.split(/\s+/).length <= 12
      ? heading
      : "";
  const normalize = (value: string) => value.trim().toLowerCase();
  const alreadyPlanned = new Set(
    [topic, mechanism, ...proposedRoots].map(normalize),
  );
  // A plan can name useful intermediate operations but nominate a very early
  // mechanism. Fetch those operations too, within the existing eight-lookups
  // budget. Search hypotheses never become graph links without evidence.
  const bridges = [...new Set(explanatoryConcepts.slice(1, -1).reverse())]
    .filter((s) => s && !alreadyPlanned.has(normalize(s)))
    .slice(0, 2);
  const roots = proposedRoots.slice(0, bridges.length ? 3 : 5);
  // A normalized name must not erase a company, material or other qualifier.
  const tokens = (value: string) =>
    value
      .toLowerCase()
      .replace(/vapour/g, "vapor")
      .match(/[\p{L}\p{N}]{3,}/gu)
      ?.map((w) => w.replace(/s$/, "")) || [];
  const topicWords = new Set(tokens(topic));
  const stop = new Set([
    "the",
    "and",
    "for",
    "how",
    "what",
    "why",
    "doe",
    "can",
    "please",
    "explain",
    "trace",
    "history",
    "origin",
    "thi",
    "that",
  ]);
  const overview = tokens(question).some(
    (w) => !stop.has(w) && !topicWords.has(w),
  )
    ? question
    : topic;
  // A search for a product may return its manufacturer rather than an explanation
  // of the technology. Always retrieve the canonical overview as well; an entity
  // qualifier remains an additional source, never a replacement for that overview.
  const searches = [
    ...new Set(
      // Reserve the original qualified request before optional bridge lookups.
      [preciseTopic, topic, mechanism, ...roots, overview, ...bridges].filter(
        Boolean,
      ),
    ),
  ].slice(0, 8);
  const retrieve = async (query: string) => {
    const deadline = Date.now() + 20_000;
    const lookup = async (params: URLSearchParams) => {
      const remaining = deadline - Date.now();
      if (remaining <= 0) throw new Error("Reference lookup time limit");
      return object(
        await fetchJSON(
          `${API}?${params}`,
          {},
          signal,
          Math.min(15000, remaining),
          500_000,
        ),
      );
    };
    const disambiguation = (page: unknown) =>
      Object.hasOwn(object(object(page).pageprops), "disambiguation");
    const hasText = (pages: unknown) =>
      Array.isArray(pages) &&
      pages.some(
        (p) =>
          Number(object(p).pageid) > 0 &&
          object(p).extract &&
          !disambiguation(p),
      );
    let pages: unknown;
    // A planner can return a descriptive mechanism rather than an article title.
    // A short search fallback is only a retrieval hypothesis; the resulting
    // passages must still establish the original claim and scope.
    const meaningful = query
      .split(/\s+/)
      .filter((w) => !stop.has(w.toLowerCase()));
    const alternatives = [
      query,
      ...(query === mechanism && meaningful.length > 4
        ? [meaningful.slice(0, 4).join(" ")]
        : []),
    ];
    for (const title of alternatives) {
      const params = new URLSearchParams({
        action: "query",
        titles: title.slice(0, 180),
        redirects: "1",
        prop: "extracts|revisions|pageprops",
        ppprop: "disambiguation",
        exlimit: "1",
        // Fetch bounded plaintext, then select complete explanatory paragraphs.
        explaintext: "1",
        rvprop: "ids|timestamp",
        format: "json",
        formatversion: "2",
        origin: "*",
      });
      let raw = await lookup(params);
      pages = object(raw.query).pages;
      if (!hasText(pages)) {
        const ambiguous = Array.isArray(pages) && pages.some(disambiguation);
        params.delete("titles");
        params.delete("redirects");
        params.set("generator", "search");
        params.set("gsrlimit", "1");
        params.set("gsrnamespace", "0");
        const searchContext =
          (context.subjects || []).map((s) => s.replace(/_/g, " ")).join(" ") ||
          preciseTopic ||
          topic;
        params.set(
          "gsrsearch",
          `${title.replace(/[-–—]/g, " ")}${ambiguous ? " " + searchContext : ""}`.slice(
            0,
            180,
          ),
        );
        raw = await lookup(params);
        pages = object(raw.query).pages;
      }
      if (hasText(pages)) break;
    }
    return (Array.isArray(pages) ? pages : []).flatMap((value) => {
      if (disambiguation(value)) {
        gaps.push(
          `The reference “${text(object(value).title, 240)}” is a disambiguation page, not an explanation; it was withheld.`,
        );
        return [];
      }
      const page = object(value),
        revision = object(
          Array.isArray(page.revisions) ? page.revisions[0] : {},
        );
      const id = Number(page.pageid),
        rev = Number(revision.revid);
      const title = text(page.title, 240);
      if (
        !Number.isSafeInteger(id) ||
        id <= 0 ||
        !Number.isSafeInteger(rev) ||
        rev <= 0 ||
        !title
      )
        return [];
      const sourceId = `reference_${id}_${rev}`;
      const conflict = sourceCautions([{ id: sourceId }])[0];
      if (conflict) {
        gaps.push(
          `A known conflicting reference revision was withheld: ${conflict.title}. ${conflict.finding} Comparison: ${conflict.comparisonUrl}`,
        );
        return [];
      }
      const passage = referencePassages(
        typeof page.extract === "string" ? page.extract : "",
        [topic, question, mechanism, ...foundations, ...explanatoryConcepts],
        query === topic || query === preciseTopic || query === mechanism
          ? 5000
          : roots.includes(query) || bridges.includes(query)
            ? 2400
            : 2000,
      );
      if (!passage) return [];
      return [
        {
          id: sourceId,
          title,
          authors: ["Wikipedia contributors"],
          year: null,
          kind: "reference_excerpt" as const,
          passage,
          url: `https://en.wikipedia.org/w/index.php?oldid=${rev}`,
          license: LICENSE,
          retrieved_at: new Date().toISOString(),
          search_group:
            query === topic || query === preciseTopic
              ? "technology overview"
              : query === mechanism
                ? "mechanism reference"
                : roots.includes(query)
                  ? "foundational reference"
                  : bridges.includes(query)
                    ? "enabling reference"
                    : "requested context",
        },
      ];
    });
  };
  // Keep source acquisition at four in flight, including when several distinct
  // foundational laws are needed. Each lookup has its own shared time bound.
  const responses: PromiseSettledResult<ResearchSource[]>[] = new Array(
    searches.length,
  );
  let next = 0;
  await Promise.all(
    Array.from({ length: Math.min(4, searches.length) }, async () => {
      while (next < searches.length) {
        const i = next++;
        try {
          responses[i] = {
            status: "fulfilled",
            value: await retrieve(searches[i]),
          };
        } catch (reason) {
          responses[i] = { status: "rejected", reason };
        }
      }
    }),
  );
  signal.throwIfAborted();
  responses.forEach((r, i) => {
    if (r.status === "fulfilled") {
      sources.push(...r.value);
      if (!r.value.length)
        gaps.push(
          `No usable general reference explanation was found for “${searches[i]}”.`,
        );
    } else
      gaps.push(
        `The general reference search for “${searches[i]}” was unavailable. No evidence was inferred from it.`,
      );
  });
  // Searches are ordered by explanatory priority. An alias or a qualified
  // context lookup must not replace the canonical overview's longer passage
  // and category merely because both returned the same article revision.
  const unique = new Map<string, ResearchSource>();
  for (const source of sources)
    if (!unique.has(source.id)) unique.set(source.id, source);
  return { sources: [...unique.values()], gaps };
}
