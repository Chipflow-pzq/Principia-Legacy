/** Small provider output contracts. Local evidence validation remains authoritative. */
import {
  subjects,
  insightKinds,
  object,
  operationalKinds,
  type Registry,
} from "./model";
import { additionIds, additionRoles } from "./refinement";
import { SCHEMA } from "./prompts";
type Schema = Record<string, unknown>;

/** Do not ask the composer to produce a deduction that the existing review
 * gate necessarily rejects. For technological/empirical endpoints, focus this
 * bounded composer on actual use rather than deductions of device existence or
 * measured outcomes. Formal theorem endpoints retain deductions. This narrows
 * proposals, never changes the shared registry or grants approval.
 */
export function compositionRegistry(
  nodes: { kind: string; role?: string }[],
  registry: Registry,
): Registry {
  const operationalResult = nodes.some(
    (n) =>
      n.role === "frontier" &&
      [...operationalKinds, "empirical_finding"].includes(n.kind),
  );
  return nodes.length &&
    (operationalResult || nodes.every((n) => operationalKinds.includes(n.kind)))
    ? Object.fromEntries(
        Object.entries(registry).filter(([key]) => key !== "premise_for"),
      )
    : registry;
}

/** Literal example text needs a new composition, not a formatting repair. */
export function isTemplateDraft(value: unknown): boolean {
  const data = object(value);
  const nodes = ["nodes", "result", "roots", "steps"].flatMap((key) =>
    Array.isArray(data[key])
      ? (data[key] as unknown[])
      : data[key]
        ? [data[key]]
        : [],
  );
  return (
    nodes.length > 0 &&
    nodes.every(
      (n) =>
        object(n).claim === SCHEMA.nodes[0].claim &&
        object(n).title === SCHEMA.nodes[0].title,
    )
  );
}

function classificationErrors(
  node: Record<string, unknown>,
  label: string,
): string[] {
  return (
    [
      ["subject", subjects],
      ["kind", insightKinds],
    ] as const
  )
    .filter(([field, allowed]) => !allowed.includes(String(node[field])))
    .map(
      ([field, allowed]) =>
        `${label}: ${field}=${String(node[field])} is not an allowed classification. Choose from ${allowed.join(", ")} without changing the scientific claim.`,
    );
}

/** Syntactically valid JSON can still put mechanisms in the roots array.
 * Do not silently truncate or relabel those records during assembly. Let the
 * bounded format repair move the original records; evidence review is later.
 */
