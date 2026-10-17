import { useEffect, useRef, useState } from "react";
import { remainingEstimate, STAGES, type Progress } from "./explore/progress";

export function ExplorationProgress({
  progress,
  running,
  elapsed,
  onCancel,
  onInspect,
}: {
  progress: Progress;
  running: boolean;
  elapsed: number;
  onCancel: () => void;
  onInspect?: () => void;
}) {
  const panel = useRef<HTMLElement>(null);
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!running) return;
    panel.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [running]);
  return (
    <section
      ref={panel}
      className="research-progress"
      aria-label="Exploration progress"
    >
      <div className="research-progress-heading">
        <div>
          <span className="eyebrow">
            {progress.state === "complete"
              ? "SEARCH FINISHED"
              : progress.state === "paused"
                ? "WORK RETAINED IN THIS TAB"
                : progress.refinement
                  ? "IMPROVING MISSING LINKS · FINAL PASS"
                  : `STEP ${progress.stage + 1} OF ${STAGES.length}`}
          </span>
          <h2>
            {progress.state === "complete"
              ? "Evidence check finished."
              : progress.state === "paused"
                ? progress.stage === 4
                  ? "Your map is available."
                  : "Continue from where you stopped."
                : STAGES[progress.stage]}
          </h2>
        </div>
        <div className="research-clock">
          {running && <strong>{remainingEstimate(progress, now)}</strong>}
          <span>
            {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")}{" "}
            elapsed
          </span>
          {running && (
            <small>
              {progress.deadline
                ? "Time limit · your draft stays available if review stops"
                : "Estimate · source and provider speed vary"}
            </small>
          )}
        </div>
      </div>
      <ol className="research-stages" aria-label="Research stages">
        {STAGES.map((label, i) => (
          <li
            key={label}
            className={
              progress.state === "complete" || i < progress.stage
                ? "done"
                : i === progress.stage
                  ? "current"
                  : "waiting"
            }
            aria-current={i === progress.stage ? "step" : undefined}
          >
            <span aria-hidden="true">
              {progress.state === "complete" || i < progress.stage
                ? "✓"
                : i + 1}
            </span>
            {label}
          </li>
        ))}
      </ol>
      <p className="explore-progress" role="status">
        {running && <span className="live-dot" />}
        {progress.detail}
      </p>
      {progress.stage === 4 && progress.state === "working" && (
        <p className="muted">
          {progress.reviewedInsights || 0} insights and{" "}
          {progress.reviewedConnections || 0} connections assessed. You can
          already inspect your map below. Completed checks are model judgments,
          not human verification.
        </p>
      )}
      <dl className="research-counts">
        {[
          ["External sources", progress.papers],
          ["Sources with text", progress.passages],
          ["Atlas insights", progress.atlas],
          ["Map insights", progress.insights],
          ["Connections", progress.connections],
        ].map(([label, value]) => (
          <div key={label}>
            <dd>{value}</dd>
            <dt>{label}</dt>
          </div>
        ))}
      </dl>
      <div className="research-updates">
        <div>
          <h3>Recent activity</h3>
          <ul>
            {progress.activity.slice(-4).map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>
            {progress.state === "complete"
              ? "Insights in your map"
              : progress.titles.length
                ? "Insights taking shape"
                : progress.foundations?.length
                  ? "Foundations being investigated"
                  : "What happens next"}
          </h3>
          {progress.titles.length ? (
            <ul>
              {progress.titles.map((title, i) => (
                <li key={i}>{title}</li>
              ))}
            </ul>
          ) : progress.foundations?.length && progress.state !== "complete" ? (
            <>
              <ul>
                {progress.foundations.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
              <p className="muted">
                Search hypotheses · inclusion still requires evidence.
              </p>
            </>
          ) : (
            <p>
              {progress.state === "complete"
                ? "No insights survived the evidence check. The gaps below explain what remains unresolved."
                : progress.stage < 3
                  ? "The agent is gathering passages about the mechanisms, earlier ideas and limits. Source-linked insights will appear here as the map is written."
                  : "Waiting for a complete insight with a valid source quotation. Partial sentences are never presented as findings."}
            </p>
          )}
        </div>
      </div>
      {running && (
        <div className="research-progress-actions">
          {onInspect && (
            <button className="primary" onClick={onInspect}>
              Inspect draft now
            </button>
          )}
          <button onClick={onCancel}>Pause exploration</button>
          <span>
            Completed work stays in this tab. You can resume the unfinished
            step.
          </span>
        </div>
      )}
    </section>
  );
}
