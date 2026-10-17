import type { Contribution, Info, Relation } from "../types";
import { excerpts } from "./excerpts";

export type Evidence = { source: string; quote: string };
export type ResearchSource = {
  id: string;
  title: string;
  url: string;
  authors: string[];
  year: number | null;
  kind:
    "abstract" | "metadata" | "atlas" | "article_excerpt" | "reference_excerpt";
  pmcid?: string;
  license?: string;
  passage: string;
  retrieved_at: string;
  doi?: string;
  references?: string[];
  atlas_id?: string;
  revision?: number;
  content_hash?: string;
  atlas_kind?: string;
  search_group?: string;
};
export type Insight = {
  id: string;
  title: string;
  claim: string;
  problem: string;
  move: string;
  explanation: string;
  assumptions: string[];
  limitations: string[];
  attribution: string[];
  year: number | null;
  subject: string;
  kind: string;
  evidence: Evidence[];
  role?: "foundation" | "bridge" | "frontier" | "limitation";
};
export type Connection = {
  id: string;
  premises: string[];
  conclusion: string;
  predicate: string;
  layer: string;
  warrant: string;
  scope: string;
  evidence: Evidence[];
  basis?: "documented" | "synthesis" | "teaching";
  steps?: string[];
};
export type Receipt = {
  stage: string;
  model: string;
  started_at: string;
  outcome: "completed" | "failed" | "cancelled";
  input_hash: string;
  prompt_hash: string;
  input_tokens: number | null;
  output_tokens: number | null;
  elapsed_ms?: number;
  first_content_ms?: number | null;
  output_characters?: number;
  response_bytes?: number;
  stream_events?: number;
  reasoning_characters?: number;
  thinking_disabled?: boolean;
  thinking_budget?: number;
  response_format?: "json_schema" | "json_object" | "text";
};
export type Exploration = {
  format: "principia-exploration/v1";
  id: string;
  title: string;
  query: string;
  summary: string;
  created_at: string;
  atlas_release: string;
  snapshot_hash: string;
  model: string;
  status: "unverified_draft";
  action_scope: "read_only";
  completion?: "partial" | "complete";
  check_status?: "not_started" | "incomplete" | "completed" | "not_recorded";
  nodes: Insight[];
  relations: Connection[];
  sources: ResearchSource[];
  gaps: string[];
  receipts: Receipt[];
};
export type Registry = Info["predicates"];
export const subjects = [
  "mathematics",
  "physics",
  "computer_science",
  "economics",
  "biology_medicine",
];
export const operationalKinds = ["method", "mechanism", "representation"];
export const insightKinds = [
  "theorem",
  "argument",
  "empirical_finding",
  "negative_result",
  "method",
  "mechanism",
  "representation",
  "heuristic",
  "conjecture",
  "question",
  "normative_argument",
];
const idPattern = /^[a-zA-Z0-9_-]{1,100}$/;
export function text(value: unknown, max = 3000): string {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}
export function strings(value: unknown, max = 12): string[] {
  return Array.isArray(value)
    ? value
        .slice(0, max)
        .map((v) => text(v, 1200))
        .filter(Boolean)
    : [];
}
export function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}
const normalize = (value: string) => value.replace(/\s+/g, " ").trim();
export function safeURL(value: string): string {
  try {
    const url = new URL(value);
    if (
      url.protocol !== "https:" ||
      url.username ||
      url.password ||
      url.port ||
      !url.hostname.includes(".") ||
      /(?:^|\.)(?:localhost|local|internal|test)$/.test(url.hostname) ||
      /^[\d.]+$/.test(url.hostname) ||
      url.hostname.includes(":")
    )
      return "";
    return url.href;
  } catch {
    return "";
  }
}
function evidence(
  value: unknown,
  sources: ResearchSource[],
  recoverReferenceIds = false,
): Evidence[] {
  if (!Array.isArray(value)) return [];
  const result: Evidence[] = [];
  for (const raw of value.slice(0, 5)) {
    const e = object(raw);
    let source = sources.find((s) => s.id === e.source);
    // Some generated citations omit only the reference revision. Recover that
    // exact page identity only when this retrieval contains ONE version. Never
    // fuzzy-match titles, select between revisions, or repair imported maps.
    if (
      !source &&
      recoverReferenceIds &&
      typeof e.source === "string" &&
      /^reference_\d+$/.test(e.source)
    ) {
      const versions = sources.filter(
        (s) =>
          s.kind === "reference_excerpt" &&
          s.id.startsWith(`${e.source}_`) &&
          /^reference_\d+_\d+$/.test(s.id),
      );
      if (versions.length === 1) source = versions[0];
    }
    let anchor = typeof e.anchor === "string" ? e.anchor.trim() : "";
    // Non-structured providers sometimes qualify an exact excerpt ID. Removing
    // that same source's literal prefix is unambiguous; ranges remain invalid.
    if (source)
      for (const prefix of new Set([
        `${source.id}:`,
        `${source.id} `,
        `${e.source}:`,
        `${e.source} `,
      ]))
        if (
          anchor.startsWith(prefix) &&
          /^p\d+$/.test(anchor.slice(prefix.length))
        )
          anchor = anchor.slice(prefix.length);
    const quote = normalize(
      source && typeof e.anchor === "string"
        ? excerpts(source.passage).find((p) => p.anchor === anchor)?.quote || ""
        : text(e.quote, 500),
    );
    if (
      source &&
      source.kind !== "metadata" &&
      quote.length >= 12 &&
      quote.split(/\s+/).length <= 25 &&
      normalize(source.passage).includes(quote)
    )
      result.push({ source: source.id, quote });
  }
  return result;
}

