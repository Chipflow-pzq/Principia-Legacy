import { useEffect, useMemo, useRef, useState } from "react";
import { Graph } from "./Graph";
import { ConnectionFilter, ConnectionLine } from "./Connections";
import { RichText } from "./RichText";
import { LAYERS, words, type Info } from "./types";
import { explore, type Checkpoint } from "./explore/agent";
import { type Progress } from "./explore/progress";
import { ExplorationProgress } from "./ExplorationProgress";
import { type ProviderSettings } from "./explore/settings";
import {
  graphData,
  importExploration,
  type Connection,
  type Evidence,
  type Exploration,
  type Insight,
  type Receipt,
} from "./explore/model";
import { deleteMap, downloadMap, savedMaps, saveMap } from "./explore/library";
import { lineage, readingRoute, roleLabels } from "./explore/lineage";
import { sourceCautions } from "./explore/sourceQuality";

function EvidenceList({
  evidence,
  draft,
  onAtlas,
}: {
  evidence: Evidence[];
  draft: Exploration;
  onAtlas: (id: string, release: string) => void;
}) {
  return (
    <div className="personal-evidence">
      {evidence.map((e, i) => {
        const source = draft.sources.find((s) => s.id === e.source)!;
        return (
          <article key={i}>
            <span className="eyebrow">
              {source.kind === "atlas"
                ? `Atlas explanation · revision ${source.revision}`
                : source.kind === "reference_excerpt"
                  ? "General reference · secondary evidence"
                  : source.kind === "article_excerpt"
                    ? "Open-access article excerpt"
                    : "Abstract excerpt"}
            </span>
            <h4>{source.title}</h4>
            <blockquote>{e.quote}</blockquote>
            <p className="muted">
              {source.authors.slice(0, 4).join(", ")}
              {source.authors.length > 4 ? " et al." : ""}
              {source.year ? ` · ${source.year}` : ""}
            </p>
            {source.atlas_id ? (
              <button
                onClick={() => onAtlas(source.atlas_id!, draft.atlas_release)}
              >
                Inspect the original atlas insight ↗
              </button>
            ) : (
              <a href={source.url} target="_blank" rel="noopener noreferrer">
                Open source ↗
              </a>
            )}
            {source.license && (
              <p className="muted">
                <a
                  href={source.license}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Source license ↗
                </a>{" "}
                · Excerpted; original wording retained.
              </p>
            )}
            <p className="evidence-caveat">
              A matching quotation makes the evidence inspectable. It does not
              establish that the model’s interpretation is correct.
            </p>
          </article>
        );
      })}
    </div>
  );
}
function DraftInspector({
  draft,
  selected,
  onSelect,
  onClose,
  onAtlas,
  predicates,
}: {
  draft: Exploration;
  selected: string;
  onSelect: (id: string) => void;
  onClose: () => void;
  onAtlas: (id: string, release: string) => void;
  predicates: Info["predicates"];
}) {
  const node = draft.nodes.find((n) => n.id === selected),
    relation = draft.relations.find((r) => r.id === selected);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    if (selected) {
      heading.current?.focus({ preventScroll: true });
      if (window.innerWidth <= 1200)
        heading.current?.closest("section")?.scrollIntoView({ block: "start" });
    }
    return () => {
      if (previous?.isConnected) previous.focus({ preventScroll: true });
    };
  }, [selected]);
  if (!node && !relation) return null;
  const item = (node || relation) as Insight | Connection;
  return (
    <section
      className="personal-inspector"
      aria-label="Personal map inspector"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          e.stopPropagation();
          onClose();
        }
      }}
    >
      <div className="personal-inspector-top">
        <span className="draft-badge">AI-generated · unverified</span>
        <button aria-label="Close personal map inspector" onClick={onClose}>
          ×
        </button>
      </div>
      <h2 tabIndex={-1} ref={heading}>
        {node?.title || "Why is this connection here?"}
      </h2>
      {node ? (
        <>
          {node.role && <p className="eyebrow">{roleLabels[node.role]}</p>}
          <p className="personal-claim">
            <RichText text={node.claim} />
          </p>
          <dl className="personal-details">
            {[
              ["Problem", node.problem],
              ["Conceptual move", node.move],
              ["Explanation", node.explanation],
            ]
              .filter(([, value]) => value)
              .map(([label, value]) => (
                <div key={label}>
                  <dt>{label}</dt>
                  <dd>
                    <RichText text={value} />
                  </dd>
                </div>
              ))}
          </dl>
          <h3>Attribution</h3>
          <p>
            {node.attribution.join(", ") ||
              "Not established in the retrieved evidence"}
            {node.year != null ? ` · ${node.year}` : ""}
          </p>
          <h3>Assumptions</h3>
          {node.assumptions.length ? (
            <ul>
              {node.assumptions.map((v, i) => (
                <li key={i}>
                  <RichText text={v} />
                </li>
              ))}
            </ul>
          ) : (
            <p>
              No assumptions were extracted; this does not establish that none
              apply.
            </p>
          )}
          <h3>Limitations</h3>
          {node.limitations.length ? (
            <ul>
              {node.limitations.map((v, i) => (
                <li key={i}>
                  <RichText text={v} />
                </li>
              ))}
            </ul>
          ) : (
            <p>Not established in this bounded search.</p>
          )}
        </>
      ) : (
        relation && (
          <>
            <p>
              <ConnectionLine layer={relation.layer} />
              {words(relation.layer)} · {words(relation.predicate)}
            </p>
            <div className="personal-endpoints">
              {relation.premises.length > 1 && (
                <strong>All of these premises are jointly required</strong>
              )}
              {relation.premises.map((id) => (
                <button key={id} onClick={() => onSelect(id)}>
                  {draft.nodes.find((n) => n.id === id)?.title}
                </button>
              ))}
              <span aria-hidden="true">
                {predicates[relation.predicate]?.symmetric ? "↔" : "↓"}
              </span>
              <button onClick={() => onSelect(relation.conclusion)}>
                {draft.nodes.find((n) => n.id === relation.conclusion)?.title}
              </button>
            </div>
            {predicates[relation.predicate]?.symmetric && (
              <p>
                This comparison is symmetric; it does not imply a direction of
                influence.
              </p>
            )}
            <h3>Warrant</h3>
            {relation.basis && (
              <p className="evidence-caveat">
                {relation.basis === "documented"
                  ? "Documented relationship · the cited passage describes this connection."
                  : relation.basis === "synthesis"
                    ? "Reasoned synthesis · the model combines cited findings under the assumptions below. This is not a documented history of influence."
                    : "Learning guidance · an editorial explanation of what helps a reader understand the next idea."}
              </p>
            )}
            <p>
              <RichText text={relation.warrant} />
            </p>
            {!!relation.steps?.length && (
              <>
                <h3>Reasoning steps</h3>
                <ol>
                  {relation.steps.map((step, i) => (
                    <li key={i}>
                      <RichText text={step} />
                    </li>
                  ))}
                </ol>
              </>
            )}
            <h3>Scope</h3>
            <p>
              <RichText
                text={
                  relation.scope ||
                  "No additional scope was extracted; examine the source before relying on this interpretation."
                }
              />
            </p>
          </>
        )
      )}
      <h3>Inspectable evidence</h3>
      <EvidenceList evidence={item.evidence} draft={draft} onAtlas={onAtlas} />
    </section>
  );
}

