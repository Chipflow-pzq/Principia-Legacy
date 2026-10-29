import { useEffect, useState } from "react";
import { api, words } from "./types";

type Counts = {
  topics: number;
  topics_with_insights: number;
  reading_routes: number;
  insights: number;
  works: number;
  works_with_insights: number;
  people: number;
  people_with_insights: number;
};
type Coverage = { subjects: Record<string, Counts>; notice: string };

export function CoveragePanel({
  release,
  pillar,
}: {
  release: string;
  pillar: string;
}) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Coverage | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setData(null);
    setError("");
    api<Coverage>("coverage", { release }, controller.signal)
      .then(setData)
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [open, release]);
  return (
    <details
      className="coverage-panel"
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary>What is available in this atlas?</summary>
      <p>
        Topics and works can be listed before their explanations are ready.
        These live counts separate the reading catalogue from the content you
        can explore.
      </p>
      {error && <p role="alert">{error}</p>}
      {open && !data && !error && <p role="status">Loading coverage…</p>}
      {data && (
        <>
          <div className="coverage-table">
            <table>
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Insights</th>
                  <th>Topics with insights / listed</th>
                  <th>Works with insights / listed</th>
                  <th>Scientists linked to insights / listed</th>
                  <th>Reading routes checked by AI</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(data.subjects)
                  .filter(([key]) => !pillar || key === pillar)
                  .map(([key, c]) => (
                    <tr key={key}>
                      <th>{words(key)}</th>
                      <td>{c.insights.toLocaleString()}</td>
                      <td>
                        {c.topics_with_insights} / {c.topics}
                      </td>
                      <td>
                        {c.works_with_insights} / {c.works}
                      </td>
                      <td>
                        {c.people_with_insights} / {c.people}
                      </td>
                      <td>{c.reading_routes}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
          <p className="muted">
            {data.notice} Scientist profiles may describe a selected work
            without covering that person's full career.
          </p>
        </>
      )}
    </details>
  );
}