/** A quote match is a mechanical check, never proof that it entails the claim. */
export function validateDraft(
  raw: unknown,
  sources: ResearchSource[],
  registry: Registry,
  options: { recoverReferenceIds?: boolean } = {},
) {
  const value = object(raw),
    gaps = strings(value.gaps, 40);
  const nodes: Insight[] = [],
    relations: Connection[] = [];
  const used = new Set<string>();
  for (const item of (Array.isArray(value.nodes) ? value.nodes : []).slice(
    0,
    24,
  )) {
    const n = object(item),
      id = text(n.id, 100),
      anchors = evidence(n.evidence, sources, options.recoverReferenceIds);
    const claim = text(n.claim),
      explanation = text(n.explanation),
      title = text(n.title, 180);
    if (
      !idPattern.test(id) ||
      used.has(id) ||
      !title ||
      !subjects.includes(String(n.subject)) ||
      !insightKinds.includes(String(n.kind)) ||
      claim.length < 25 ||
      explanation.length < 40 ||
      !anchors.length
    ) {
      gaps.push(
        `An insight was withheld because its identity, explanation or inspectable evidence was incomplete: ${title || id || "untitled"}.`,
      );
      continue;
    }
    used.add(id);
    nodes.push({
      id,
      title,
      claim,
      explanation,
      problem: text(n.problem),
      move: text(n.move),
      assumptions: strings(n.assumptions),
      limitations: strings(n.limitations),
      attribution: strings(n.attribution),
      year:
        Number.isInteger(n.year) &&
        Number(n.year) >= -4000 &&
        Number(n.year) <= new Date().getFullYear()
          ? Number(n.year)
          : null,
      subject: String(n.subject),
      kind: String(n.kind),
      evidence: anchors,
      ...(["foundation", "bridge", "frontier", "limitation"].includes(
        String(n.role),
      )
        ? { role: n.role as Insight["role"] }
        : {}),
    });
  }
  const signatures = new Set<string>();
  for (const item of (Array.isArray(value.relations)
    ? value.relations
    : []
  ).slice(0, 48)) {
    const r = object(item),
      id = text(r.id, 100),
      predicate = text(r.predicate, 80);
    const rule = Object.hasOwn(registry, predicate)
      ? registry[predicate]
      : undefined;
    const premises = [...new Set(strings(r.premises, 6))],
      conclusion = text(r.conclusion, 100);
    const anchors = evidence(r.evidence, sources, options.recoverReferenceIds),
      warrant = text(r.warrant);
    const scope = text(r.scope);
    const sharedTaskOnly =
      predicate === "analogous_to" &&
      /\b(?:limited|confined)\s+to\s+(?:(?:their|the|its)\s+)?(?:shared|common|same)\s+(?:purpose|task|topic|goal)\b/i.test(
        scope,
      );
    const endpointNodes = premises.map((p) => nodes.find((n) => n.id === p));
    const target = nodes.find((n) => n.id === conclusion);
    const basis = ["documented", "synthesis", "teaching"].includes(
      String(r.basis),
    )
      ? (r.basis as Connection["basis"])
      : undefined;
    const steps = strings(r.steps, 4).map((s) => s.slice(0, 600));
    // Endpoint claims already carry validated evidence. A third source can
    // document their connection: citation identity is not entailment.
    // Synthesis exposes an explicit reasoning chain for the independent check.
    // Older files without a declared basis retain their original stricter rule.
    const missingBridge =
      basis === "documented"
        ? !scope
        : basis === "synthesis"
          ? !(
              ["logical", "evidential", "conceptual"].includes(
                rule?.layer || "",
              ) || predicate === "applied_in"
            ) ||
            !scope ||
            steps.length < 2
          : basis === "teaching"
            ? rule?.layer !== "pedagogical" || !scope
            : rule?.layer !== "pedagogical" &&
              !anchors.some((anchor) =>
                [...endpointNodes, target].every((n) =>
                  n?.evidence.some((e) => e.source === anchor.source),
                ),
              );
    const reverseHistory =
      predicate === "historical_basis_for" &&
      (target?.year == null ||
        endpointNodes.some((n) => n?.year == null || n.year >= target.year!));
    // Conservative personal-map guards. A component list is not an inference,
    // and a method is not the observation that evaluates it.
    const wrongEvidenceRole =
      ["supports", "challenges"].includes(predicate) &&
      endpointNodes.some(
        (n) =>
          ![
            "empirical_finding",
            "negative_result",
            "argument",
            "theorem",
            "normative_argument",
          ].includes(n?.kind || ""),
      );
    const partWholeInference =
      predicate === "premise_for" &&
      steps.length < 2 &&
      ["method", "representation", "mechanism"].includes(target?.kind || "") &&
      endpointNodes.every((n) =>
        ["method", "representation", "mechanism"].includes(n?.kind || ""),
      );
    const signature = `${predicate}:${rule?.symmetric ? [...premises, conclusion].sort().join("|") : premises.slice().sort().join("|") + ">" + conclusion}`;
    if (
      !idPattern.test(id) ||
      used.has(id) ||
      !rule ||
      !premises.length ||
      !target ||
      endpointNodes.some((n) => !n) ||
      premises.includes(conclusion) ||
      !anchors.length ||
      warrant.length < 30 ||
      reverseHistory ||
      wrongEvidenceRole ||
      partWholeInference ||
      missingBridge ||
      sharedTaskOnly ||
      signatures.has(signature) ||
      (rule.symmetric && premises.length !== 1)
    ) {
      gaps.push(
        `A proposed connection was withheld (${id || "unnamed"}): ${reverseHistory ? "year-only dates do not establish an earlier historical basis" : wrongEvidenceRole ? "an evidence arrow must run from evidence or an argument to a claim" : partWholeInference ? "component or method membership does not establish logical implication" : missingBridge ? (basis ? "its declared evidence basis lacks explicit reasoning, scope or an admissible predicate" : "no inspected source was cited for both the connection and all of its endpoints; separate papers do not establish this bridge") : sharedTaskOnly ? "a similarity explicitly limited to a shared purpose is not a structural analogy" : !premises.length ? "no premise insight was supplied" : !target || endpointNodes.some((n) => !n) || premises.includes(conclusion) ? "an endpoint was missing or the connection pointed to itself" : !anchors.length ? "none of its cited excerpts matched a retrieved source" : "its identity, scope or meaning did not pass checks"}.`,
      );
      continue;
    }
    used.add(id);
    signatures.add(signature);
    relations.push({
      id,
      premises,
      conclusion,
      predicate,
      layer: rule.layer,
      warrant,
      scope,
      evidence: anchors,
      ...(basis ? { basis } : {}),
      ...(steps.length ? { steps } : {}),
    });
  }
  return {
    title: text(value.title, 180),
    summary: text(value.summary),
    nodes,
    relations,
    gaps: [...new Set(gaps)],
  };
}