export default function Explorer({
  info,
  onAtlas,
  query,
  settings,
  onStatus,
}: {
  info: Info;
  onAtlas: (id: string, release: string) => void;
  query: string;
  settings: ProviderSettings;
  onStatus: (status: "idle" | "running" | "ready" | "paused") => void;
}) {
  const { key, model } = settings;
  const [running, setRunning] = useState(false),
    [progress, setProgress] = useState<Progress | null>(null),
    [error, setError] = useState("");
  const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(null);
  useEffect(() => {
    if (!running) setCheckpoint(null);
  }, [query]);
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!running) return;
    const start = Date.now();
    setElapsed(0);
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - start) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, [running]);
  const [receipts, setReceipts] = useState<Receipt[]>([]),
    [draft, setDraft] = useState<Exploration | null>(null);
  const [library, setLibrary] = useState<Exploration[]>([]),
    [session, setSession] = useState<Exploration[]>([]),
    [notice, setNotice] = useState("");
  const [removed, setRemoved] = useState<{
    map: Exploration;
    saved?: Exploration;
  } | null>(null);
  const [selected, setSelected] = useState(""),
    [layers, setLayers] = useState(LAYERS),
    [view, setView] = useState<"map" | "list">("map");
  const controller = useRef<AbortController | null>(null),
    fileInput = useRef<HTMLInputElement>(null);
  const map = useMemo(() => (draft ? graphData(draft) : null), [draft]);
  // A filter from a different question must not make a newly generated graph
  // appear to have no connections. Keep the reader's choice while this map grows.
  useEffect(() => {
    setLayers(LAYERS);
    setSelected("");
  }, [draft?.id]);
  const coverage = useMemo(
    () => (draft ? lineage(draft.nodes, draft.relations) : null),
    [draft],
  );
  const itinerary = useMemo(
    () =>
      draft && coverage
        ? coverage.hasReadingPath
          ? coverage
          : readingRoute(draft.nodes, draft.relations)
        : null,
    [draft, coverage],
  );
  const savedVersions = useMemo(
    () => new Set(library.map((d) => JSON.stringify(d))),
    [library],
  );
  const isSaved = (d: Exploration) => savedVersions.has(JSON.stringify(d));
  const unsaved =
    session.some((s) => !isSaved(s)) ||
    (!!checkpoint && checkpoint.phase !== "done");
  useEffect(() => {
    savedMaps(info.predicates)
      .then(setLibrary)
      .catch((e) => setNotice(e.message));
    return () => {
      controller.current?.abort();
    };
  }, []);
  useEffect(() => {
    const warn = (e: BeforeUnloadEvent) => {
      if (running || unsaved) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [running, unsaved]);
  function open(d: Exploration) {
    setDraft(d);
    setSelected("");
    setLayers(LAYERS);
    setReceipts(d.receipts);
    setNotice("");
    onStatus("ready");
  }
  function acceptPreview(result: Exploration) {
    setDraft(result);
    setSession((old) => [result, ...old.filter((d) => d.id !== result.id)]);
  }
  async function run(event?: React.FormEvent, resume = false) {
    event?.preventDefault();
    if (running) return;
    const abort = new AbortController();
    controller.current = abort;
    setRunning(true);
    onStatus("running");
    setError("");
    setNotice("");
    if (!resume) {
      setReceipts([]);
      setCheckpoint(null);
      setDraft(null);
      setSelected("");
    }
    const saved = resume ? checkpoint : null;
    try {
      const result = await explore({
        query: saved?.query || query,
        key,
        model,
        release: saved?.release || info.release_id,
        registry: info.predicates,
        signal: abort.signal,
        progress: setProgress,
        receipts: setReceipts,
        checkpoint: setCheckpoint,
        preview: acceptPreview,
        ...(saved ? { resume: saved } : {}),
      });
      acceptPreview(result);
      open(result);
      onStatus(result.completion === "partial" ? "paused" : "ready");
      if (result.completion === "partial")
        setNotice(
          "Your map is available with an unfinished evidence review. You can inspect or save it, or resume the check.",
        );
    } catch (e) {
      onStatus("paused");
      setError(
        abort.signal.aborted
          ? "Exploration paused. Your sources and completed insights are retained in this tab. Submitted requests may still be charged."
          : e instanceof Error
            ? e.message
            : "Exploration failed.",
      );
    } finally {
      controller.current = null;
      setRunning(false);
    }
  }
  async function save(d: Exploration) {
    try {
      await saveMap(d, info.predicates);
      const stored = await savedMaps(info.predicates);
      setLibrary(stored);
      const saved = stored.find((s) => s.id === d.id)!;
      setSession((old) => old.map((s) => (s.id === d.id ? saved : s)));
      setDraft((current) => (current?.id === d.id ? saved : current));
      setNotice(
        "Saved in this browser on this device. Clearing site data will remove it; download a file for a portable copy.",
      );
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function remove(id: string) {
    try {
      const existing =
        session.find((d) => d.id === id) || library.find((d) => d.id === id);
      await deleteMap(id);
      if (existing)
        setRemoved({ map: existing, saved: library.find((d) => d.id === id) });
      setLibrary((old) => old.filter((d) => d.id !== id));
      setSession((old) => old.filter((d) => d.id !== id));
      if (draft?.id === id) {
        setDraft(null);
        setSelected("");
        if (![...session, ...library].some((d) => d.id !== id))
          onStatus("idle");
      }
      setNotice("The local map was removed.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function undoRemove() {
    if (!removed) return;
    const recovered = removed;
    if (recovered.saved) {
      try {
        await saveMap(recovered.saved, info.predicates);
        setLibrary(await savedMaps(info.predicates));
      } catch {
        setError(
          "The map was restored in this session, but browser storage is unavailable. Download it to keep a copy.",
        );
      }
    }
    setSession((old) => [
      recovered.map,
      ...old.filter((d) => d.id !== recovered.map.id),
    ]);
    open(recovered.map);
    onStatus(recovered.map.completion === "partial" ? "paused" : "ready");
    setRemoved(null);
    setNotice("Map restored.");
  }
  async function importFile(file?: File) {
    if (!file) return;
    try {
      if (file.size > 2_000_000)
        throw new Error("Choose a map smaller than 2 MB.");
      const imported = importExploration(await file.text(), info.predicates);
      // A portable file receives a fresh local identity; it cannot overwrite an existing map.
      imported.id = crypto.randomUUID();
      setSession((old) => [imported, ...old]);
      open(imported);
      setNotice(
        "File opened in memory. Choose Save on this device to keep it in this browser.",
      );
    } catch (e) {
      setError(
        e instanceof SyntaxError
          ? "This file is not valid JSON."
          : (e as Error).message,
      );
    } finally {
      if (fileInput.current) fileInput.current.value = "";
    }
  }
  const maps = [
    ...session,
    ...library.filter((l) => !session.some((d) => d.id === l.id)),
  ];
  return (
    <section className="explorer" aria-label="Personal research exploration">
      <form id="research-run" onSubmit={run} />
      {progress && (!draft || draft.id === checkpoint?.id) && (
        <ExplorationProgress
          progress={progress}
          running={running}
          elapsed={elapsed}
          onCancel={() => controller.current?.abort()}
          onInspect={
            draft
              ? () => {
                  const result = document.getElementById(
                    "personal-exploration-result",
                  );
                  result?.focus({ preventScroll: true });
                  result?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                  });
                }
              : undefined
          }
        />
      )}
      {!running && checkpoint && checkpoint.phase !== "done" && (
        <div className="research-resume">
          <div>
            <p className="muted">For “{checkpoint.query}”</p>
            <strong>
              {checkpoint.checked
                ? "Your draft is still available."
                : `${checkpoint.sources.length} retrieved sources are retained.`}
            </strong>
            <p>
              Resume the unfinished step with your selected model. Completed
              stages are not requested again. This uses your provider balance.
            </p>
          </div>
          <button
            className="primary"
            disabled={!key.trim() || checkpoint.receipts.length >= 24}
            onClick={() => run(undefined, true)}
          >
            {checkpoint.phase === "review"
              ? "Resume evidence check"
              : "Resume exploration"}
          </button>
        </div>
      )}
      {error && (
        <div className="error" role="alert">
          {error}
          <button onClick={() => setError("")}>Dismiss</button>
        </div>
      )}
      {notice && (
        <p className="local-notice" role="status">
          {notice}
        </p>
      )}
      {removed && (
        <p className="local-notice">
          Removed “{removed.map.title}”.{" "}
          <button onClick={undoRemove} disabled={running}>
            Undo removal
          </button>
        </p>
      )}
      <div className="personal-library">
        <details>
          <summary>
            My maps <span>{maps.length} on this device or in this session</span>
          </summary>
          <p>
            Only Save on this device writes a map to browser storage. Unsaved
            session maps disappear when this tab closes. Nothing is uploaded.
          </p>
          {maps.length ? (
            <ul>
              {maps.map((d) => (
                <li key={d.id}>
                  <button onClick={() => open(d)} disabled={running}>
                    {d.title}
                    <small>
                      {isSaved(d)
                        ? "Saved on this device"
                        : library.some((l) => l.id === d.id)
                          ? "Unsaved changes · this session only"
                          : "Unsaved · this session only"}
                    </small>
                  </button>
                  <button
                    aria-label={`Remove ${d.title}`}
                    disabled={running}
                    onClick={() => remove(d.id)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No personal maps yet.</p>
          )}
        </details>
        <button disabled={running} onClick={() => fileInput.current?.click()}>
          Open a map file
        </button>
        <input
          ref={fileInput}
          hidden
          type="file"
          accept=".json,application/json"
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            void importFile(file);
          }}
        />
      </div>
      {draft && map && (
        <section
          id="personal-exploration-result"
          tabIndex={-1}
          className="personal-result"
          aria-label="Exploration result"
        >
          <div className="draft-notice">
            <strong>Personal draft · not verified</strong>
            <span>
              {draft.completion === "partial"
                ? "Map in progress · evidence check unfinished. Received insights are shown below; they may change."
                : draft.check_status === "completed"
                  ? "Generated and challenged by a model. No human review. Separate from the published atlas."
                  : "No completed model check is recorded. No human review. Separate from the published atlas."}
            </span>
          </div>
          <div className="personal-result-heading">
            <div>
              <h2>{draft.title}</h2>
              <p>
                <RichText text={draft.summary} />
              </p>
            </div>
            <div className="explore-actions">
              <button disabled={running} onClick={() => save(draft)}>
                {isSaved(draft)
                  ? "Saved on this device ✓"
                  : library.some((l) => l.id === draft.id)
                    ? "Save updated map"
                    : "Save on this device"}
              </button>
              <button onClick={() => downloadMap(draft)}>Download map</button>
            </div>
          </div>
          {sourceCautions(draft.sources).map((finding) => (
            <aside
              className="personal-gaps"
              role="note"
              key={finding.sourceId}
              aria-label="Known source conflict"
            >
              <strong>This map uses a source with a known conflict</strong>
              <p>{finding.finding}</p>
              <a
                href={finding.comparisonUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                {finding.comparisonTitle} ↗
              </a>
              <p className="muted">
                Identified by an automated source comparison on{" "}
                {finding.checkedAt}; no qualified human audit. This saved map
                has not been rewritten. Its affected insights and connections
                need rechecking.
              </p>
            </aside>
          ))}
          {coverage && draft.completion !== "partial" && (
            <section
              className="personal-lineage"
              aria-label="Foundations and explanatory path"
            >
              <h3>
                {coverage.hasBackbone
                  ? "Follow the main explanation"
                  : itinerary?.hasNavigationPath
                    ? "Follow a guided reading path"
                    : "The explanatory path is still incomplete"}
              </h3>
              <p>
                {coverage.foundations} foundational{" "}
                {coverage.foundations === 1 ? "idea" : "ideas"} ·{" "}
                {coverage.connected} of {draft.nodes.length} insights connected.
                {coverage.isolated.length > 0 &&
                  ` ${coverage.isolated.length} ${coverage.isolated.length === 1 ? "insight still needs" : "insights still need"} an evidenced bridge.`}
                {itinerary?.hasNavigationPath &&
                  !coverage.hasBackbone &&
                  " This is a reading route through individually labelled connections, not a historical or deductive chain."}
                {!itinerary?.hasNavigationPath &&
                  " This map does not yet establish a representative route from foundations to the requested result."}
              </p>
              {itinerary && itinerary.route.length > 1 && (
                <ol>
                  {itinerary.route.map((id, i) => (
                    <li key={id}>
                      {i > 0 && (
                        <button
                          className="lineage-link"
                          onClick={() =>
                            setSelected(itinerary.relations[i - 1])
                          }
                          aria-label={`Inspect connection to ${draft.nodes.find((n) => n.id === id)?.title}`}
                        >
                          {itinerary.reversed[i - 1]
                            ? "bounds"
                            : words(
                                draft.relations.find(
                                  (r) => r.id === itinerary.relations[i - 1],
                                )?.predicate || "",
                              )}{" "}
                          →
                        </button>
                      )}
                      <button
                        onClick={() => setSelected(id)}
                        aria-pressed={selected === id}
                      >
                        {draft.nodes.find((n) => n.id === id)?.title}
                      </button>
                    </li>
                  ))}
                </ol>
              )}
              {itinerary?.reversed.some(Boolean) && (
                <p className="muted">
                  “Bounds” reads a limit toward the method it constrains. On the
                  map, that same arrow points from the method to its limit; open
                  it to inspect the original meaning.
                </p>
              )}
              {coverage.supporting.length > 0 && (
                <div className="personal-supporting">
                  <span>Other inputs to this explanation:</span>
                  {coverage.supporting.map((id) => (
                    <button key={id} onClick={() => setSelected(id)}>
                      {draft.nodes.find((n) => n.id === id)?.title}
                    </button>
                  ))}
                </div>
              )}
              {coverage.hasBackbone && (
                <p className="muted">
                  Each step has its own evidence and assumptions. Open a
                  connection to see whether it documents an application,
                  develops an inference, or offers learning guidance.
                </p>
              )}
            </section>
          )}
          <div className="personal-map-toolbar">
            <span>
              {draft.nodes.length} insights ·{" "}
              {draft.relations.filter((r) => layers.includes(r.layer)).length}{" "}
              {layers.length !== LAYERS.length &&
                `of ${draft.relations.length} `}
              connections
            </span>
            <ConnectionFilter value={layers} onChange={setLayers} />
            {layers.length !== LAYERS.length && (
              <button onClick={() => setLayers(LAYERS)}>
                Show all connections
              </button>
            )}
            <div className="segmented">
              <button
                className={view === "map" ? "active" : ""}
                onClick={() => setView("map")}
              >
                Map
              </button>
              <button
                className={view === "list" ? "active" : ""}
                onClick={() => setView("list")}
              >
                List
              </button>
            </div>
          </div>
          {draft.nodes.length > 0 ? (
            <div
              className={`personal-workspace ${selected ? "with-inspector" : ""}`}
            >
              <div>
                {view === "map" ? (
                  <Graph
                    key={draft.id}
                    autoFit
                    nodes={map.nodes}
                    relations={map.relations}
                    predicates={info.predicates}
                    selected={selected}
                    visibleLayers={layers}
                    onSelect={setSelected}
                    onRelation={setSelected}
                  />
                ) : (
                  <div
                    className="personal-node-list"
                    aria-label="Exploration insights"
                  >
                    {draft.nodes.map((n) => (
                      <button
                        key={n.id}
                        aria-pressed={selected === n.id}
                        onClick={() => setSelected(n.id)}
                      >
                        <span>
                          {n.role ? `${roleLabels[n.role]} · ` : ""}
                          {n.year ?? "Date unknown"}
                        </span>
                        <strong>{n.title}</strong>
                        <RichText text={n.claim} />
                      </button>
                    ))}
                  </div>
                )}
                <details className="personal-connections">
                  <summary>Inspect connections without using the graph</summary>
                  {!draft.relations.some((r) => layers.includes(r.layer)) && (
                    <p className="muted">
                      {draft.relations.length
                        ? "No connections match the selected types. Choose another type above."
                        : "No connections have been established. The insights remain available; see the evidence gaps below."}
                    </p>
                  )}
                  {draft.relations
                    .filter((r) => layers.includes(r.layer))
                    .map((r) => (
                      <button key={r.id} onClick={() => setSelected(r.id)}>
                        <ConnectionLine layer={r.layer} />
                        <span>
                          {r.premises
                            .map(
                              (id) =>
                                draft.nodes.find((n) => n.id === id)?.title,
                            )
                            .join(" + ")}{" "}
                          <em>{words(r.predicate)}</em>{" "}
                          {
                            draft.nodes.find((n) => n.id === r.conclusion)
                              ?.title
                          }
                        </span>
                      </button>
                    ))}
                </details>
              </div>
              {selected && (
                <DraftInspector
                  draft={draft}
                  selected={selected}
                  onSelect={setSelected}
                  onClose={() => setSelected("")}
                  onAtlas={onAtlas}
                  predicates={info.predicates}
                />
              )}
            </div>
          ) : (
            <p className="empty">
              No insights survived the evidence challenge. The gaps below
              explain what remains unresolved.
            </p>
          )}
          <details className="personal-gaps">
            <summary>What remains uncertain · {draft.gaps.length}</summary>
            <ul>
              {draft.gaps.map((g, i) => (
                <li key={i}>{g}</li>
              ))}
            </ul>
          </details>
          <p className="muted">
            To investigate a gap, edit the question above and start another
            bounded exploration. This map stays available in My maps for the
            rest of the session.
          </p>
        </section>
      )}
      {receipts.length > 0 && (
        <details className="exploration-receipts">
          <summary>Request receipts · {receipts.length} calls</summary>
          <p>
            Reported token use is not a bill. Missing usage after a failure or
            cancellation does not mean the request was free.
          </p>
          <ul>
            {receipts.map((r, i) => (
              <li key={i}>
                <strong>{r.stage}</strong> · {r.outcome}
                <br />
                <span>
                  {r.model} · {r.input_tokens ?? "unknown"} input /{" "}
                  {r.output_tokens ?? "unknown"} output tokens
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
