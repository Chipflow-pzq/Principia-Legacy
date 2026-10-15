import { useState } from "react";
import { words } from "./types";
import { RichText } from "./Inspector";
type ChangeRef = {
  id: string;
  revision: number;
  title: string;
  type: string;
  publication_state: string | null;
  visible: boolean;
};
export type ReleaseChanges = {
  release_id: string;
  from_release: string;
  added: ChangeRef[];
  removed: ChangeRef[];
  changed: { before: ChangeRef; after: ChangeRef }[];
};
export function Changes({
  data,
  onInspect,
}: {
  data: ReleaseChanges;
  onInspect: (id: string, relation: boolean, snapshot: string) => void;
}) {
  const [limit, setLimit] = useState(20);
  const additions = data.added.filter(
    (r) => r.type === "contribution" || r.type === "relation",
  );
  const removals = data.removed.filter(
    (r) => r.type === "contribution" || r.type === "relation",
  );
  const changed = data.changed.filter(
    (r) => r.after.type === "contribution" || r.after.type === "relation",
  );
  const open = (r: ChangeRef, snapshot: string) =>
    r.visible ? (
      <button
        className="text-link"
        onClick={() => onInspect(r.id, r.type === "relation", snapshot)}
      >
        Inspect revision {r.revision} ↗
      </button>
    ) : (
      <span className="muted">
        {words(r.publication_state || "unavailable")}; requires recheck
      </span>
    );
  return (
    <div className="release-changes">
      <p className="notice">
        {data.from_release} → {data.release_id}
      </p>
      <div className="hero-stats">
        <span>
          <strong>{additions.length}</strong> new contributions & connections
        </span>
        <span>
          <strong>{changed.length}</strong> revised
        </span>
        <span>
          <strong>{removals.length}</strong> removed from this snapshot
        </span>
      </div>
      {!!changed.length && (
        <section>
          <h2>Revised understanding</h2>
          {changed.slice(0, limit).map((r) => (
            <article className="change-card" key={r.after.id}>
              <span className="eyebrow">
                {words(r.after.type)} · revision {r.before.revision} →{" "}
                {r.after.revision}
              </span>
              <h3>
                <RichText text={r.after.title} />
              </h3>
              <div className="change-actions">
                {open(r.before, data.from_release)}
                {open(r.after, data.release_id)}
              </div>
            </article>
          ))}
        </section>
      )}
      {!!additions.length && (
        <section>
          <h2>New to this snapshot</h2>
          {additions.slice(0, limit).map((r) => (
            <article className="change-card" key={r.id}>
              <span className="eyebrow">{words(r.type)}</span>
              <h3>
                <RichText text={r.title} />
              </h3>
              {open(r, data.release_id)}
            </article>
          ))}
        </section>
      )}
      {!!removals.length && (
        <section>
          <h2>Preserved in the earlier snapshot</h2>
          {removals.slice(0, limit).map((r) => (
            <article className="change-card" key={r.id}>
              <h3>
                <RichText text={r.title} />
              </h3>
              {open(r, data.from_release)}
            </article>
          ))}
        </section>
      )}
      {Math.max(additions.length, removals.length, changed.length) > limit && (
        <button onClick={() => setLimit((n) => n + 30)}>
          Show more changes
        </button>
      )}
      <details className="notice">
        <summary>Sources and review records</summary>
        <p>
          {data.added.filter((r) => r.type === "source").length} new sources;{" "}
          {data.added.filter((r) => r.type === "review").length} new review
          records;{" "}
          {data.changed.filter((r) => r.after.type === "source").length} source
          revisions. Review records remain attached to the exact content they
          checked.
        </p>
      </details>
      {!additions.length && !changed.length && !removals.length && (
        <p>No contribution or relationship changes between these snapshots.</p>
      )}
    </div>
  );
}
