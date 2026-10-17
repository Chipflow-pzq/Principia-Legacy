import { test, expect } from "@playwright/test";
import { build } from "vite";
import { resolve } from "node:path";
import { articleCandidates } from "../src/explore/articles";
import { packet } from "../src/explore/agent";
import { mergeSources } from "../src/explore/sources";
import type { ResearchSource } from "../src/explore/model";

test("reviews cannot crowd the direct study out of full-text acquisition or the evidence packet", () => {
  const source = (id: string, title: string): ResearchSource => ({
    id,
    title,
    pmcid: `PMC${id}`,
    passage: "Synthetic study mechanism evidence. ".repeat(180),
    authors: [],
    year: 2020,
    kind: "abstract",
    url: "https://example.org",
    retrieved_at: "fixture",
  });
  const direct = source(
    "123",
    "Accurate structure prediction with a synthetic system",
  );
  const reviews = [1, 2, 3].map((i) =>
    source(String(i), `Structure prediction overview ${i}`),
  );
  const candidates = articleCandidates(
    [...reviews, direct],
    "structure prediction",
  );
  expect(candidates).toHaveLength(3);
  expect(candidates[0].id).toBe(direct.id);
  const references = Array.from({ length: 8 }, (_, i) => ({
    ...source(`r${i}`, "Structure prediction reference"),
    kind: "reference_excerpt" as const,
    search_group: i === 0 ? "technology overview" : "mechanism reference",
  }));
  const selected = packet(
    [
      ...references,
      { ...direct, kind: "article_excerpt", search_group: "selected study" },
    ],
    "structure prediction",
  );
  expect(
    selected.find((s) => s.id === direct.id)?.excerpts.length,
  ).toBeGreaterThan(20);
  expect(
    selected.reduce(
      (sum, s) => sum + s.excerpts.reduce((n, e) => n + e.quote.length, 0),
      0,
    ),
  ).toBeLessThanOrEqual(24000);
});

test("a full source pool retains a newly read study and keeps its priority when an abstract is upgraded", () => {
  const pool: ResearchSource[] = Array.from({ length: 60 }, (_, i) => ({
    id: `source_${i + 1}`,
    title: `Earlier abstract ${i}`,
    url: `https://example.org/${i}`,
    authors: [],
    year: null,
    kind: "abstract",
    passage: "An inspectable synthetic abstract.",
    search_group: `distinct search ${i}`,
    retrieved_at: "fixture",
  }));
  const study: ResearchSource = {
    ...pool[0],
    id: "",
    url: "https://example.org/study",
    title: "Direct study",
    kind: "article_excerpt",
    passage: "A full synthetic mechanism explanation.",
    search_group: "selected study",
  };
  const merged = mergeSources(pool, [study]);
  expect(merged).toHaveLength(60);
  expect(merged.find((s) => s.url === study.url)).toMatchObject({
    kind: "article_excerpt",
    search_group: "selected study",
    passage: study.passage,
  });
  expect(pool.every((s) => s.kind === "abstract")).toBe(true);
  const upgraded = mergeSources(pool, [{ ...study, url: pool[0].url }]);
  expect(upgraded[0]).toMatchObject({
    id: "source_1",
    kind: "article_excerpt",
    search_group: "selected study",
  });
  const later = mergeSources(upgraded, [pool[0]]);
  expect(later[0].passage).toBe(study.passage);
  expect(later[0].kind).toBe("article_excerpt");
});

const built = await build({
  configFile: false,
  logLevel: "silent",
  build: {
    write: false,
    minify: false,
    lib: {
      entry: resolve("src/explore/articles.ts"),
      name: "ArticleTest",
      formats: ["iife"],
    },
  },
});
const bundle = (Array.isArray(built) ? built[0] : (built as any)).output.find(
  (o: any) => o.type === "chunk",
).code;
const paragraph =
  "Plasma generated in an electric field contains energetic electrons. Their collisions activate precursor molecules while the substrate can remain cooler than in a thermal deposition process.";
