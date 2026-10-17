import {
  object,
  strings,
  text,
  operationalKinds,
  type validateDraft,
} from "./model";
import { completedItems, ProviderFailure } from "./stream";

type Draft = ReturnType<typeof validateDraft>;

function checks(
  value: unknown,
  ids: Set<string>,
  relation = false,
): (Record<string, unknown> & { id: string })[] {
  if (!Array.isArray(value)) return [];
  const seen = new Set<string>();
  return value.flatMap((raw) => {
    const item = object(raw),
      id = text(item.id, 100);
    if (
      !ids.has(id) ||
      seen.has(id) ||
      typeof item.keep !== "boolean" ||
      (!relation &&
        item.assessed_role !== undefined &&
        ![
          "general_foundation",
          "requested_result",
          "supporting_idea",
          "limiting_condition",
        ].includes(String(item.assessed_role))) ||
      (relation &&
        [
          "direction_correct",
          "warrant_supported",
          "scope_matches_endpoints",
        ].some((field) => typeof item[field] !== "boolean"))
    )
      return [];
    seen.add(id);
    return [
      {
        ...item,
        id,
        ...(!relation && item.assessed_role !== undefined
          ? {
              foundation_general: item.assessed_role === "general_foundation",
              endpoint_matches: item.assessed_role === "requested_result",
            }
          : {}),
      },
    ];
  });
}

/** Counts completed verdicts, not tokens or a fabricated percentage. */
export function reviewProgress(content: string, draft: Draft) {
  return {
    nodes: checks(
      completedItems(content, "node_checks"),
      new Set(draft.nodes.map((n) => n.id)),
    ).length,
    relations: checks(
      completedItems(content, "relation_checks"),
      new Set(draft.relations.map((r) => r.id)),
      true,
    ).length,
  };
}

