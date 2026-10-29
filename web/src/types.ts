import { readAtlas } from "./cloudConnection";
export type Ref = { id: string; revision: number };
export type AnchorRef = {
  source_id: string;
  source_revision: number;
  anchor_id: string;
};
export type Contribution = {
  id: string;
  revision: number;
  content_hash: string;
  type: "contribution";
  title: string;
  kind: string;
  pillar: string;
  claim: string;
  problem: string;
  conceptual_move: string;
  explanation: string;
  assumptions: string[];
  limits: string[];
  attribution: { name: string; role: string; evidence_note?: string }[];
  date: { year: number | null; precision: string; event: string; note: string };
  anchors: AnchorRef[];
  human_review: string;
  effective_human_review?: string;
  machine_screening: string;
  scientific_standing: string;
  dossiers: string[];
  curation: { requested_model?: string; method?: string };
};
export type Relation = {
  id: string;
  revision: number;
  type: "relation";
  premises: Ref[];
  conclusion: Ref;
  predicate: string;
  layer: string;
  scope: string;
  warrant: string;
  anchors: AnchorRef[];
  human_review: string;
  effective_human_review?: string;
  machine_screening: string;
};
export type Source = {
  id: string;
  revision: number;
  title: string;
  creators: string[];
  url: string;
  date: string;
  source_version: string;
  access_state: string;
  rights: { license: string; distributed_material: string };
  anchors: {
    id: string;
    selector: string;
    summary: string;
    checked: boolean;
    text_hash: string;
  }[];
};
export type Dossier = {
  reading_route?: {
    ready: boolean;
    review: string;
    scope: string;
    rationale: string;
    notice: string;
  };
  work_count?: number;
  work_ids?: string[];
  isolated_contribution_count?: number;
  area?: string;
  topic_kind?: string;
  tags?: string[];
  id: string;
  title: string;
  pillar: string;
  flagship: boolean;
  endpoint: string | null;
  status: string;
  contribution_count: number;
  relation_count: number;
  source_count: number;
  historical_relation_count: number;
  boundary_relation_count: number;
  human_review_count: number;
  checklist_coverage: number;
  checklist: { id: string; requirement: string; supported: boolean }[];
  gaps: string[];
  frontier_open: boolean;
  search_outcomes: Record<string, string>;
};
export type Tour = {
  id: string;
  title: string;
  description: string;
  dossiers: string[];
};
export type Info = {
  connection_mode?: "private_cloud";
  release_id: string;
  counts: Record<string, number>;
  subject_counts?: Record<string, number>;
  catalog_counts?: {
    works: number;
    people: number;
    topics: number;
    works_with_insights: number;
  };
  pillars: Record<string, string>;
  predicates: Record<
    string,
    { layer: string; symmetric: boolean; label: string; meaning?: string }
  >;
  releases: string[];
  current_release_id?: string;
  tours: Tour[];
  human_reviewed: number;
};
export type Neighborhood = {
  available_count?: number | null;
  traversal_bounded?: boolean;
  release_id: string;
  contributions: Contribution[];
  relations: Relation[];
  notice: string;
};
export type Inspection = {
  pending?: boolean;
  works?: Work[];
  topics?: TopicLink[];
  people?: Person[];
  idea_families?: {
    id: string;
    title: string;
    description: string;
    members: { id: string; revision: number; title: string }[];
  }[];
  endpoints?: { id: string; revision: number; title: string }[];
  release_id: string;
  record: Contribution | Relation;
  sources: Source[];
  reviews: {
    reviewer_type: string;
    scope: string;
    rationale: string;
    reviewer_identity: string;
  }[];
};
const responseCache = new Map<
  string,
  { value: unknown; time: number; bytes: number }
