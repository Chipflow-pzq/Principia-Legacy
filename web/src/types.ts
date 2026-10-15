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
  release_id: string;
  counts: Record<string, number>;
  subject_counts?: Record<string, number>;
  pillars: Record<string, string>;
  predicates: Record<
    string,
    { layer: string; symmetric: boolean; label: string }
  >;
  releases: string[];
  current_release_id?: string;
  tours: Tour[];
  human_reviewed: number;
};
export type Neighborhood = {
  available_count?: number | null;
  release_id: string;
  contributions: Contribution[];
  relations: Relation[];
  notice: string;
};
export type Inspection = {
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
export async function api<T>(
  path: string,
  params: Record<string, string | number | boolean | undefined> = {},
  signal?: AbortSignal,
): Promise<T> {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") query.set(k, String(v));
  });
  const response = await fetch(
    `${import.meta.env.BASE_URL}api/${path}?${query}`,
    { signal },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      data.error || "The reader could not complete this request.",
    );
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
export function words(value: string) {
  const labels: Record<string, string> = {
    historical: "History",
    logical: "Reasoning",
    evidential: "Evidence",
    conceptual: "Similar ideas",
    pedagogical: "Learning prerequisites",
    historical_basis_for: "informed the development of",
    motivated: "motivated",
    applied_in: "was applied in",
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
};
export type PersonDetail = {
  release_id: string;
  person: Person;
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
  totals: { ideas: number; people: number; topics: number };
};
