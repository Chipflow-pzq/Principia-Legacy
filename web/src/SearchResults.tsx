import { SearchData, COLORS, words } from "./types";
import { WorkCards } from "./Works";
import { RichText } from "./RichText";
import { PersonCard, TopicLinks } from "./People";
export function SearchResults({
  data,
  filter,
  onFilter,
  query,
  human,
  onIdea,
  onWork,
  onPerson,
  onTopic,
  selected,
  onPage,
}: {
  data: SearchData;
  filter: "all" | "ideas" | "people" | "topics" | "works";
  onFilter: (filter: "all" | "ideas" | "people" | "topics" | "works") => void;
  query: string;
  human: boolean;
  onIdea: (id: string) => void;
  onWork: (id: string) => void;
  onPerson: (id: string) => void;
  onTopic: (id: string) => void;
  selected?: string;
  onPage: (offset: number) => void;
}) {
  const total =
    filter === "all"
      ? Math.max(
          data.totals.ideas,
          data.totals.people,
          data.totals.topics,
          data.totals.works || 0,
        )
      : data.totals[filter] || 0;
  const preview = <T,>(items: T[]) =>
    filter === "all" ? items.slice(0, 4) : items;
  const shown =
    filter === "all"
      ? [data.results, data.people, data.topics, data.works || []].reduce(
          (sum, rows) => sum + Math.min(4, rows.length),
          0,
        )
      : (filter === "ideas" ? data.results : data[filter] || []).length;
  const more = (
    kind: "ideas" | "people" | "topics" | "works",
    label: string,
  ) =>
    filter === "all" && (data.totals[kind] || 0) > 4 ? (
      <button className="text-link" onClick={() => onFilter(kind)}>
        See all {data.totals[kind]} {label} →
      </button>
    ) : null;
  return (
    <section className="search-results">
      <div className="section-head">
        <h2>Search results for “{query}”</h2>
        <span>{shown} shown</span>
      </div>
      <div className="search-filters" aria-label="Result types">
        {(["all", "topics", "works", "ideas", "people"] as const).map((k) => (
          <button
            key={k}
            aria-pressed={filter === k}
            className={filter === k ? "active" : ""}
            onClick={() => {
              onFilter(k);
            }}
          >
            {k === "all"
              ? "All results"
              : k === "people"
                ? "Scientists & contributors"
                : k === "ideas"
                  ? "Ideas"
                  : k === "works"
                    ? "Works"
                    : "Topics"}
            {k !== "all" && ` · ${data.totals[k] || 0}`}
          </button>
        ))}
      </div>
      {!!data.search_interpretation?.corrections.length && (
        <p className="search-interpretation">
          Also matching{" "}
          {data.search_interpretation.corrections
            .map((c) => `“${c.from}” → “${c.to}”`)
            .join(", ")}
          .
        </p>
      )}
      {!!data.search_interpretation?.concepts.length && (
        <p className="search-interpretation">
          Related terms: {data.search_interpretation.concepts.join(" · ")}.
        </p>
      )}
      {!shown && (
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
            {preview(data.people).map((p) => (
              <PersonCard
                key={p.id}
                person={p}
                onClick={() => onPerson(p.id)}
              />
            ))}
          </div>
          {more("people", "people")}
        </section>
      )}
      {(filter === "all" || filter === "topics") && !!data.topics.length && (
        <section aria-label="Matching topics">
          <h3>Topics</h3>
          <TopicLinks topics={preview(data.topics)} onTopic={onTopic} />
          {more("topics", "topics")}
        </section>
      )}
      {(filter === "all" || filter === "works") && !!data.works?.length && (
        <section aria-label="Matching works">
          <h3>Works</h3>
          <WorkCards works={preview(data.works)} onWork={onWork} />
          {more("works", "works")}
        </section>
      )}
      {(filter === "all" || filter === "ideas") && (
        <section aria-label="Matching ideas">
          <h3>Ideas · {data.totals.ideas}</h3>
          {preview(data.results).map((n) => (
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
          {more("ideas", "ideas")}
        </section>
      )}
      {filter !== "all" && !data.totals[filter] && (
        <p className="notice">
          No {filter === "people" ? "scientists or contributors" : filter} match
          this search in the current release.
        </p>
      )}
      {filter !== "all" && (
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
      )}
    </section>
  );
}