>();
let cachedBytes = 0;
function apiURL(
  path: string,
  params: Record<string, string | number | boolean | undefined>,
) {
  const query = new URLSearchParams();
  Object.entries(params)
    .sort(([a], [b]) => a.localeCompare(b))
    .forEach(([k, v]) => {
      if (v !== undefined && v !== "") query.set(k, String(v));
    });
  return `${import.meta.env.BASE_URL}api/${path}?${query}`;
}
export function cachedAPI<T>(
  path: string,
  params: Record<string, string | number | boolean | undefined> = {},
): T | undefined {
  const entry = responseCache.get(apiURL(path, params));
  return entry && Date.now() - entry.time < 60_000
    ? (entry.value as T)
    : undefined;
}
export async function api<T>(
  path: string,
  params: Record<string, string | number | boolean | undefined> = {},
  signal?: AbortSignal,
): Promise<T> {
  signal?.throwIfAborted();
  const hit = cachedAPI<T>(path, params);
  if (hit !== undefined) return hit;
  const url = apiURL(path, params);
  const { data, text } = await readAtlas(url, signal);
  if (text.length < 4_000_000) {
    cachedBytes -= responseCache.get(url)?.bytes || 0;
    responseCache.delete(url);
    responseCache.set(url, {
      value: data,
      time: Date.now(),
      bytes: text.length * 2,
    });
    cachedBytes += text.length * 2;
    while (responseCache.size > 80 || cachedBytes > 24_000_000) {
      const first = responseCache.keys().next().value!;
      cachedBytes -= responseCache.get(first)!.bytes;
      responseCache.delete(first);
    }
  }
  return data;
}
export const COLORS: Record<string, string> = {
  mathematics: "#aa8df3",
  physics: "#66bcc8",
  computer_science: "#e6b263",
  economics: "#dc8d92",
  biology_medicine: "#83bc8e",
};
export const LAYERS = [
  "historical",
  "logical",
  "evidential",
  "conceptual",
  "pedagogical",
];
// One palette for the canvas, controls and legends; dash patterns also encode type.
export const CONNECTIONS: Record<
  string,
  {
    color: string;
    ink: string;
    style: "solid" | "dashed" | "dotted";
    dash: number[];
  }
> = {
  historical: {
    color: "#e9b665",
    ink: "#936016",
    style: "solid",
    dash: [1, 0],
  },
  logical: { color: "#78aff7", ink: "#326cba", style: "solid", dash: [1, 0] },
  evidential: {
    color: "#64d2ac",
    ink: "#207b5e",
    style: "dashed",
    dash: [12, 4],
  },
  conceptual: {
    color: "#d69ce7",
    ink: "#8e479f",
    style: "dashed",
    dash: [6, 5],
  },
  pedagogical: {
    color: "#f2929f",
    ink: "#b1425a",
    style: "dotted",
    dash: [2, 5],
  },
};
export function words(value: string) {
  const labels: Record<string, string> = {
    historical: "History",
    logical: "Reasoning",
    evidential: "Evidence",
    conceptual: "Similar ideas",
    pedagogical: "Learning prerequisites",
    historical_basis_for: "informed the development of",
    motivated: "motivated",
    applied_in: "is used in",
    independent_formulation_of: "independent formulation of",
    premise_for: "is a premise for",
    generalized_by: "is generalized by",
    bounded_by: "is limited by",
    supports: "supports",
    challenges: "challenges",
    analogous_to: "is analogous to",
    equivalent_under: "is equivalent under stated conditions to",
    prerequisite_for_reading: "helps explain",
    biology_medicine: "Biology & medicine",
  };
  return labels[value] || value.replaceAll("_", " ");
}

export type TopicLink = {
  id: string;
  title: string;
  pillar: string;
  reason?: string;
  origin?: string;
  contribution_count?: number;
  relation_count?: number;
  work_count?: number;
  reading_route?: { ready: boolean };
};
export type Person = {
  id: string;
  name: string;
  kind: string;
  revision: number;
  content_hash: string;
  aliases: string[];
  biography: string;
  life_dates?: string;
  bio_sources: { title: string; url: string; note?: string }[];
  subjects: string[];
  contribution_count: number;
  topic_ids: string[];
  profile_status: string;
  work_count?: number;
  selection_reason?: string;
};
export type PersonDetail = {
  release_id: string;
  person: Person;
  works?: Work[];
  contributions: (Contribution & {
    credit?: { role: string; recorded_name: string; evidence_note: string };
  })[];
  topics: TopicLink[];
};
export type SearchData = {
  offset: number;
  limit: number;
  results: Contribution[];
  people: Person[];
  topics: TopicLink[];
  works?: Work[];
  search_interpretation?: {
    match_mode?: "direct" | "related" | "semantic";
    notice?: string;
    corrections: { from: string; to: string }[];
    concepts: string[];
  };
  totals: { ideas: number; people: number; topics: number; works?: number };
};

export type CatalogSource = { url: string; title: string; note: string };
export type Work = {
  id: string;
  revision: number;
  content_hash: string;
  title: string;
  kind: string;
  subjects: string[];
  year?: number;
  recognition_year?: number;
  summary: string;
  insight_count: number;
  status: string;
  provenance: CatalogSource[];
};
export type WorkDetail = {
  release_id: string;
  work: Work;
  contributions: Contribution[];
  memberships: { contribution: Ref; role: string; reason: string }[];
  topics: TopicLink[];
  people: Person[];
  sources: Source[];
  relations: {
    id: string;
    predicate: string;
    layer: string;
    warrant: string;
    endpoints: Work[];
    symmetric: boolean;
    human_review?: string;
    machine_screening?: string;
    provenance: CatalogSource[];
  }[];
  shared_insights: { work: Work; insight_count: number }[];
  notice: string;
};