/** Only the excerpts actually inspected travel with a saved personal map. */
export function citedSources(
  sources: ResearchSource[],
  nodes: Insight[],
  relations: Connection[],
): ResearchSource[] {
  const quotes = new Map<string, Set<string>>();
  for (const item of [...nodes, ...relations])
    for (const e of item.evidence) {
      if (!quotes.has(e.source)) quotes.set(e.source, new Set());
      quotes.get(e.source)!.add(e.quote);
    }
  return sources
    .filter((s) => quotes.has(s.id))
    .map((s) => ({
      id: s.id,
      title: s.title,
      url: s.url,
      authors: s.authors,
      year: s.year,
      kind: s.kind,
      passage: [...quotes.get(s.id)!].join("\n…\n"),
      retrieved_at: s.retrieved_at,
      ...(s.doi ? { doi: s.doi } : {}),
      ...(s.license ? { license: s.license } : {}),
      ...(s.pmcid ? { pmcid: s.pmcid } : {}),
      ...(s.atlas_id
        ? {
            atlas_id: s.atlas_id,
            revision: s.revision,
            content_hash: s.content_hash,
          }
        : {}),
    }));
}

export function graphData(draft: Exploration): {
  nodes: Contribution[];
  relations: Relation[];
} {
  return {
    nodes: draft.nodes.map((n) => ({
      id: n.id,
      revision: 1,
      content_hash: "personal-draft",
      type: "contribution",
      title: n.title,
      kind: n.kind,
      pillar: n.subject,
      claim: n.claim,
      problem: n.problem,
      conceptual_move: n.move,
      explanation: n.explanation,
      assumptions: n.assumptions,
      limits: n.limitations,
      attribution: n.attribution.map((name) => ({
        name,
        role: "unverified draft attribution",
      })),
      date: { year: n.year, precision: "unverified", event: "", note: "" },
      anchors: [],
      human_review: "not_reviewed",
      machine_screening: "not_screened",
      scientific_standing: "unverified",
      dossiers: [],
      curation: {},
    })),
    relations: draft.relations.map((r) => ({
      id: r.id,
      revision: 1,
      type: "relation",
      premises: r.premises.map((id) => ({ id, revision: 1 })),
      conclusion: { id: r.conclusion, revision: 1 },
      predicate: r.predicate,
      layer: r.layer,
      warrant: r.warrant,
      scope: r.scope,
      anchors: [],
      human_review: "not_reviewed",
      machine_screening: "not_screened",
    })),
  };
}

