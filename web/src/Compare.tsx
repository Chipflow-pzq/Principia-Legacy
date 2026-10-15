import { useEffect, useRef, useState } from "react";
import { api, Contribution, words } from "./types";
import { RichText } from "./Inspector";

export type ComparedContribution = Contribution & { snapshot_id: string };

export function Compare({
  records,
  suggestions,
  release,
  onAdd,
  onRemove,
  onClose,
  onInspect,
}: {
  records: ComparedContribution[];
  suggestions: Contribution[];
  release: string;
  onAdd: (id: string, snapshot: string) => void;
  onRemove: (id: string, snapshot: string) => void;
  onClose: () => void;
  onInspect: (id: string, snapshot: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Contribution[]>([]);
  const [error, setError] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    (input.current || panel.current)?.focus({ preventScroll: true });
    return () => {
      if (previous?.isConnected) previous.focus({ preventScroll: true });
    };
  }, []);
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(
      () =>
        api<{ results: Contribution[] }>(
          "search",
          { q: query, release, limit: 15 },
          controller.signal,
        )
          .then((r) => {
            setResults(r.results);
            setError("");
          })
          .catch((e) => {
            if (e.name !== "AbortError") setError(e.message);
          }),
      180,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, release]);
  const options = (query.trim() ? results : suggestions)
    .filter(
      (n) => !records.some((r) => r.id === n.id && r.snapshot_id === release),
    )
    .slice(0, 12);
  return (
    <section
      className="compare-tray"
      role="dialog"
      ref={panel}
      tabIndex={-1}
      aria-label="Compare contributions"
    >
      <div className="section-head">
        <div>
          <h2>Compare two ideas</h2>
          <p className="muted">
            Read their claims, assumptions, and limits side by side.
          </p>
        </div>
        <button onClick={onClose} aria-label="Close comparison">
          Close ×
        </button>
      </div>
      <div className="compare-columns">
        {records.map((n) => (
          <article key={`${n.id}:${n.snapshot_id}`}>
            <div className="section-head">
              <span className="eyebrow">{words(n.pillar)}</span>
              <button
                aria-label={`Remove ${n.title} from comparison`}
                onClick={() => onRemove(n.id, n.snapshot_id)}
              >
                ×
              </button>
            </div>
            <h3>
              <RichText text={n.title} />
            </h3>
            <p className="muted">
              Revision {n.revision} · {n.snapshot_id}
            </p>
            <p>
              <RichText text={n.claim} />
            </p>
            <h4>The key idea</h4>
            <p>
              <RichText text={n.conceptual_move} />
            </p>
            <h4>Assumptions</h4>
            <ul>
              {n.assumptions.map((s, i) => (
                <li key={i}>
                  <RichText text={s} />
                </li>
              ))}
            </ul>
            <h4>Limits</h4>
            <ul>
              {n.limits.map((s, i) => (
                <li key={i}>
                  <RichText text={s} />
                </li>
              ))}
            </ul>
            <button onClick={() => onInspect(n.id, n.snapshot_id)}>
              Inspect evidence ↗
            </button>
          </article>
        ))}
        {records.length < 2 && (
          <div className="compare-picker">
            <h3>Choose the second idea</h3>
            <label>
              Search this release
              <input
                ref={input}
                aria-label="Find a contribution to compare"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Try attention, causality, or entropy…"
              />
            </label>
            <p className="muted">
              {query ? "Search results" : "From the map you are reading"}
            </p>
            {error && <p role="alert">{error}</p>}
            <div className="compare-options">
              {options.map((n) => (
                <button key={n.id} onClick={() => onAdd(n.id, release)}>
                  {n.title}
                  <span>
                    {n.date.year || "Date uncertain"} · {words(n.pillar)}
                  </span>
                </button>
              ))}
            </div>
            {!options.length && (
              <p className="muted">
                {query
                  ? "No matches. Try a shorter search."
                  : "Search above to choose any idea in this release."}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