export function draftContractErrors(value: unknown): string[] {
  const data = object(value);
  if (isTemplateDraft(value)) return []; // The agent's single semantic replacement handles this case.
  if (!["result", "roots", "steps"].some((key) => data[key] !== undefined))
    return Array.isArray(data.nodes)
      ? data.nodes.flatMap((n) =>
          classificationErrors(object(n), `Insight ${String(object(n).id)}`),
        )
      : [];
  const errors: string[] = [];
  for (const [key, maximum, roles] of [
    ["result", 1, ["frontier"]],
    ["roots", 2, ["foundation"]],
    ["steps", 5, ["bridge", "limitation"]],
  ] as const) {
    const raw = data[key];
    if (raw === undefined) continue; // Missing evidence may leave a section absent.
    const items = Array.isArray(raw) ? raw : [raw];
    if (items.length > maximum)
      errors.push(
        `${key} contains more than ${maximum} records; check for misplaced sections.`,
      );
    for (const item of items) {
      const node = object(item);
      if (typeof node.claim !== "string")
        errors.push(
          `${key} includes a non-insight item or misplaced section marker.`,
        );
      else if (
        node.role !== undefined &&
        !(roles as readonly unknown[]).includes(node.role)
      )
        errors.push(
          `${key} contains a record with role ${String(node.role)}; preserve it in its proper section.`,
        );
      if (typeof node.claim === "string")
        errors.push(
          ...classificationErrors(
            node,
            `${key} ${String(node.title || node.id || "")}`,
          ),
        );
    }
  }
  return errors;
}
const bounded = (maxLength: number): Schema => ({ type: "string", maxLength });
// Leave room for complete sentences. Tight character ceilings can make a
// constrained decoder end a factual explanation mid-sentence; token budgets
// and local import limits remain the resource boundary.
const string = bounded(500);
const boolean: Schema = { type: "boolean" };
const array = (items: Schema, maxItems: number): Schema => ({
  type: "array",
  items,
  maxItems,
});
const record = (properties: Record<string, Schema>): Schema => ({
  type: "object",
  properties,
  required: Object.keys(properties),
  additionalProperties: false,
});
export function outputSchema(stage: string, input: unknown): Schema {
  if (stage.startsWith("relation check"))
    return record({
      assessment: bounded(500),
      id: { type: "string", enum: [object(object(input).relation).id] },
      direction: { type: "string", enum: ["valid", "invalid", "unclear"] },
      scope: { type: "string", enum: ["valid", "invalid", "unclear"] },
      warrant: {
        type: "string",
        enum: ["supported", "unsupported", "unclear"],
      },
      ...(object(object(input).relation).predicate === "bounded_by"
        ? {
            endpoint_roles: record({
              from: {
                type: "string",
                enum: ["restricted_claim", "restricting_condition", "neither"],
              },
              to: {
                type: "string",
                enum: ["restricted_claim", "restricting_condition", "neither"],
              },
            }),
          }
        : {}),
      ...(object(object(input).relation).predicate === "premise_for"
        ? {
            connection_type: {
              type: "string",
              enum: [
                "deductive_derivation",
                "design_rationale",
                "component_use",
                "analogy",
                "unsupported",
              ],
            },
          }
        : {}),
    });
  if (stage === "research plan")
    return record({
      atlas_foundation_id: {
        type: "string",
        enum: [
          "",
          ...(Array.isArray(object(input).available_foundations)
            ? (object(input).available_foundations as unknown[])
            : []
          )
            .map((v) => object(v).id)
            .filter((v) => typeof v === "string"),
        ],
      },
      endpoint: string,
      topic: string,
      root_principle: bounded(80),
      mechanism: bounded(100),
      backbone: array(string, 6),
      foundations: array(bounded(100), 5),
      subjects: array({ type: "string", enum: subjects }, 3),
      queries: array(bounded(180), 4),
      gaps: array(string, 8),
    });
  if (stage === "evidence challenge") {
    const nodes = object(object(input).draft).nodes;
    const ids = (Array.isArray(nodes) ? nodes : []).map((n) => object(n).id);
    return record({
      node_checks: {
        ...array(
          record({
            assessment: bounded(160),
            id: ids.length ? { type: "string", enum: ids } : string,
            keep: boolean,
            reason: string,
            attribution_supported: boolean,
            date_supported: boolean,
            assessed_role: {
              type: "string",
              enum: [
                "general_foundation",
                "requested_result",
                "supporting_idea",
                "limiting_condition",
              ],
            },
          }),
          ids.length,
        ),
        minItems: ids.length,
      },
      relation_checks: array(
        record({
          id: string,
          scope_matches_endpoints: boolean,
          direction_correct: boolean,
          warrant_supported: boolean,
          keep: boolean,
          reason: string,
        }),
        48,
      ),
      gaps: array(string, 4),
    });
  }
  const data = object(input);
  const sourceIds = (Array.isArray(data.sources) ? data.sources : [])
    .map((s) => object(s).id)
    .filter((id): id is string => typeof id === "string");
  const predicates = Object.keys(object(data.registry));
  const anchorIds = [
    ...new Set(
      (Array.isArray(data.sources) ? data.sources : []).flatMap((s) => {
        const passages = object(s).excerpts;
        return (Array.isArray(passages) ? passages : [])
          .map((p) => object(p).anchor)
          .filter((id): id is string => typeof id === "string");
      }),
    ),
  ];
  const nodeIds = (Array.isArray(data.nodes) ? data.nodes : [])
    .map((n) => object(n).id)
    .filter((id): id is string => typeof id === "string");
  if (data.refinement) nodeIds.push(...additionIds);
  const endpoint = nodeIds.length ? { type: "string", enum: nodeIds } : string;
  const evidence = {
    ...array(
      record({
        source: sourceIds.length ? { type: "string", enum: sourceIds } : string,
        anchor: anchorIds.length ? { type: "string", enum: anchorIds } : string,
      }),
      5,
    ),
    minItems: 1,
  };
  const shape = {
    title: string,
    summary: string,
    nodes: array(
      record({
        id: string,
        title: bounded(100),
        claim: string,
        problem: bounded(120),
        move: bounded(140),
        explanation: bounded(600),
        assumptions: array(bounded(100), 2),
        limitations: array(bounded(100), 2),
        attribution: array(string, 12),
        year: { type: ["integer", "null"] },
        subject: { type: "string", enum: subjects },
        kind: { type: "string", enum: insightKinds },
        role: {
          type: "string",
          enum: ["foundation", "bridge", "frontier", "limitation"],
        },
        evidence,
      }),
      10,
    ),
    relations: array(
      record({
        id: string,
        from: { ...array(endpoint, 8), minItems: 1 },
        to: endpoint,
        predicate: predicates.length
          ? { type: "string", enum: predicates }
          : string,
        warrant: bounded(300),
        scope: bounded(180),
        basis: {
          type: "string",
          enum: ["documented", "synthesis", "teaching"],
        },
        steps: array(bounded(160), 3),
        evidence,
      }),
      18,
    ),
    gaps: array(string, 12),
  };
  if (stage === "connect insights")
    return record({
      ...(data.refinement
        ? {
            additions: array(
              {
                ...(shape.nodes as { items: Schema }).items,
                properties: {
                  ...object(
                    object((shape.nodes as { items: Schema }).items).properties,
                  ),
                  id: { type: "string", enum: additionIds },
                  role: {
                    type: "string",
                    enum: additionRoles(
                      (Array.isArray(data.nodes) ? data.nodes : []).map(
                        (n) => ({ role: String(object(n).role) }),
                      ),
                    ),
                  },
                },
              },
              2,
            ),
          }
        : {}),
      relations: array((shape.relations as { items: Schema }).items, 10),
      gaps: array(string, 6),
    });
  const node = (shape.nodes as { items: Schema }).items;
  // An unknown discovery date is allowed to be absent. Some constrained
  // decoders stall on a required nullable scalar; local validation still
  // normalizes omission to null and never infers a date from publication year.
  node.required = (node.required as string[]).filter((key) => key !== "year");
  const withRoles = (roles: string[]) => ({
    ...node,
    properties: {
      ...object(node.properties),
      role: { type: "string", enum: roles },
    },
  });
  return record({
    title: shape.title,
    summary: shape.summary,
    result: array(withRoles(["frontier"]), 1),
    roots: array(withRoles(["foundation"]), 2),
    steps: array(withRoles(["bridge", "limitation"]), 5),
    gaps: shape.gaps,
  });
}