/** Import is a boundary, not a shortcut around validation. Unknown fields are discarded. */
export function importExploration(
  input: string,
  registry: Registry,
): Exploration {
  if (input.length > 2_000_000)
    throw new Error("This file is too large (maximum 2 MB).");
  const v = object(JSON.parse(input));
  if (
    v.format !== "principia-exploration/v1" ||
    v.action_scope !== "read_only" ||
    v.status !== "unverified_draft"
  )
    throw new Error("Choose a Principia personal exploration file.");
  if (
    !Array.isArray(v.sources) ||
    v.sources.length > 60 ||
    !Array.isArray(v.nodes) ||
    v.nodes.length > 24 ||
    !Array.isArray(v.relations) ||
    v.relations.length > 48
  )
    throw new Error("The map exceeds the supported bounds.");
  const sources: ResearchSource[] = [],
    ids = new Set<string>();
  for (const raw of v.sources) {
    const s = object(raw),
      id = text(s.id, 100),
      url = safeURL(text(s.url, 2000));
    if (
      !idPattern.test(id) ||
      ids.has(id) ||
      ![
        "atlas",
        "abstract",
        "metadata",
        "article_excerpt",
        "reference_excerpt",
      ].includes(String(s.kind)) ||
      (s.kind !== "atlas" && !url)
    )
      throw new Error("This map contains an invalid source.");
    ids.add(id);
    sources.push({
      id,
      title: text(s.title, 400),
      url,
      authors: strings(s.authors, 30),
      year: Number.isInteger(s.year) ? Number(s.year) : null,
      kind: s.kind as ResearchSource["kind"],
      passage: text(s.passage, 15000),
      retrieved_at: text(s.retrieved_at, 50),
      ...(s.kind === "atlas" && idPattern.test(String(s.atlas_id))
        ? {
            atlas_id: String(s.atlas_id),
            revision: Number(s.revision),
            content_hash: text(s.content_hash, 64),
          }
        : {}),
      ...(s.doi ? { doi: text(s.doi, 300) } : {}),
      ...(s.license && safeURL(String(s.license))
        ? { license: safeURL(String(s.license)) }
        : {}),
      ...(/^PMC[0-9]+$/.test(String(s.pmcid))
        ? { pmcid: String(s.pmcid) }
        : {}),
    });
  }
  const checked = validateDraft(v, sources, registry);
  if (
    checked.nodes.length !== v.nodes.length ||
    checked.relations.length !== v.relations.length
  )
    throw new Error(
      "This map contains unsupported nodes or connections. Import was stopped.",
    );
  return {
    format: "principia-exploration/v1",
    id: idPattern.test(String(v.id)) ? String(v.id) : crypto.randomUUID(),
    title: checked.title,
    query: text(v.query, 500),
    summary: checked.summary,
    created_at: text(v.created_at, 50),
    atlas_release: text(v.atlas_release, 100),
    snapshot_hash: text(v.snapshot_hash, 64),
    model: text(v.model, 160),
    status: "unverified_draft",
    action_scope: "read_only",
    completion: v.completion === "partial" ? "partial" : "complete",
    check_status: ["not_started", "incomplete", "completed"].includes(
      String(v.check_status),
    )
      ? (v.check_status as Exploration["check_status"])
      : "not_recorded",
    nodes: checked.nodes,
    relations: checked.relations,
    sources: citedSources(sources, checked.nodes, checked.relations),
    gaps: checked.gaps,
    receipts: (Array.isArray(v.receipts) ? v.receipts : [])
      .slice(0, 24)
      .map((raw) => {
        const r = object(raw);
        return {
          stage: text(r.stage, 80),
          model: text(r.model, 160),
          started_at: text(r.started_at, 50),
          outcome: ["completed", "failed", "cancelled"].includes(
            String(r.outcome),
          )
            ? (r.outcome as Receipt["outcome"])
            : "failed",
          input_hash: text(r.input_hash, 64),
          prompt_hash: text(r.prompt_hash, 64),
          ...(typeof r.thinking_disabled === "boolean"
            ? { thinking_disabled: r.thinking_disabled }
            : {}),
          ...(Number.isSafeInteger(r.thinking_budget) &&
          Number(r.thinking_budget) >= 0 &&
          Number(r.thinking_budget) <= 1_000_000
            ? { thinking_budget: Number(r.thinking_budget) }
            : {}),
          ...(["json_schema", "json_object", "text"].includes(
            String(r.response_format),
          )
            ? {
                response_format:
                  r.response_format as Receipt["response_format"],
              }
            : {}),
          ...(Number.isInteger(r.reasoning_characters) &&
          Number(r.reasoning_characters) >= 0
            ? {
                reasoning_characters: Math.min(
                  Number(r.reasoning_characters),
                  1_000_000,
                ),
              }
            : {}),
          ...(Number.isFinite(r.elapsed_ms) && Number(r.elapsed_ms) >= 0
            ? { elapsed_ms: Math.min(Number(r.elapsed_ms), 600_000) }
            : {}),
          ...(Number.isFinite(r.first_content_ms) &&
          Number(r.first_content_ms) >= 0
            ? {
                first_content_ms: Math.min(Number(r.first_content_ms), 600_000),
              }
            : {}),
          ...(Number.isInteger(r.output_characters) &&
          Number(r.output_characters) >= 0
            ? {
                output_characters: Math.min(
                  Number(r.output_characters),
                  100_000,
                ),
              }
            : {}),
          ...(Number.isInteger(r.response_bytes) &&
          Number(r.response_bytes) >= 0
            ? { response_bytes: Math.min(Number(r.response_bytes), 64_000_000) }
            : {}),
          ...(Number.isInteger(r.stream_events) && Number(r.stream_events) >= 0
            ? { stream_events: Math.min(Number(r.stream_events), 200_000) }
            : {}),
          input_tokens:
            Number.isInteger(r.input_tokens) && Number(r.input_tokens) >= 0
              ? Number(r.input_tokens)
              : null,
          output_tokens:
            Number.isInteger(r.output_tokens) && Number(r.output_tokens) >= 0
              ? Number(r.output_tokens)
              : null,
        };
      }),
  };
}