/** Missing, duplicate or ambiguous verdicts cannot earn a completed check. */
export function applyReview(raw: unknown, draft: Draft): Draft {
  const result = object(raw);
  const nodeChecks = checks(
    result.node_checks,
    new Set(draft.nodes.map((n) => n.id)),
  );
  const relationChecks = checks(
    result.relation_checks,
    new Set(draft.relations.map((r) => r.id)),
    true,
  );
  if (
    !Array.isArray(result.node_checks) ||
    !Array.isArray(result.relation_checks) ||
    nodeChecks.length !== draft.nodes.length ||
    relationChecks.length !== draft.relations.length ||
    nodeChecks.length !== result.node_checks.length ||
    draft.nodes.some(
      (n) =>
        n.role === "foundation" &&
        typeof nodeChecks.find((c) => c.id === n.id)?.foundation_general !==
          "boolean",
    ) ||
    draft.nodes.some(
      (n) =>
        n.role === "frontier" &&
        typeof nodeChecks.find((c) => c.id === n.id)?.endpoint_matches !==
          "boolean",
    ) ||
    relationChecks.length !== result.relation_checks.length
  )
    throw new ProviderFailure(
      "The evidence review did not assess every insight and connection unambiguously. Your draft is available below; resume only this check when ready.",
    );

  const kept = new Set(
    nodeChecks.filter((n) => n.keep === true).map((n) => n.id),
  );
  const passed = new Set(
    relationChecks
      .filter(
        (r) =>
          r.keep === true &&
          r.direction_correct === true &&
          r.warrant_supported === true &&
          r.scope_matches_endpoints === true,
      )
      .map((r) => r.id),
  );
  const nodes = draft.nodes
    .filter((n) => kept.has(n.id))
    .map((n) =>
      (n.role === "foundation" &&
        nodeChecks.find((c) => c.id === n.id)?.foundation_general === false) ||
      (n.role === "frontier" &&
        nodeChecks.find((c) => c.id === n.id)?.endpoint_matches === false)
        ? { ...n, role: "bridge" as const }
        : n,
    )
    .map((n) => {
      const check = nodeChecks.find((c) => c.id === n.id)!;
      return {
        ...n,
        // A reference's collective authorship is source credit, never discovery
        // attribution, even if a model accidentally approves it. The original
        // source credit remains in every evidence inspector and portable source.
        attribution:
          check.attribution_supported === true
            ? n.attribution.filter(
                (name) =>
                  !/^wikipedia(?: contributors| authors)?$/i.test(name.trim()),
              )
            : [],
        year: check.date_supported === true ? n.year : null,
      };
    });
  for (const r of draft.relations) {
    const target = nodes.find((n) => n.id === r.conclusion);
    if (r.predicate === "premise_for" && target?.kind === "empirical_finding") {
      passed.delete(r.id);
      const verdict = relationChecks.find((c) => c.id === r.id);
      if (verdict)
        verdict.reason =
          "A reported empirical observation cannot be established by logical deduction from a design or general principle. A theoretical prediction and an observed result must remain separate claims.";
    }
    if (
      r.predicate === "premise_for" &&
      operationalKinds.includes(
        nodes.find((n) => n.id === r.conclusion)?.kind || "",
      ) &&
      r.premises.every((id) =>
        operationalKinds.includes(nodes.find((n) => n.id === id)?.kind || ""),
      )
    ) {
      // A numbered list can still just describe components. Conservatively
      // withhold this shape even when a model mislabels it as a deduction.
      // Formal claims/arguments remain eligible; imports are not rewritten.
      passed.delete(r.id);
      const verdict = relationChecks.find((c) => c.id === r.id);
      if (verdict)
        verdict.reason =
          "Operational components alone do not establish a logical derivation of another process. Numbered steps and a positive model verdict cannot establish that implication; the inference was withheld.";
    }
    if (r.predicate === "bounded_by") {
      const check = nodeChecks.find((c) => c.id === r.conclusion);
      // Independent verdicts must agree on what the endpoint IS. A requested
      // apparatus/process cannot become its own limiting condition merely
      // because an arrow's warrant talks about a limit absent from that node.
      if (
        (check?.assessed_role === "requested_result" &&
          operationalKinds.includes(target?.kind || "")) ||
        (check?.assessed_role === "general_foundation" &&
          target?.kind === "empirical_finding")
      ) {
        passed.delete(r.id);
        const verdict = relationChecks.find((c) => c.id === r.id);
        if (verdict)
          verdict.reason =
            "The destination was independently assessed as a requested process or general empirical claim, not a restricting condition. The contradictory limiting arrow was withheld.";
      }
    }
    if (r.predicate !== "historical_basis_for") continue;
    if (
      target?.year == null ||
      r.premises.some((id) => {
        const source = nodes.find((n) => n.id === id);
        return source?.year == null || source.year >= target.year!;
      })
    ) {
      passed.delete(r.id);
      const verdict = relationChecks.find((c) => c.id === r.id);
      if (verdict)
        verdict.reason =
          "Discovery dates were not established; the earlier-to-later historical basis cannot be retained.";
    }
  }
  const relations = draft.relations.filter(
    (r) =>
      passed.has(r.id) &&
      kept.has(r.conclusion) &&
      r.premises.every((id) => kept.has(id)),
  );
  const gaps = [...draft.gaps, ...strings(result.gaps, 40)];
  for (const n of draft.nodes) {
    if (!kept.has(n.id)) continue;
    const check = nodeChecks.find((c) => c.id === n.id)!;
    if (
      n.attribution.length >
      (nodes.find((v) => v.id === n.id)?.attribution.length || 0)
    )
      gaps.push(
        `Discovery attribution for “${n.title}” was not established by the check and has been left unspecified.`,
      );
    if (n.year !== null && check.date_supported !== true)
      gaps.push(
        `The discovery date for “${n.title}” was not established by the check and has been left unspecified.`,
      );
  }
  for (const n of draft.nodes)
    if (
      n.role === "foundation" &&
      kept.has(n.id) &&
      nodeChecks.find((c) => c.id === n.id)?.foundation_general === false
    )
      gaps.push(
        `“${n.title}” explains a specialized mechanism. A deeper governing principle is still needed.`,
      );
  for (const n of draft.nodes)
    if (
      n.role === "frontier" &&
      kept.has(n.id) &&
      nodeChecks.find((c) => c.id === n.id)?.endpoint_matches === false
    )
      gaps.push(
        `“${n.title}” is related work, but does not establish the exact requested result. The endpoint is still missing.`,
      );
  for (const n of nodeChecks)
    if (!kept.has(n.id))
      gaps.push(
        `Insight withheld (${text(n.id, 100)}): ${text(n.reason, 500) || "Its claims were not established by the supplied passages."}`,
      );
  for (const r of relationChecks)
    if (!passed.has(r.id))
      gaps.push(
        `Connection withheld (${text(r.id, 100)}): ${text(r.reason, 500) || "Its scope, warrant or direction was not established."}`,
      );
  const removed = draft.nodes.length - nodes.length,
    removedRelations = draft.relations.length - relations.length;
  if (removed || removedRelations)
    gaps.push(
      `The model check withheld ${removed} insights and ${removedRelations} connections. Missing links have not been filled in.`,
    );
  return { ...draft, nodes, relations, gaps };
}
