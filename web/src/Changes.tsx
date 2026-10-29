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
  offset?: number;
  limit?: number;
  totals?: Record<"added" | "removed" | "changed", number>;
  record_counts?: Record<
    "added" | "removed" | "changed",
    Record<string, number>
  >;
  catalog_changes?: Record<
    string,
    { added: string[]; removed: string[]; changed: string[] }
  >;
  added: ChangeRef[];
  removed: ChangeRef[];
  changed: { before: ChangeRef; after: ChangeRef }[];
};
export function Changes({
  data,
  onInspect,
  onMore,
  loading = false,
}: {
  data: ReleaseChanges;
  onInspect: (id: string, relation: boolean, snapshot: string) => void;
  onMore?: () => void;
  loading?: boolean;
}) {
  const [legacyLimit, setLimit] = useState(20);
  const limit = data.limit ? Infinity : legacyLimit;
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
          <strong>{data.totals?.added ?? additions.length}</strong> new
          contributions & connections
        </span>
        <span>
          <strong>{data.totals?.changed ?? changed.length}</strong> revised
        </span>
        <span>
          <strong>{data.totals?.removed ?? removals.length}</strong> removed
          from this snapshot
        </span>
      </div>
      {data.catalog_changes && (
        <details className="notice">
          <summary>Catalog changes: topics, works and people</summary>
          <p>
            Catalog entries describe selected works and contributors. They are
            counted separately from extracted insights.
          </p>
          {Object.entries(data.catalog_changes).map(([kind, changes]) => (
            <p key={kind}>
              {kind === "dossiers" ? "Topics" : words(kind)}:{" "}
              {changes.added.length} added, {changes.changed.length} revised,{" "}
              {changes.removed.length} removed from the current catalog. Earlier
              profiles remain available in the earlier snapshot.
            </p>
          ))}
        </details>
      )}
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
      {(data.totals
        ? Math.max(...Object.values(data.totals)) >
          (data.offset || 0) + (data.limit || 0)
        : Math.max(additions.length, removals.length, changed.length) >
          limit) && (
        <button
          disabled={loading}
          onClick={() => (onMore ? onMore() : setLimit((n) => n + 30))}
        >
          {loading ? "Loading changes…" : "Show more changes"}
        </button>
      )}
      <details className="notice">
        <summary>Sources and review records</summary>
        <p>
          {data.record_counts?.added.source ??
            data.added.filter((r) => r.type === "source").length}{" "}
          new sources;{" "}
          {data.record_counts?.added.review ??
            data.added.filter((r) => r.type === "review").length}{" "}
          new review records;{" "}
          {data.record_counts?.changed.source ??
            data.changed.filter((r) => r.after.type === "source").length}{" "}
          source revisions. Review records remain attached to the exact content
          they checked.
        </p>
      </details>
      {!additions.length && !changed.length && !removals.length && (
        <p>No contribution or relationship changes between these snapshots.</p>
      )}
    </div>
  );
}