const xml = (license = "https://creativecommons.org/licenses/by/4.0/") =>
  `<?xml version="1.0"?><article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta><permissions><license><ext-link xlink:href="${license}">License</ext-link></license></permissions></article-meta></front><body><sec><title>Mechanism</title><p>${paragraph}</p></sec></body></article>`;

test("open-access extraction preserves wording and license without executing source markup", async ({
  page,
}) => {
  const requests: string[] = [];
  await page.route("**/*", (r) => {
    requests.push(r.request().url());
    return r.abort();
  });
  await page.addScriptTag({ content: bundle });
  const result = await page.evaluate(
    ({ source }) =>
      (window as any).ArticleTest.articlePassages(
        source,
        "plasma deposition electron collision",
      ),
    { source: xml() },
  );
  expect(result).toEqual({
    passage: paragraph,
    license: "https://creativecommons.org/licenses/by/4.0/",
  });
  const denied = await page.evaluate(
    ({ source }) =>
      (window as any).ArticleTest.articlePassages(source, "plasma deposition"),
    { source: xml("https://creativecommons.org/licenses/by-nc-nd/4.0/") },
  );
  expect(denied).toBeNull();
  const entity = await page.evaluate(
    ({ source }) =>
      (window as any).ArticleTest.articlePassages(source, "plasma"),
    {
      source:
        '<!DOCTYPE article [<!ENTITY external SYSTEM "https://example.org/private">]>' +
        xml(),
    },
  );
  expect(entity).toBeNull();
  expect(requests).toEqual([]);
});

test("method passages need not repeat the study's product name", async ({
  page,
}) => {
  await page.addScriptTag({ content: bundle });
  const method =
    "Electron collisions transfer energy to precursor molecules and create reactive species. The reaction then proceeds at the substrate surface while the bulk gas remains cooler.";
  const result = await page.evaluate(
    ({ source, method }) =>
      (window as any).ArticleTest.articlePassages(
        source.replace("</sec>", `<p>${method}</p></sec>`),
        "Plasma",
        ["electron collisions", "reaction kinetics"],
      ),
    { source: xml(), method },
  );
  expect(result.passage).toContain(method);
  expect(result.passage.length).toBeLessThanOrEqual(6400);
});

test("explanatory article acquisition uses only fixed PMC destinations and bounded excerpts", async ({
  page,
}) => {
  const requests: string[] = [];
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    requests.push(url.href);
    expect(url.origin).toBe("https://www.ebi.ac.uk");
    if (url.pathname.endsWith("/search"))
      return route.fulfill({
        headers: { "Access-Control-Allow-Origin": "*" },
        json: {
          resultList: {
            result: [
              {
                title: "Plasma deposition mechanisms review",
                doi: "10.1000/fixture",
                pmcid: "PMC123",
                abstractText: paragraph,
                authorString: "Synthetic fixture",
                pubYear: "2020",
              },
              {
                title: "Plasma deposition",
                doi: "10.1000/unsafe",
                pmcid: "https://example.org/injected",
                abstractText: paragraph,
              },
            ],
          },
        },
      });
    expect(url.pathname).toBe("/europepmc/webservices/rest/PMC123/fullTextXML");
    return route.fulfill({
      headers: { "Access-Control-Allow-Origin": "*" },
      contentType: "application/xml",
      body: xml(),
    });
  });
  await page.addScriptTag({ content: bundle });
  const result = await page.evaluate(() =>
    (window as any).ArticleTest.explanatoryArticles(
      "plasma deposition",
      ["electron collision"],
      new AbortController().signal,
    ),
  );
  expect(result.sources).toHaveLength(1);
  expect(result.sources[0]).toMatchObject({
    kind: "article_excerpt",
    pmcid: "PMC123",
    passage: paragraph,
  });
  expect(requests).toHaveLength(2);
  expect(result.gaps).toEqual([]);
});
