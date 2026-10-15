import { useState } from "react";
import { SearchData, COLORS, words } from "./types";
import { RichText } from "./RichText";
import { PersonCard, TopicLinks } from "./People";
export function SearchResults({
  data,
  query,
  human,
  onIdea,
  onPerson,
  onTopic,
  selected,
  onPage,
}: {
  data: SearchData;
  query: string;
  human: boolean;
  onIdea: (id: string) => void;
  onPerson: (id: string) => void;
  onTopic: (id: string) => void;
  selected?: string;
  onPage: (offset: number) => void;
}) {
  const [filter, setFilter] = useState<"all" | "ideas" | "people" | "topics">(
    "all",
  );
  const total = Math.max(
    data.totals.ideas,
    data.totals.people,
    data.totals.topics,
  );
  const count = data.results.length + data.people.length + data.topics.length;
  return (
    <section className="search-results">
      <div className="section-head">
        <h2>Search results for “{query}”</h2>
        <span>{count} shown</span>
      </div>
      <div className="search-filters" aria-label="Result types">
        {(["all", "ideas", "people", "topics"] as const).map((k) => (
          <button
            key={k}
            aria-pressed={filter === k}
            className={filter === k ? "active" : ""}
            onClick={() => setFilter(k)}
          >
            {k === "all"
              ? "All results"
              : k === "people"
                ? "Scientists & contributors"
                : k === "ideas"
                  ? "Ideas"
                  : "Topics"}
            {k !== "all" && ` · ${data.totals[k]}`}
          </button>
        ))}
      </div>
      {!count && (
        <div className="empty-state">
          <h3>No matches in this release</h3>
          <p>
            {human
              ? "No matching human-reviewed records are available."
              : "Try a related term or a scientist’s name. Missing results can also be coverage gaps."}
          </p>
        </div>
      )}
      {(filter === "all" || filter === "people") && !!data.people.length && (
        <section aria-label="Matching scientists and contributors">
          <h3>Scientists & contributors</h3>
          <div className="people-grid">
            {data.people.map((p) => (
              <PersonCard
                key={p.id}
                person={p}
                onClick={() => onPerson(p.id)}
              />
            ))}
          </div>
        </section>
      )}
      {(filter === "all" || filter === "topics") && !!data.topics.length && (
        <section aria-label="Matching topics">
          <h3>Topics</h3>
          <TopicLinks topics={data.topics} onTopic={onTopic} />
        </section>
      )}
      {(filter === "all" || filter === "ideas") && (
        <section aria-label="Matching ideas">
          <h3>Ideas · {data.totals.ideas}</h3>
          {data.results.map((n) => (
            <button
              className={`result-card ${selected === n.id ? "selected" : ""}`}
              aria-current={selected === n.id ? "true" : undefined}
              key={n.id}
              onClick={() => onIdea(n.id)}
            >
              <span className="eyebrow" style={{ color: COLORS[n.pillar] }}>
                {words(n.pillar)} · {n.date.year || "Date uncertain"}
              </span>
              <h3>
                <RichText text={n.title} />
              </h3>
              <p>
                <RichText text={n.claim} />
              </p>
              <span className="text-link">
                Read idea & explore its topics ↗
              </span>
            </button>
          ))}
        </section>
      )}
      {filter !== "all" && data.totals[filter] === 0 && (
        <p className="notice">
          No {filter === "people" ? "scientists or contributors" : filter} match
          this search in the current release.
        </p>
      )}
      <div className="pagination">
        <button
          disabled={!data.offset}
          onClick={() => onPage(Math.max(0, data.offset - data.limit))}
        >
          Previous results
        </button>
        <span>
          Page {Math.floor(data.offset / data.limit) + 1} of{" "}
          {Math.max(1, Math.ceil(total / data.limit))}
        </span>
        <button
          disabled={data.offset + data.limit >= total}
          onClick={() => onPage(data.offset + data.limit)}
        >
          Next results
        </button>
      </div>
    </section>
  );
}
