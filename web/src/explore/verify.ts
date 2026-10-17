import {
  object,
  type Registry,
  type ResearchSource,
  type validateDraft,
} from "./model";
import { Provider } from "./provider";
import { ProviderFailure } from "./stream";
import { applyReview } from "./review";
import { BOUNDARY, CHALLENGE, relationChallenge } from "./prompts";

type Draft = ReturnType<typeof validateDraft>;
export type ReviewCheckpoint = {
  nodes?: Record<string, unknown>;
  relations: Record<string, Record<string, unknown>>;
};

export function checkedNodes(checkpoint?: ReviewCheckpoint) {
  const checks = checkpoint?.nodes?.node_checks;
  return Array.isArray(checks) ? checks : [];
}

/** Validate the assessment, rather than interpreting missing or ambiguous flags as approval. */
export function relationVerdict(
  raw: unknown,
  id: string,
  predicate = "",
): Record<string, unknown> {
  const v = object(raw);
  if (
    v.id !== id ||
    !["valid", "invalid", "unclear"].includes(String(v.direction)) ||
    !["valid", "invalid", "unclear"].includes(String(v.scope)) ||
    !["supported", "unsupported", "unclear"].includes(String(v.warrant)) ||
    typeof v.assessment !== "string"
  )
    throw new ProviderFailure(
      "A connection check returned an incomplete verdict. Completed checks are retained; resume the unfinished review when ready.",
    );
  const direction_correct = v.direction === "valid",
    scope_matches_endpoints = v.scope === "valid",
    warrant_supported = v.warrant === "supported";
  const roles = object(v.endpoint_roles);
  const boundDirection =
    predicate !== "bounded_by" ||
    (roles.from === "restricted_claim" && roles.to === "restricting_condition");
  const deduction =
    predicate !== "premise_for" || v.connection_type === "deductive_derivation";
  return {
    id,
    direction_correct: direction_correct && boundDirection,
    scope_matches_endpoints,
    warrant_supported: warrant_supported && deduction,
    keep:
      direction_correct &&
      boundDirection &&
      deduction &&
      scope_matches_endpoints &&
      warrant_supported,
    reason: !deduction
      ? "The proposed inference was not classified as a deductive derivation of the actual conclusion. " +
        v.assessment.slice(0, 360)
      : boundDirection
        ? v.assessment.slice(0, 500)
        : "The directed bound did not identify a restricted claim as its start and an actual restricting condition as its destination. " +
          v.assessment.slice(0, 340),
  };
}

