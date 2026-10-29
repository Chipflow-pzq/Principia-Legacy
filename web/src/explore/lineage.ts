import type { Connection, Insight } from "./model";

export const roleLabels = {
  foundation: "Foundation",
  bridge: "Enabling idea",
  frontier: "Requested result",
  limitation: "Boundary or tradeoff",
};

const forwardPredicates = new Set([
  "historical_basis_for",
  "applied_in",
  "motivated",
  "generalized_by",
  "premise_for",
  "prerequisite_for_reading",
  "supports",
]);

/** Find the ungrounded entrance to the result's existing explanatory branch.
 * These are search priorities, never proposed or automatically accepted edges.
 */
export function connectionGaps(nodes: Insight[], relations: Connection[]) {
  const analysis = lineage(nodes, relations);
  const unreachable = new Set(analysis.unreachable);
  const forward = relations.filter((r) => forwardPredicates.has(r.predicate));
  const required = new Set(
    nodes.filter((n) => n.role === "frontier").map((n) => n.id),
  );
  for (let pass = 0; pass < nodes.length; pass++) {
    const before = required.size;
    for (const r of forward)
      if (required.has(r.conclusion))
        r.premises.forEach((id) => required.add(id));
    if (before === required.size) break;
  }
  const missing = nodes.filter(
    (n) => required.has(n.id) && unreachable.has(n.id),
  );
  const entrances = missing.filter(
    (n) =>
      !forward.some(
        (r) =>
          r.conclusion === n.id && r.premises.some((id) => unreachable.has(id)),
      ),
  );
  return {
    has_core_route: analysis.hasBackbone,
    isolated_ids: analysis.isolated,
    reachable_from_foundations: nodes
      .filter((n) => !unreachable.has(n.id))
      .map((n) => n.id),
    ungrounded_result_branch: missing.map((n) => n.id),
    priority_gap_targets: (entrances.length ? entrances : missing).map(
      (n) => n.id,
    ),
    meaning:
      "Find evidence for the missing mechanism into these targets. A target may need a new general principle or a distinct parallel input; do not force an existing reachable node to explain it.",
  };
}

/** An explanatory reading route, never a claim of transitive proof or influence. */
export function lineage(nodes: Insight[], relations: Connection[]) {
  return analyze(nodes, relations, false);
}

/** A reading itinerary may visit the technology constrained by a known bound.
 * This does not reverse the stored arrow, assert causation, or earn the stricter
 * directed-backbone metric used by lineage(). */
export function readingRoute(nodes: Insight[], relations: Connection[]) {
  return analyze(nodes, relations, true);
}

function analyze(
  nodes: Insight[],
  relations: Connection[],
  readConstraints: boolean,
) {
  const foundations = nodes.filter((n) => n.role === "foundation");
  const targets = new Set(
    nodes.filter((n) => n.role === "frontier").map((n) => n.id),
  );
  const connected = new Set(
    relations.flatMap((r) => [...r.premises, r.conclusion]),
  );
  const forward: (Connection & { readReverse?: boolean })[] = relations.filter(
    (r) => forwardPredicates.has(r.predicate),
  );
  if (readConstraints)
    forward.push(
      ...relations
        .filter((r) => r.predicate === "bounded_by" && r.premises.length === 1)
        .map((r) => ({
          ...r,
          premises: [r.conclusion],
          conclusion: r.premises[0],
          readReverse: true,
        })),
    );
  // Joint premises are conjunctive: one connected input cannot stand in for
  // an unexplained co-premise, even in a navigation route.
  const reachable = new Set(foundations.map((n) => n.id));
  for (let pass = 0; pass < nodes.length; pass++) {
    const before = reachable.size;
    for (const r of forward)
      if (r.premises.every((id) => reachable.has(id)))
        reachable.add(r.conclusion);
    if (before === reachable.size) break;
  }
  let best: { nodes: string[]; relations: string[]; scientific: number } = {
    nodes: [],
    relations: [],
    scientific: 0,
  };
  const substantial = (path: typeof best) =>
    path.nodes.length >= 3 && path.scientific >= 1;
  // A direct teaching shortcut must not hide a longer, evidenced explanation.
  // Enumerate simple paths within a fixed work/depth budget, then prefer a
  // compact substantial route. This is navigation, not transitive entailment.
  let remaining = 5000;
  for (const start of foundations) {
    const queue = [
      { nodes: [start.id], relations: [] as string[], scientific: 0 },
    ];
    while (queue.length && remaining-- > 0) {
      const path = queue.shift()!,
        last = path.nodes.at(-1)!;
      if (targets.has(last)) {
        if (
          !best.nodes.length ||
          (substantial(path) && !substantial(best)) ||
          (substantial(path) === substantial(best) &&
            (path.nodes.length < best.nodes.length ||
              (path.nodes.length === best.nodes.length &&
                path.scientific > best.scientific)))
        )
          best = path;
        continue;
      }
      if (path.nodes.length >= 8) continue;
      for (const r of forward)
        if (
          r.premises.includes(last) &&
          r.premises.every((id) => reachable.has(id)) &&
          !path.nodes.includes(r.conclusion)
        )
          queue.push({
            nodes: [...path.nodes, r.conclusion],
            relations: [...path.relations, r.id],
            scientific: path.scientific + Number(r.layer !== "pedagogical"),
          });
    }
  }
  const core = new Set<string>([...targets].filter((id) => reachable.has(id)));
  for (let pass = 0; pass < nodes.length; pass++) {
    const before = core.size;
    for (const r of forward)
      if (core.has(r.conclusion) && r.premises.every((id) => reachable.has(id)))
        for (const id of r.premises) core.add(id);
    if (before === core.size) break;
  }
  const coreScientific = forward.filter(
    (r) =>
      r.layer !== "pedagogical" &&
      core.has(r.conclusion) &&
      r.premises.every((id) => core.has(id)),
  ).length;
  return {
    unreachable: nodes.filter((n) => !reachable.has(n.id)).map((n) => n.id),
    supporting: nodes
      .filter((n) => core.has(n.id) && !best.nodes.includes(n.id))
      .map((n) => n.id),
    foundations: foundations.length,
    connected: connected.size,
    isolated: nodes.filter((n) => !connected.has(n.id)).map((n) => n.id),
    route: best.nodes,
    relations: best.relations,
    reversed: best.relations.map(
      (id) => forward.find((r) => r.id === id)?.readReverse === true,
    ),
    hasNavigationPath: targets.size === 1 && best.nodes.length >= 3,
    scientificSteps: best.scientific,
    hasReadingPath:
      targets.size === 1 && best.nodes.length >= 3 && core.size >= 4,
    hasBackbone:
      targets.size === 1 &&
      best.nodes.length >= 3 &&
      core.size >= 4 &&
      coreScientific >= 2,
  };
}
