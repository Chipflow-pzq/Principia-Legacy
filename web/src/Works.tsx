import { useEffect, useState } from "react";
import { api, Work, WorkDetail, words } from "./types";
import { TopicLinks } from "./People";
import { usePageOffset } from "./usePageOffset";
import { RichText } from "./RichText";

export function WorkCard({
  work,
  onClick,
}: {
  work: Work;
  onClick: () => void;
}) {
  return (
    <button id={`work-card-${work.id}`} className="work-card" onClick={onClick}>
      <span className="eyebrow">
        {words(work.kind)}
        {work.year ? ` · ${work.year}` : ""}
      </span>
      <h3>
        <RichText text={work.title} />
      </h3>
      <p>{work.summary}</p>
      <span className="card-bottom">
        <span>
          {work.insight_count
            ? `${work.insight_count} extracted insights`
            : "Reading list only · no extracted insights"}
        </span>
        <span>Read work ↗</span>
      </span>
    </button>
  );
}
export function WorkCards({
  works,
  onWork,
}: {
  works: Work[];
  onWork: (id: string) => void;
}) {
  return (
    <div className="works-grid">
      {works.map((work) => (
        <WorkCard key={work.id} work={work} onClick={() => onWork(work.id)} />
      ))}
    </div>
  );
}
export function TopicWorks({
  topic,
  person,
  release,
  human,
  onWork,
}: {
  topic: string;
  person?: string;
  release: string;
  human: boolean;
  onWork: (id: string) => void;
}) {
  const [data, setData] = useState<{ works: Work[]; total: number } | null>(
      null,
    ),
    [error, setError] = useState("");
  const [offset, setOffset] = usePageOffset(
    "worklistpage",
    `${topic || person}/${human}`,
    12,
  );
  useEffect(() => {
    const c = new AbortController();
    setData(null);
    setError("");
    api<{ works: Work[]; total: number }>(
      "works",
      { topic, person, release, human, limit: 12, offset },
      c.signal,
    )
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, [topic, person, release, human, offset]);
  if (error) return <p role="alert">{error}</p>;
  if (!data) return <p role="status">Loading works…</p>;
  if (!data.total) return null;
  return (
    <section className="topic-works" aria-label="Works in this topic">
      <h2>
        {person ? "Selected works" : "Works behind this topic"}{" "}
        <span className="muted">· {data.total}</span>
      </h2>
      <p className="muted">
        Papers, books, discoveries and technologies. One work can explain
        several insights and appear in several topics.
      </p>
      <WorkCards works={data.works} onWork={onWork} />
      {data.total > 12 && (
        <nav className="pagination" aria-label="Works in topic pages">
          <button
            disabled={!offset}
            onClick={() => setOffset(Math.max(0, offset - 12))}
          >
            Previous works
          </button>
          <span>
            {offset + 1}–{Math.min(offset + 12, data.total)} of {data.total}
          </span>
          <button
            disabled={offset + 12 >= data.total}
            onClick={() => setOffset(offset + 12)}
          >
            Next works
          </button>
        </nav>
      )}
    </section>
  );
}
export function WorkPage({
  id,
  backLabel,
  release,
  human,
  onBack,
  onTopic,
  onPerson,
  onIdea,
  onWork,
}: {
  id: string;
  backLabel?: string;
  release: string;
  human: boolean;
  onBack: () => void;
  onTopic: (id: string) => void;
  onPerson: (id: string) => void;
  onIdea: (id: string) => void;
  onWork: (id: string) => void;
}) {
  const [offset, setOffset] = usePageOffset("workpage", `${id}/${human}`, 40);
  const [data, setData] = useState<
      (WorkDetail & { contribution_total: number }) | null
    >(null),
    [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    setData(null);
    setError("");
    api<WorkDetail & { contribution_total: number }>(
      `works/${encodeURIComponent(id)}`,
      { release, human, limit: 40, offset },
      c.signal,
    )
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => c.abort();
  }, [id, release, human, offset]);
  return (
    <article className="work-page">
      <button className="back-link" onClick={onBack}>
        ← {backLabel || "Back to browsing"}
      </button>
      {error ? (
        <p role="alert">{error}</p>
      ) : !data ? (
        <p role="status">Loading work…</p>
      ) : (
        <>
          <span className="eyebrow">
            {words(data.work.kind)} ·{" "}
            {data.work.subjects.map(words).join(" / ")}
          </span>
          <h1>
            <RichText text={data.work.title} />
          </h1>
          <p className="work-summary">{data.work.summary}</p>
          <p className="muted">
            {data.work.year
              ? `Published / introduced ${data.work.year} · `
              : ""}
            {data.work.recognition_year
              ? `Recognition year ${data.work.recognition_year} · `
              : ""}
            Revision {data.work.revision} · {data.release_id}
          </p>
          {!!data.people.length && (
            <div className="work-people">
              {data.people.map((p) => (
                <button key={p.id} onClick={() => onPerson(p.id)}>
                  {p.name} ↗
                </button>
              ))}
            </div>
          )}
          <h2>Read this work in context</h2>
          <TopicLinks topics={data.topics} onTopic={onTopic} />
          <h2>Insights from this work</h2>
          {!!data.contributions.length && (
            <p className="muted">
              These source passages explain the ideas below. Original discovery
              credit is recorded separately in each insight.
            </p>
          )}
          {!data.contributions.length && (
            <p className="notice">
              {human
                ? "No insights from this work have a recorded human review."
                : "This is a reading-list entry. Its insights have not yet been extracted and checked. You can open the original work below, or return to your search for available explanations."}
            </p>
          )}
          <div className="node-list">
            {data.contributions.map((n) => (
              <button key={n.id} onClick={() => onIdea(n.id)}>
                <div>
                  <h3>
                    <RichText text={n.title} />
                  </h3>
                  <p>
                    <RichText text={n.claim} />
                  </p>
                  <small>
                    {words(
                      data.memberships.find((m) => m.contribution.id === n.id)
                        ?.role || "explains",
                    )}
                    {n.date.year ? ` · ${n.date.year}` : ""} · Read insight ↗
                  </small>
                </div>
                <span>↗</span>
              </button>
            ))}
          </div>
          {data.contribution_total > 40 && (
            <nav className="pagination" aria-label="Work insight pages">
              <button
                disabled={!offset}
                onClick={() => setOffset(Math.max(0, offset - 40))}
              >
                Previous insights
              </button>
              <span>
                {offset + 1}–{Math.min(offset + 40, data.contribution_total)} of{" "}
                {data.contribution_total}
              </span>
              <button
                disabled={offset + 40 >= data.contribution_total}
                onClick={() => setOffset(offset + 40)}
              >
                Next insights
              </button>
            </nav>
          )}
          {!!data.memberships.length && (
            <details>
              <summary>Why these insights belong to this work</summary>
              {data.memberships.map((m) => (
                <p key={m.contribution.id}>
                  <strong>
                    {
                      data.contributions.find((n) => n.id === m.contribution.id)
                        ?.title
                    }
                  </strong>
                  <br />
                  {m.reason}
                </p>
              ))}
            </details>
          )}
          {!!data.relations.length && (
            <section>
              <h2>Connections through extracted insights</h2>
              {data.relations.map((r) => (
                <details key={r.id}>
                  <summary>
                    {r.endpoints
                      .map((w) => w.title)
                      .join(
                        ` ${r.symmetric ? "↔" : "→"} ${words(r.predicate)} ${r.symmetric ? "↔" : "→"} `,
                      )}
                  </summary>
                  <p>{r.warrant}</p>
                  <p className="muted">
                    {words(r.layer)} · Machine-screened ·{" "}
                    {words(r.human_review || "not_reviewed")} by a human.
                    Projected from a revision-pinned insight connection. This
                    does not characterize every claim in either work.
                  </p>
                  {r.endpoints
                    .filter((w) => w.id !== id)
                    .map((w) => (
                      <button key={w.id} onClick={() => onWork(w.id)}>
                        Read {w.title} ↗
                      </button>
                    ))}
                  {r.provenance.map((s) => (
                    <p key={s.url + s.note}>
                      <a href={s.url} target="_blank" rel="noreferrer">
                        {s.title} ↗
                      </a>{" "}
                      · {s.note}
                    </p>
                  ))}
                </details>
              ))}
            </section>
          )}
          {!!data.shared_insights.length && (
            <section>
              <h2>Other works explaining shared insights</h2>
              <p className="muted">
                Shared content does not establish historical influence.
              </p>
              <WorkCards
                works={data.shared_insights.map((s) => s.work)}
                onWork={onWork}
              />
            </section>
          )}
          <section className="work-provenance">
            <h2>Sources & scope</h2>
            <p>{data.notice}</p>
            {data.work.provenance.map((s) => (
              <p key={s.url + s.note}>
                <a href={s.url} target="_blank" rel="noreferrer">
                  {s.title} ↗
                </a>
                <br />
                <span className="muted">{s.note}</span>
              </p>
            ))}
            {data.sources.map((s) => (
              <details key={s.id}>
                <summary>
                  {s.title} · evidence revision {s.revision}
                </summary>
                <p>
                  {s.access_state} · {s.rights.license}
                </p>
                <p>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    Open the original source ↗
                  </a>
                </p>
                {s.anchors.map((a) => (
                  <p key={a.id}>
                    <strong>{a.selector}</strong> · {a.summary}
                  </p>
                ))}
              </details>
            ))}
          </section>
        </>
      )}
    </article>
  );
}
