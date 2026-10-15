import { useEffect, useState } from "react";
import { api, Person, PersonDetail, TopicLink, words } from "./types";
import { RichText } from "./RichText";

export function PersonPage({
  id,
  release,
  onIdea,
  onTopic,
  onBack,
  hasSearch,
  human,
}: {
  id: string;
  release: string;
  onIdea: (id: string) => void;
  onTopic: (id: string) => void;
  onBack: () => void;
  hasSearch: boolean;
  human: boolean;
}) {
  const [data, setData] = useState<PersonDetail | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    setData(null);
    setError("");
    api<PersonDetail>(
      `people/${encodeURIComponent(id)}`,
      { release, human },
      c.signal,
    )
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, [id, release, human]);
  return (
    <section className="person-page">
      <button className="back-link" onClick={onBack}>
        ←{" "}
        {hasSearch ? "Back to search results" : "All scientists & contributors"}
      </button>
      {error ? (
        <p role="alert">{error}</p>
      ) : !data ? (
        <p role="status">Loading contributor…</p>
      ) : (
        <>
          <span className="eyebrow">
            {data.person.kind === "person" ? "Scientist" : "Contributor"} ·{" "}
            {data.person.profile_status}
          </span>
          <h1>{data.person.name}</h1>
          {data.person.life_dates && (
            <p className="muted">{data.person.life_dates}</p>
          )}
          <p className="person-bio">
            {data.person.biography ||
              "This page gathers the credit recorded in the atlas. Biographical details have not yet been sourced."}
          </p>
          <p className="muted">
            {data.person.subjects.map(words).join(" · ")} ·{" "}
            {data.contributions.length} insights · {data.topics.length} topics
          </p>
          {!!data.person.bio_sources?.length && (
            <details>
              <summary>Profile sources</summary>
              {data.person.bio_sources.map((s) => (
                <p key={s.url}>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.title} ↗
                  </a>
                  <span className="muted">{s.note}</span>
                </p>
              ))}
            </details>
          )}
          <h2>Explore their ideas in these topics</h2>
          {human && !data.contributions.length && (
            <p role="status">
              No ideas on this page have a recorded human review in this
              release. Turn off “Human-reviewed only” to explore the available
              material.
            </p>
          )}
          <TopicLinks topics={data.topics} onTopic={onTopic} />
          <h2>Ideas and recorded contributions</h2>
          <p className="muted">
            Credit is shown for each idea; this list does not claim sole
            authorship or a complete body of work.
          </p>
          <div className="node-list">
            {data.contributions.map((n) => (
              <button key={n.id} onClick={() => onIdea(n.id)}>
                <span>{n.date.year || "—"}</span>
                <div>
                  <h3>
                    <RichText text={n.title} />
                  </h3>
                  <p>
                    <RichText text={n.claim} />
                  </p>
                  <small>
                    {n.credit?.role} · {n.credit?.recorded_name}
                  </small>
                  {n.credit?.evidence_note && (
                    <small>{n.credit.evidence_note}</small>
                  )}
                </div>
                <span>↗</span>
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
export function TopicLinks({
  topics,
  onTopic,
}: {
  topics: TopicLink[];
  onTopic: (id: string) => void;
}) {
  return (
    <div className="topic-links">
      {topics.map((t) => (
        <button key={t.id} className="topic-link" onClick={() => onTopic(t.id)}>
          <span className="eyebrow">{words(t.pillar)}</span>
          <strong>{t.title}</strong>
          {t.reason && <span className="muted">{t.reason}</span>}
          <span>Open topic ↗</span>
        </button>
      ))}
    </div>
  );
}
export function PeopleDirectory({
  release,
  onPerson,
  human,
  query,
  offset,
  onQuery,
  onPage,
}: {
  release: string;
  onPerson: (id: string) => void;
  human: boolean;
  query: string;
  offset: number;
  onQuery: (value: string) => void;
  onPage: (value: number) => void;
}) {
  const [data, setData] = useState<{ people: Person[]; total: number } | null>(
      null,
    ),
    [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    setData(null);
    setError("");
    const t = setTimeout(
      () =>
        api<{ people: Person[]; total: number }>(
          "people",
          { release, human, q: query, offset, limit: 48 },
          c.signal,
        )
          .then(setData)
          .catch((e) => {
            if (e.name !== "AbortError") setError(e.message);
          }),
      120,
    );
    return () => {
      clearTimeout(t);
      c.abort();
    };
  }, [release, human, offset, query]);
  return (
    <section className="people-directory">
      <span className="eyebrow">The people behind the ideas</span>
      <h1>Scientists & contributors</h1>
      <p>
        Explore recorded contributions, shared credit, and the topics they help
        explain.
      </p>
      <input
        aria-label="Find a scientist or contributor"
        placeholder="Find a name…"
        value={query}
        onChange={(e) => onQuery(e.target.value)}
      />
      {error && <p role="alert">{error}</p>}
      {!data && !error && <p role="status">Finding contributors…</p>}
      {data?.total === 0 && (
        <p role="status">
          {human
            ? "No contributors have ideas with a recorded human review in this release."
            : "No names match this search in this release."}
        </p>
      )}
      <div className="people-grid">
        {data?.people.map((p) => (
          <PersonCard key={p.id} person={p} onClick={() => onPerson(p.id)} />
        ))}
      </div>
      {data && (
        <div className="pagination">
          <button
            disabled={!offset}
            onClick={() => onPage(Math.max(0, offset - 48))}
          >
            Previous
          </button>
          <span>
            {data.total ? offset + 1 : 0}–{Math.min(offset + 48, data.total)} of{" "}
            {data.total}
          </span>
          <button
            disabled={offset + 48 >= data.total}
            onClick={() => onPage(offset + 48)}
          >
            Next
          </button>
        </div>
      )}
    </section>
  );
}
export function PersonCard({
  person: p,
  onClick,
}: {
  person: Person;
  onClick: () => void;
}) {
  return (
    <button className="person-card" onClick={onClick}>
      <span className="eyebrow">
        {p.kind === "person" ? "Scientist" : "Contributor"}
      </span>
      <h3>{p.name}</h3>
      <p>{p.biography || p.subjects.map(words).join(" · ")}</p>
      <span>{p.contribution_count} insights · Open profile ↗</span>
    </button>
  );
}
