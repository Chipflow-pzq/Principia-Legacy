import { fetchJSON, fetchText } from "./network";
import { object, safeURL, type ResearchSource } from "./model";
import { fromEuropePMC, rankLiterature } from "./sources";

const ROOT = "https://www.ebi.ac.uk/europepmc/webservices/rest/";
const licensePattern =
  /^https?:\/\/(?:www\.)?creativecommons\.org\/(?:licenses\/by\/|publicdomain\/zero\/)\d\.\d\/?$/i;

/** Keep a directly relevant study alongside explanatory reviews. A review
 * preference must not consume every full-text slot and exclude the result itself. */
export function articleCandidates(sources: ResearchSource[], topic: string) {
  const ranked = rankLiterature(sources, topic);
  const isReview = (s: ResearchSource) =>
    /\breview\b|overview|fundamentals/i.test(s.title);
  const direct = ranked.find((s) => !isReview(s));
  const reviews = ranked.filter(isReview);
  return [
    ...new Map(
      [...(direct ? [direct] : []), ...reviews, ...ranked].map((s) => [
        s.pmcid,
        s,
      ]),
    ).values(),
  ].slice(0, 3);
}

/** Inert XML only. No HTML insertion, external entities, scripts, images or source-supplied requests. */
export function articlePassages(
  xml: string,
  question: string,
  concepts: string[] = [],
): { passage: string; license: string } | null {
  if (/<!ENTITY\b/i.test(xml)) return null;
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  if (doc.querySelector("parsererror")) return null;
  const license = [
    ...doc.querySelectorAll("article-meta permissions license ext-link"),
  ]
    .map(
      (n) =>
        n.getAttribute("xlink:href") ||
        n.getAttribute("href") ||
        n.textContent ||
        "",
    )
    .find((url) => licensePattern.test(url));
  if (!license) return null;
  const terms = [
    ...new Set(
      (
        question
          .toLowerCase()
          .replace(/vapour/g, "vapor")
          .match(/[\p{L}\p{N}]{4,}/gu) || []
      ).filter(
        (w) =>
          ![
            "with",
            "from",
            "that",
            "this",
            "review",
            "principles",
            "fundamentals",
          ].includes(w),
      ),
    ),
  ];
  const conceptsWords = [
    ...new Set(
      concepts
        .join(" ")
        .toLowerCase()
        .match(/[\p{L}\p{N}]{4,}/gu) || [],
    ),
  ].filter(
    (w) =>
      !terms.includes(w) &&
      ![
        "with",
        "from",
        "that",
        "this",
        "which",
        "into",
        "using",
        "used",
        "their",
        "these",
      ].includes(w),
  );
  const candidates = [...doc.querySelectorAll("body p")]
    .filter((p) => !p.closest("fig, table-wrap, ref-list"))
    .slice(0, 300)
    .map((p, i) => {
      // Keep paragraph wording and document order; do not splice a synthetic quotation.
      const value = (p.textContent || "").replace(/\s+/g, " ").trim();
      const lower = value.toLowerCase().replace(/vapour/g, "vapor");
      const hits = terms.filter((t) => lower.includes(t)).length;
      const heading =
        p.closest("sec")?.querySelector("title")?.textContent || "";
      return {
        value,
        i,
        hits,
        lower,
        concepts: conceptsWords.filter((t) => lower.includes(t)),
        orientation: /introduct|background|principle|mechanism/i.test(heading)
          ? 1
          : 0,
      };
    });
  const weights = new Map(
    conceptsWords.map((term) => [
      term,
      1 +
        Math.log(
          1 +
            candidates.length /
              Math.max(
                1,
                candidates.filter((p) => p.lower.includes(term)).length,
              ),
        ),
    ]),
  );
  // Methods often explain an operation without repeating the paper's title or
  // product name. Retain concept-rich paragraphs as well as branded overviews;
  // rare route vocabulary is more useful than repeated generic topic words.
  const paragraphs = candidates
    .filter(
      (p) =>
        p.value.length >= 80 &&
        (p.hits >= Math.min(2, terms.length) ||
          (conceptsWords.length > 0 &&
            p.concepts.length >= Math.min(2, conceptsWords.length))),
    )
    .map((p) => ({
      ...p,
      score:
        p.hits * 2 +
        p.orientation +
        p.concepts.reduce((sum, t) => sum + (weights.get(t) || 1), 0),
    }));
  const selected = new Set<number>();
  let size = 0;
  for (const p of [...paragraphs].sort(
    (a, b) => b.score - a.score || a.i - b.i,
  )) {
    if (size + p.value.length > 6400) continue;
    selected.add(p.i);
    size += p.value.length;
    if (selected.size >= 10) break;
  }
  const passage = paragraphs
    .filter((p) => selected.has(p.i))
    .map((p) => p.value)
    .join("\n\n");
  return passage
    ? { passage, license: safeURL(license.replace(/^http:/i, "https:")) }
    : null;
}

/** At most three openly licensed articles, fetched directly by the user's browser. */
export async function explanatoryArticles(
  topic: string,
  concepts: string[],
  signal: AbortSignal,
  progress: (detail: string) => void = () => {},
  question = topic,
  existing: ResearchSource[] = [],
): Promise<{ sources: ResearchSource[]; gaps: string[] }> {
  const sources: ResearchSource[] = [],
    gaps: string[] = [];
  const safeTopic = topic
    .replace(/["()\[\]{}:]/g, " ")
    .trim()
    .slice(0, 120);
  const query = `TITLE_ABS:("${safeTopic}") AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") sort_cited:y`;
  try {
    const raw = object(
      await fetchJSON(
        `${ROOT}search?${new URLSearchParams({ query, format: "json", resultType: "core", pageSize: "12" })}`,
        {},
        signal,
        15000,
      ),
    );
    const list = object(raw.resultList).result;
    const candidates = articleCandidates(
      [
        ...new Map(
          [
            ...(Array.isArray(list) ? list : [])
              .map(fromEuropePMC)
              .filter((s): s is ResearchSource => !!s?.pmcid),
            ...existing.filter((s) => /^PMC[0-9]+$/.test(s.pmcid || "")),
          ].map((s) => [s.pmcid, s]),
        ).values(),
      ],
      topic,
    );
    await Promise.all(
      candidates.map(async (s, index) => {
        try {
          const xml = await fetchText(
            `${ROOT}${s.pmcid}/fullTextXML`,
            {},
            signal,
            15000,
          );
          const extracted = articlePassages(
            xml,
            `${topic} ${question}`,
            concepts,
          );
          if (!extracted) {
            gaps.push(
              `No reusable explanatory passage was available from “${s.title}”; its abstract remains the available evidence.`,
            );
            return;
          }
          sources.push({
            ...s,
            ...extracted,
            kind: "article_excerpt",
            search_group:
              index === 0 && !/\breview\b|overview|fundamentals/i.test(s.title)
                ? "selected study"
                : "explanatory articles",
          });
          progress(`Read explanatory passages: ${s.title}`);
        } catch {
          signal.throwIfAborted();
          gaps.push(
            `The open-access text of “${s.title}” was unavailable. No evidence was inferred from it.`,
          );
        }
      }),
    );
    if (!candidates.length)
      gaps.push(
        "No matching openly licensed explanatory article was found in Europe PMC.",
      );
  } catch {
    signal.throwIfAborted();
    gaps.push(
      "The search for open-access explanatory articles was unavailable; only other retrieved evidence was used.",
    );
  }
  return { sources, gaps };
}
