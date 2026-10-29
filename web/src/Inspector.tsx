import { useEffect, useRef, useState } from "react";
import { RichText } from "./RichText";
export { RichText } from "./RichText";
import { Contribution, Inspection, Relation, words } from "./types";
import { WorkCards } from "./Works";
import { TopicLinks } from "./People";
export function Inspector({
  data,
  onClose,
  onTrace,
  onCompare,
  onSelect,
  onTopic,
  onPerson,
  onWork,
  searchNavigation,
  onReturnToSearch,
}: {
  data: Inspection;
  onClose: () => void;
  onTrace: (id: string) => void;
  onCompare: (id: string) => void;
  onSelect: (id: string) => void;
  onTopic: (id: string) => void;
  onPerson: (id: string) => void;
  onWork: (id: string) => void;
  onReturnToSearch?: () => void;
  searchNavigation?: {
    index: number;
    total: number;
    previous?: () => void;
    next?: () => void;
  };
}) {
  const [depth, setDepth] = useState<"insight" | "evidence">("insight");
  const panel = useRef<HTMLElement>(null);
  const r = data.record;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    if (window.matchMedia("(max-width: 900px)").matches) {
      panel.current?.scrollIntoView({ block: "start", behavior: "instant" });
    }
    panel.current?.focus({ preventScroll: true });
    return () => {
      if (previous?.isConnected) previous.focus({ preventScroll: true });
    };
  }, [r.id, r.revision, data.release_id]);
  const node = r.type === "contribution" ? (r as Contribution) : null;
  const edge = r.type === "relation" ? (r as Relation) : null;
  return (
    <aside
      className="inspector"
      aria-label="Record inspector"
      ref={panel}
      tabIndex={-1}
    >
      <div className="inspector-top">
        <span>
          {node ? "CONTRIBUTION" : "RELATIONSHIP"} · REV {r.revision}
        </span>
        <button aria-label="Close inspector" onClick={onClose}>
          ×
        </button>
      </div>
      {(searchNavigation || onReturnToSearch) && (
        <nav
          className="inspector-search-nav"
          aria-label="Search result navigation"
        >
          <button
            onClick={onReturnToSearch || onClose}
            aria-label="Back to search results"
          >
            ← Back to results
          </button>
          {searchNavigation && (
            <>
              <span>
                {searchNavigation.index + 1} of {searchNavigation.total}
              </span>
              <button
                aria-label="Previous search result"
                disabled={!searchNavigation.previous}
                onClick={searchNavigation.previous}
              >
                ←
              </button>
              <button
                aria-label="Next search result"
                disabled={!searchNavigation.next}
                onClick={searchNavigation.next}
              >
                →
              </button>
            </>
          )}
        </nav>
      )}
      <div className="inspector-body" aria-busy={data.pending || false}>
        {data.pending && (
          <p className="muted" role="status">
            Loading sources and review…
          </p>
        )}
        <div className="record-badges">
          <span className="badge">Machine-screened</span>
          <span className="muted">
            Human review: {words(r.effective_human_review || r.human_review)}
          </span>
        </div>
        <h2>
          <RichText text={node?.title || "Why is this arrow here?"} />
        </h2>
        {node && (
          <div className="attribution">
            {data.people?.length
              ? data.people.map((p) => (
                  <button
                    className="person-credit"
                    key={p.id}
                    onClick={() => onPerson(p.id)}
                  >
                    {p.name} ↗
                  </button>
                ))
              : node.attribution
                  .filter(
                    (a) =>
                      a.role !== "unknown" &&
                      a.name.toLowerCase() !== "unknown",
                  )
                  .map((a) => a.name)
                  .join(" · ") || "Attribution not established"}
            <span>
              {node.date.year || "Date uncertain"} · {words(node.kind)}
            </span>
          </div>
        )}
        {node && (
          <p className="claim">
            <RichText text={node.claim} />
          </p>
        )}
        {edge && (
          <p className="relation-type">
            {words(edge.predicate)} <span> / {words(edge.layer)}</span>
          </p>
        )}
        {node && (
          <>
            {!!data.works?.length && (
              <section>
                <h3>Works explaining this insight</h3>
                <WorkCards works={data.works} onWork={onWork} />
              </section>
            )}
            <section className="insight-topics">
              <h3>Explore this idea in</h3>
              <TopicLinks topics={data.topics || []} onTopic={onTopic} />
              <p className="muted">
                Open a topic to see the wider story. Use Trace to follow this
                idea’s evidenced connections.
              </p>
            </section>
          </>
        )}
        <div className="tabs">
          <button
            className={depth === "insight" ? "active" : ""}
            onClick={() => setDepth("insight")}
          >
            The insight
          </button>
          <button
            className={depth === "evidence" ? "active" : ""}
            disabled={data.pending}
            onClick={() => setDepth("evidence")}
          >
            Sources & review{" "}
            <span>{data.pending ? "…" : data.sources.length}</span>
          </button>
        </div>
        {depth === "insight" && node && (
          <>
            <section>
              <h3>The question</h3>
              <p>
                <RichText text={node.problem} />
              </p>
            </section>
            <section className="conceptual-move">
              <h3>The key idea</h3>
              <p>
                <RichText text={node.conceptual_move} />
              </p>
            </section>
            <section>
              <h3>Understand it</h3>
              <p className="explanation">
                <RichText text={node.explanation} />
              </p>
            </section>
            <section>
              <h3>Assumptions</h3>
              <ul>
                {node.assumptions.map((s, i) => (
                  <li key={i}>
                    <RichText text={s} />
                  </li>
                ))}
              </ul>
            </section>
            <section className="limits">
              <h3>Limits and open questions</h3>
              <ul>
                {node.limits.map((s, i) => (
                  <li key={i}>
                    <RichText text={s} />
                  </li>
                ))}
              </ul>
            </section>
            {data.idea_families?.map((f) => (
              <section key={f.id}>
                <h3>{f.title}</h3>
                <p className="muted">{f.description}</p>
                {f.members
                  .filter((m) => m.id !== node.id)
                  .map((m) => (
                    <button
                      className="record-link"
                      key={m.id}
                      onClick={() => onSelect(m.id)}
                    >
                      {m.title} ↗
                    </button>
                  ))}
              </section>
            ))}
            <div className="standing">
              Scientific standing: {node.scientific_standing}
            </div>
            <div className="inspector-actions">
              <button className="primary" onClick={() => onTrace(node.id)}>
                Trace its connections ↗
              </button>
              <button onClick={() => onCompare(node.id)}>Compare</button>
            </div>
          </>
        )}
        {depth === "insight" && edge && (
          <>
            <p className="claim">
              <RichText text={edge.warrant} />
            </p>
            <section>
              <h3>Applies within</h3>
              <p>
                <RichText text={edge.scope} />
              </p>
            </section>
            <section>
              <h3>
                {edge.premises.length > 1
                  ? "All of these premises together"
                  : "From contribution"}
              </h3>
              {edge.premises.map((p) => (
                <button
                  className="record-link"
                  key={p.id}
                  onClick={() => onSelect(p.id)}
                >
                  {data.endpoints?.find((e) => e.id === p.id)?.title || p.id} ·
                  revision {p.revision} ↗
                </button>
              ))}
              <h3>To contribution</h3>
              <button
                className="record-link"
                onClick={() => onSelect(edge.conclusion.id)}
              >
                {data.endpoints?.find((e) => e.id === edge.conclusion.id)
                  ?.title || edge.conclusion.id}{" "}
                · revision {edge.conclusion.revision} ↗
              </button>
            </section>
            <p className="notice">
              This {edge.layer} relationship does not imply other relationship
              types. A documented historical route is not necessarily exclusive
              ancestry.
            </p>
          </>
        )}
        {depth === "evidence" && (
          <>
            <p className="notice">
              Source passages were obtained and machine-checked. This is not
              human or domain-expert approval. Original documents open only when
              you follow a source link.
            </p>
            {data.sources.map((s) => (
              <section className="source-card" key={`${s.id}:${s.revision}`}>
                <h3>
                  <a href={s.url} target="_blank" rel="noopener noreferrer">
                    <RichText text={s.title} /> ↗
                  </a>
                </h3>
                <p className="muted">
                  {s.creators.slice(0, 5).join(", ")}
                  {s.creators.length > 5 ? " and collaborators" : ""}
                </p>
                {s.anchors
                  .filter((a) =>
                    r.anchors.some(
                      (ref) =>
                        ref.source_id === s.id &&
                        ref.source_revision === s.revision &&
                        ref.anchor_id === a.id,
                    ),
                  )
                  .map((a) => (
                    <div className="anchor" key={a.id}>
                      <strong>{a.selector}</strong>
                      <p>
                        <RichText text={a.summary} />
                      </p>
                      <details className="passage-verification">
                        <summary>Passage verification details</summary>
                        <p>
                          This fingerprint identifies the retrieved passage. It
                          does not establish that the scientific claim is
                          correct.
                        </p>
                        <code>{a.text_hash}</code>
                      </details>
                    </div>
                  ))}
                <details>
                  <summary>Access, version & rights</summary>
                  <p>
                    Revision {s.revision} · {words(s.access_state)}.{" "}
                    {s.rights.license}
                  </p>
                  <p>{s.rights.distributed_material}</p>
                  <code>{s.source_version}</code>
                </details>
              </section>
            ))}
            <section>
              <h3>Review record</h3>
              {data.reviews.map((v, i) => (
                <details key={i}>
                  <summary>
                    {words(v.reviewer_type)} · {words(v.scope)}
                  </summary>
                  <p>
                    <RichText text={v.rationale} />
                  </p>
                  <p className="muted">{v.reviewer_identity}</p>
                </details>
              ))}
            </section>
            {node && (
              <section>
                <h3>Attribution notes</h3>
                <p>
                  {node.date.year ?? "Unknown year"} · {node.date.precision}{" "}
                  precision · {node.date.event}. {node.date.note}
                </p>
                {node.attribution.map((a, i) => (
                  <p key={i}>
                    <strong>{a.name}</strong> — {a.evidence_note || a.role}
                  </p>
                ))}
              </section>
            )}
          </>
        )}
      </div>
      <footer className="record-footer">
        <code>{r.id}</code>
        <span>{data.release_id}</span>
      </footer>
    </aside>
  );
}