/** Small independent relationship checks, four in flight, sharing one review deadline. */
export async function verifyMap(options: {
  provider: Provider;
  draft: Draft;
  sources: ResearchSource[];
  query: string;
  endpoint?: string;
  registry: Registry;
  deadline: number;
  signal: AbortSignal;
  checkpoint: ReviewCheckpoint;
  updated: () => void;
  packet: (sources: ResearchSource[], query: string) => unknown;
}): Promise<Draft> {
  const {
    provider,
    draft,
    sources,
    query,
    registry,
    deadline,
    signal,
    checkpoint,
    updated,
    packet,
  } = options;
  const jobs: (() => Promise<void>)[] = [];
  let incompleteRepairs = 0;
  const checkedIds = new Set(checkedNodes(checkpoint).map((n) => object(n).id));
  const pendingNodes = draft.nodes.filter((n) => !checkedIds.has(n.id));
  // Keep both context and answer size small. Completed batches survive a slow
  // sibling request; a resume asks only for still-unchecked claims.
  const reviewNodes =
    (batch: Draft["nodes"]): (() => Promise<void>) =>
    async () => {
      const ids = new Set(
        batch.flatMap((n) => n.evidence.map((e) => e.source)),
      );
      const raw = object(
        await provider.json(
          "evidence challenge",
          BOUNDARY + CHALLENGE,
          {
            query,
            interpreted_endpoint: options.endpoint || query,
            draft: { nodes: batch, relations: [] },
            // Earlier accepted/proposed moves let the critic detect semantic
            // duplicates without asking sibling batches to reject each other.
            earlier_insights: draft.nodes
              .slice(
                0,
                draft.nodes.findIndex((n) => n.id === batch[0].id),
              )
              .map(({ id, title, claim }) => ({ id, title, claim })),
            registry: {},
            sources: packet(
              sources.filter((s) => ids.has(s.id)),
              query,
            ),
          },
          250 + batch.length * 75,
          deadline,
        ),
      );
      const verdicts = Array.isArray(raw.node_checks) ? raw.node_checks : [];
      const accepted: unknown[] = [];
      const missing = batch.filter((node) => {
        const matches = verdicts.filter((v) => object(v).id === node.id);
        if (matches.length !== 1) return true;
        try {
          applyReview(
            { node_checks: matches, relation_checks: [], gaps: [] },
            { ...draft, nodes: [node], relations: [] },
          );
          accepted.push(matches[0]);
          return false;
        } catch {
          return true;
        }
      });
      checkpoint.nodes = {
        node_checks: [...checkedNodes(checkpoint), ...accepted],
        relation_checks: [],
        // A small batch cannot diagnose omissions in the whole map.
        // Preserve per-record rejection reasons via applyReview, rather than
        // presenting batch-local absence claims as global coverage gaps.
        gaps: [],
      };
      updated();
      // A missing verdict cannot invalidate completed siblings. Ask only for
      // unresolved records, at most twice, under this pass's original deadline.
      // Provider failures and timeouts are never replayed here.
      if (missing.length && incompleteRepairs < 2 && Date.now() < deadline) {
        incompleteRepairs++;
        jobs.push(reviewNodes(missing));
      }
    };
  for (let i = 0; i < pendingNodes.length; i += 2)
    jobs.push(reviewNodes(pendingNodes.slice(i, i + 2)));
  for (const relation of draft.relations) {
    if (checkpoint.relations[relation.id]) continue;
    jobs.push(async () => {
      const { premises, conclusion, ...meaningfulRelation } = relation;
      const endpoints = draft.nodes.filter(
        (n) => relation.premises.includes(n.id) || relation.conclusion === n.id,
      );
      const ids = new Set(
        [...endpoints, relation].flatMap((n) =>
          n.evidence.map((e) => e.source),
        ),
      );
      const raw = await provider.json(
        `relation check ${relation.basis === "teaching" ? "teaching " : relation.layer === "logical" ? "reasoning " : ""}${relation.id}`,
        BOUNDARY + relationChallenge(relation.predicate),
        {
          query,
          interpreted_endpoint: options.endpoint || query,
          relation: {
            ...meaningfulRelation,
            from: premises,
            to: conclusion,
          },
          from: relation.premises.map((id) =>
            endpoints.find((n) => n.id === id),
          ),
          to: endpoints.find((n) => n.id === relation.conclusion),
          directed_statement: `${relation.premises.map((id) => endpoints.find((n) => n.id === id)?.title).join(" AND ")} — ${relation.predicate} → ${endpoints.find((n) => n.id === relation.conclusion)?.title}`,
          meaning: registry[relation.predicate],
          sources: sources
            .filter((s) => ids.has(s.id))
            .map((s) => ({
              id: s.id,
              title: s.title,
              kind: s.kind,
              passage: s.passage,
            })),
        },
        450,
        deadline,
      );
      checkpoint.relations[relation.id] = relationVerdict(
        raw,
        relation.id,
        relation.predicate,
      );
      updated();
    });
  }
  let failure: unknown;
  async function worker() {
    while (jobs.length && !failure) {
      signal.throwIfAborted();
      try {
        await jobs.shift()!();
      } catch (error) {
        failure = error;
      }
    }
  }
  await Promise.all(
    Array.from({ length: Math.min(4, jobs.length) }, () => worker()),
  );
  signal.throwIfAborted();
  if (failure) throw failure;
  return applyReview(
    {
      ...checkpoint.nodes,
      relation_checks: Object.values(checkpoint.relations),
    },
    draft,
  );
}