/** Provider JSON mode does not enforce enums. Catch identity/vocabulary mistakes
 * before they silently consume the semantic-refinement allowance. A formatting
 * repair may recover only an unambiguous existing intent, never invent an edge.
 */
export function connectionContractErrors(
  raw: unknown,
  input: unknown,
): string[] {
  const data = object(input),
    value = object(raw);
  if (!Array.isArray(data.nodes) || !Array.isArray(value.relations)) return [];
  const ids = new Set(data.nodes.map((n) => String(object(n).id)));
  if (data.refinement && Array.isArray(value.additions))
    for (const n of value.additions)
      if (additionIds.includes(String(object(n).id)))
        ids.add(String(object(n).id));
  const predicates = Object.keys(object(data.registry));
  const errors: string[] = [];
  if (data.refinement && Array.isArray(value.additions))
    for (const n of value.additions)
      errors.push(
        ...classificationErrors(object(n), `Addition ${String(object(n).id)}`),
      );
  for (const item of value.relations) {
    const r = object(item),
      from = r.from ?? r.premises,
      to = r.to ?? r.conclusion;
    if (
      !Array.isArray(from) ||
      !from.length ||
      !from.every((id) => ids.has(String(id))) ||
      !ids.has(String(to))
    )
      errors.push(
        `Relation ${String(r.id)} uses missing or unknown insight endpoints. Source IDs are not insight IDs.`,
      );
    if (predicates.length && !predicates.includes(String(r.predicate)))
      errors.push(
        `Relation ${String(r.id)} uses invalid predicate=${String(r.predicate)}. Allowed predicates: ${predicates.join(", ")}. Evidence bases and layer names are not predicates; an explicit reading-aid relationship uses prerequisite_for_reading. Recover only its existing meaning, otherwise omit it.`,
      );
  }
  return errors.slice(0, 8);
}
