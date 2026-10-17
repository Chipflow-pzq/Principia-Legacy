import { assembleConnection } from "./assembly";
import { object, strings, type validateDraft } from "./model";

type Draft = ReturnType<typeof validateDraft>;
export const additionIds = ["addition-1", "addition-2"];
export function additionRoles(nodes: { role?: string }[]) {
  return [
    "bridge",
    "limitation",
    "foundation",
    ...(!nodes.some((n) => n.role === "frontier") ? ["frontier"] : []),
  ];
}

/** Add a small missing mechanism without rewriting an already checked record.
 * New IDs deliberately cannot inherit an old node's verdict or incident edges.
 * This is a candidate merge only: evidence validation and review still follow.
 */
export function refinementCandidate(base: Draft, raw: unknown) {
  const value = object(raw),
    gaps = [...base.gaps, ...strings(value.gaps, 6)];
  const additions: Record<string, unknown>[] = [];
  const used = new Set(base.nodes.map((n) => n.id));
  const allowed = additionRoles(base.nodes);
  let addedResult = false;
  for (const item of (Array.isArray(value.additions)
    ? value.additions
    : []
  ).slice(0, 2)) {
    const n = object(item),
      id = String(n.id);
    if (
      !additionIds.includes(id) ||
      used.has(id) ||
      !allowed.includes(String(n.role)) ||
      (n.role === "frontier" && addedResult)
    ) {
      gaps.push(
        "A refinement tried to replace an existing insight or use an invalid addition slot; that candidate was withheld.",
      );
      continue;
    }
    used.add(id);
    if (n.role === "frontier") addedResult = true;
    additions.push(n);
  }
  return {
    ...base,
    nodes: [...base.nodes, ...additions],
    relations: [
      ...base.relations,
      ...(Array.isArray(value.relations) ? value.relations : [])
        .slice(0, 4)
        .map((r, i) => ({ ...assembleConnection(r), id: `refined-${i + 1}` })),
    ],
    gaps,
  };
}
