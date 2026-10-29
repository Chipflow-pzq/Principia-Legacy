import { useEffect, useRef, useState } from "react";
import { api, COLORS, Dossier, Contribution } from "./types";
import { usePageOffset } from "./usePageOffset";
import { RichText } from "./RichText";
import { CoveragePanel } from "./CoveragePanel";

export function TopicCatalog({
  release,
  pillar,
  area,
  coverage,
  offset,
  onChange,
  onTopic,
}: {
  release: string;
  pillar: string;
  area: string;
  coverage: string;
  offset: number;
  onChange: (value: { area: string; coverage: string; offset: number }) => void;
  onTopic: (id: string) => void;
}) {
  const [data, setData] = useState<{
    dossiers: Dossier[];
    total: number;
    areas: string[];
  } | null>(null);
  const [error, setError] = useState("");
  const [areaQuery, setAreaQuery] = useState("");
  const areaPicker = useRef<HTMLDetailsElement>(null);
  const areas = [...new Set([...(data?.areas || []), ...(area ? [area] : [])])];
  const matchingAreas = areas.filter((value) =>
    value.toLocaleLowerCase().includes(areaQuery.trim().toLocaleLowerCase()),
  );
  function selectArea(value: string) {
    onChange({ area: value, coverage, offset: 0 });
    setAreaQuery("");
    if (areaPicker.current) {
      areaPicker.current.open = false;
      areaPicker.current.querySelector("summary")?.focus();
    }
  }
  useEffect(() => {
    const c = new AbortController();
    setData(null);
    setError("");
    api<{ dossiers: Dossier[]; total: number; areas: string[] }>(
      "dossiers",
      {
        release,
        pillar,
        area,
        offset,
        limit: 60,
        summary: true,
        status:
          coverage === "available"
            ? "populated"
            : coverage === "ready"
              ? "route_ready"
              : coverage === "pending"
                ? "pending"
                : "",
      },
      c.signal,
    )
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, [release, pillar, area, coverage, offset]);
  return (
    <section className="all-dossiers" aria-label="Topic catalogue">
      <div className="section-heading">
        <h2>
          {(
            {
              mathematics: "Mathematics",
              physics: "Physics",
              computer_science: "Computer science",
              economics: "Economics",
              biology_medicine: "Biology & medicine",
            } as Record<string, string>
          )[pillar] || "Browse all topics"}
        </h2>
        <span aria-live="polite">
          {data ? `${data.total} topics` : "Loading topics…"}
        </span>
      </div>
      <CoveragePanel release={release} pillar={pillar} />
      <div className="catalog-filters">
        <details className="area-picker" ref={areaPicker}>
          <summary>{area ? `Area: ${area}` : "Refine by area"}</summary>
          <div className="area-options">
            <label htmlFor="find-area">Find an area</label>
            <input
              id="find-area"
              type="search"
              disabled={!data}
              value={areaQuery}
              placeholder="e.g. mechanics, genetics, algorithms"
              onChange={(e) => setAreaQuery(e.target.value)}
            />
            <button
              type="button"
              aria-pressed={!area}
              onClick={() => selectArea("")}
            >
              All areas
            </button>
            <div className="area-choices" aria-label="Matching areas">
              {matchingAreas.slice(0, 8).map((value) => (
                <button
                  type="button"
                  key={value}
                  aria-pressed={area === value}
                  onClick={() => selectArea(value)}
                >
                  {value}
                </button>
              ))}
            </div>
            <p role="status">
              {!data
                ? error
                  ? "Areas could not be loaded."
                  : "Loading areas…"
                : matchingAreas.length > 8
                  ? `Showing 8 of ${matchingAreas.length} areas. Type to narrow the list.`
                  : matchingAreas.length
                    ? `${matchingAreas.length} matching areas`
                    : "No matching areas. Try a broader term."}
            </p>
          </div>
        </details>
        <label>
          Coverage{" "}
          <select
            aria-label="Coverage"
            value={coverage}
            onChange={(e) =>
              onChange({ area, coverage: e.target.value, offset: 0 })
            }
          >
            <option value="all">All topics, including gaps</option>
            <option value="available">Ideas available</option>
            <option value="ready">Reading route checked by AI</option>
            <option value="pending">Awaiting evidence</option>
          </select>
        </label>
      </div>
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Loading topics…</p>}
      {data && (
        <>
          <div className="dossier-grid">
            {data.dossiers.map((d) => (
              <a
                id={`topic-card-${d.id}`}
                className="dossier-tile"
                key={d.id}
                href={`#dossier=${encodeURIComponent(d.id)}&release=${encodeURIComponent(release)}${pillar ? `&subject=${pillar}` : ""}`}
                onClick={(e) => {
                  if (
                    e.button === 0 &&
                    !e.metaKey &&
                    !e.ctrlKey &&
                    !e.shiftKey &&
                    !e.altKey
                  ) {
                    e.preventDefault();
                    onTopic(d.id);
                  }
                }}
              >
                <span
                  className="dossier-id"
                  style={{ color: COLORS[d.pillar] }}
                >
                  <span aria-hidden="true">▤</span>
                </span>
                <div>
                  {!pillar && (
                    <small className="topic-subject">
                      {d.pillar
                        .replaceAll("_", " ")
                        .replace("biology medicine", "Biology & medicine")}
                    </small>
                  )}
                  <h3>{d.title}</h3>
                  <span>
                    {d.contribution_count}{" "}
                    {d.contribution_count === 1 ? "insight" : "insights"} ·{" "}
                    {d.contribution_count
                      ? d.reading_route?.ready
                        ? "Reading route checked by AI"
                        : d.endpoint
                          ? "Endpoint available"
                          : "Foundations available"
                      : d.work_count
                        ? `${d.work_count} works · insights pending`
                        : "Awaiting sources"}
                  </span>
                </div>
                <span className="tile-arrow">↗</span>
              </a>
            ))}
          </div>
          {!data.total && (
            <p>
              No topics match these filters. Choose another area or include
              topics awaiting evidence.
            </p>
          )}
          {data.total > 60 && (
            <nav className="pagination" aria-label="Topic pages">
              <button
                disabled={!offset}
                onClick={() =>
                  onChange({ area, coverage, offset: Math.max(0, offset - 60) })
                }
              >
                Previous topics
              </button>
              <span aria-live="polite">
                {offset + 1}–{Math.min(offset + 60, data.total)} of {data.total}
              </span>
              <button
                disabled={offset + 60 >= data.total}
                onClick={() =>
                  onChange({ area, coverage, offset: offset + 60 })
                }
              >
                Next topics
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  );
}

export function TopicInsightList({
  topic,
  release,
  human,
  challenge,
  onSelect,
}: {
  topic: string;
  release: string;
  human: boolean;
  challenge: boolean;
  onSelect: (id: string) => void;
}) {
  const [offset, setOffset] = usePageOffset(
    "topicpage",
    `${topic}/${human}`,
    40,
  );
  const [data, setData] = useState<{
    contributions: Contribution[];
    total: number;
  } | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    setData(null);
    setError("");
    api<{ contributions: Contribution[]; total: number }>(
      `dossiers/${encodeURIComponent(topic)}/contributions`,
      { release, human, offset, limit: 40 },
      c.signal,
    )
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, [topic, release, human, offset]);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p role="status">Loading topic insights…</p>;
  return (
    <>
      <p className="muted">
        All {data.total} topic insights are available here. The map displays a
        bounded neighborhood.
        {challenge ? " Showing the limitations of each insight." : ""}
      </p>
      <div className="node-list">
        {data.contributions.map((n) => (
          <button key={n.id} onClick={() => onSelect(n.id)}>
            <span>{n.date.year || "—"}</span>
            <div>
              <h3>
                <RichText text={n.title} />
              </h3>
              <p>
                <RichText
                  text={
                    challenge
                      ? n.limits.join(" ") ||
                        "Limitations have not been established for this insight."
                      : n.claim
                  }
                />
              </p>
            </div>
            <span>↗</span>
          </button>
        ))}
      </div>
      {data.total > 40 && (
        <nav className="pagination" aria-label="Topic insight pages">
          <button
            disabled={!offset}
            onClick={() => setOffset(Math.max(0, offset - 40))}
          >
            Previous insights
          </button>
          <span>
            {offset + 1}–{Math.min(offset + 40, data.total)} of {data.total}
          </span>
          <button
            disabled={offset + 40 >= data.total}
            onClick={() => setOffset(offset + 40)}
          >
            Next insights
          </button>
        </nav>
      )}
    </>
  );
}
