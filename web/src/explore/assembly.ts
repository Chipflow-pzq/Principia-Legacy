import { object, strings } from "./model";

/** Neutral arrow names avoid treating every relationship as an inference.
 * Portable maps retain the existing premises/conclusion representation.
 * Conflicting representations remain invalid; never guess or reverse an arrow.
 */
export function assembleConnection(raw: unknown) {
  const value = object(raw);
  if (value.from === undefined && value.to === undefined) return value;
  const conflicts =
    (value.premises !== undefined &&
      JSON.stringify(value.premises) !== JSON.stringify(value.from)) ||
    (value.conclusion !== undefined && value.conclusion !== value.to);
  return {
    ...value,
    premises: conflicts ? [] : value.from,
    conclusion: conflicts ? "" : value.to,
  };
}

/** Normalize complete insight sections and earlier draft shapes. Never infer arrows. */
export function assembleDraft(raw: unknown): Record<string, unknown> {
  const data = object(raw);
  // JSON-object mode sometimes uses a single record for a one-item section.
  // Wrapping that exact record is lossless; dropping it can erase the frontier.
  const sectionItems = (key: string): unknown[] =>
    Array.isArray(data[key])
      ? (data[key] as unknown[])
      : data[key] && typeof data[key] === "object"
        ? [data[key]]
        : [];
  if (
    ["result", "roots", "steps"].some(
      (key) => Array.isArray(data[key]) || sectionItems(key).length,
    )
  ) {
    const section = (key: string, count: number, role?: string) =>
      sectionItems(key)
        .slice(0, count)
        .map((value, i) => ({
          ...object(value),
          // No arrows exist in this pass. Assign disjoint, streaming-stable
          // identities rather than trusting IDs repeated across model sections.
          id: `${key}-${i + 1}`,
          role:
            role ||
            (object(value).role === "limitation" ? "limitation" : "bridge"),
        }));
    // A single result slot prevents multiple applications from masquerading as
    // the requested endpoint. Missing evidence can leave any section empty.
    return {
      title: data.title,
      summary: data.summary,
      nodes: [
        ...section("roots", 2, "foundation"),
        ...section("steps", 5),
        ...section("result", 1, "frontier"),
      ],
      relations: [],
      gaps: strings(data.gaps, 20),
    };
  }
  if (Array.isArray(data.map)) {
    const nodes: Record<string, unknown>[] = [],
      relations: Record<string, unknown>[] = [],
      gaps = strings(data.gaps, 20);
    for (const item of data.map.slice(0, 7)) {
      const unit = object(item),
        node = object(unit.insight);
      nodes.push(node);
      for (const raw of (Array.isArray(unit.links) ? unit.links : []).slice(
        0,
        2,
      )) {
        const link = object(raw);
        if (
          link.conclusion === node.id ||
          (Array.isArray(link.premises) && link.premises.includes(node.id))
        )
          relations.push(link);
        else
          gaps.push(
            "A proposed connection did not involve its insight and was withheld.",
          );
      }
    }
    return { title: data.title, summary: data.summary, nodes, relations, gaps };
  }
  // Older checkpoints and portable drafts use the flat representation.
  if (!Array.isArray(data.backbone) && !Array.isArray(data.branches))
    return data;
  const backbone = Array.isArray(data.backbone)
    ? data.backbone.slice(0, 7)
    : [];
  const branches = Array.isArray(data.branches)
    ? data.branches.slice(0, 2)
    : [];
  const nodes: Record<string, unknown>[] = [],
    relations: Record<string, unknown>[] = [];
  const gaps = strings(data.gaps, 20);
  for (let i = 0; i < backbone.length; i++) {
    const unit = object(backbone[i]),
      node = object(unit.insight);
    nodes.push(node);
    if (!unit.connection_from_previous) continue;
    const link = object(unit.connection_from_previous);
    const previous = i ? object(object(backbone[i - 1]).insight).id : undefined;
    if (
      previous &&
      link.conclusion === node.id &&
      Array.isArray(link.premises) &&
      link.premises.includes(previous)
    )
      relations.push(link);
    else
      gaps.push(
        "A proposed backbone link did not join consecutive insights and was withheld.",
      );
  }
  for (const raw of branches) {
    const unit = object(raw),
      node = object(unit.insight),
      link = object(unit.connection);
    nodes.push(node);
    if (!unit.connection) continue;
    if (
      link.conclusion === node.id ||
      (Array.isArray(link.premises) && link.premises.includes(node.id))
    )
      relations.push(link);
    else
      gaps.push(
        "A proposed branch link did not include its insight and was withheld.",
      );
  }
  return { title: data.title, summary: data.summary, nodes, relations, gaps };
}
