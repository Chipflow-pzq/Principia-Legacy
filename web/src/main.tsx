import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Graph } from "./Graph";
import { ConnectionFilter, ConnectionLegend } from "./Connections";
import { Compare } from "./Compare";
import { PeopleDirectory, PersonPage } from "./People";
import { WorkPage, TopicWorks } from "./Works";
import { SearchResults } from "./SearchResults";
import { Changes, ReleaseChanges } from "./Changes";
import { Inspector, RichText } from "./Inspector";
import {
  api,
  COLORS,
  Contribution,
  Dossier,
  Info,
  Inspection,
  LAYERS,
  Neighborhood,
  SearchData,
  words,
} from "./types";
import "./style.css";
import Explorer from "./Explorer";
import { Settings } from "./Settings";
import { loadSettings } from "./explore/settings";
import { normalizeLocation } from "./location";
// Older preview links remain valid, without suggesting that a query string
// chooses an application build or a personal map's evidence snapshot.
history.replaceState(null, "", normalizeLocation(new URL(location.href)));
const emptyGraph: Neighborhood = {
  release_id: "",
  contributions: [],
  relations: [],
  notice: "",
};
const shortTitles: Record<string, string> = {
  M06: "Packing spheres in eight dimensions",
  P01: "Protecting quantum information",
  C01: "The Transformer and attention",
  E01: "Separating cause from prediction",
  B01: "Predicting biomolecular structures",
};
function App() {
  const [info, setInfo] = useState<Info | null>(null),
    [dossiers, setDossiers] = useState<Dossier[]>([]),
    [release, setRelease] = useState(
      () => new URLSearchParams(location.hash.slice(1)).get("release") || "",
    );
  const [page, setPage] = useState<
      "atlas" | "tours" | "changes" | "people" | "explore"
    >("atlas"),
    [pillar, setPillar] = useState(""),
    [active, setActive] = useState<Dossier | null>(null),
    [query, setQuery] = useState(
      () => new URLSearchParams(location.hash.slice(1)).get("q") || "",
    ),
    [results, setResults] = useState<SearchData | null>(null),
    [searchOffset, setSearchOffset] = useState(0),
    [searchKind, setSearchKind] = useState<
      "all" | "ideas" | "people" | "topics" | "works"
    >("all"),
    [catalogLimit, setCatalogLimit] = useState(60),
    [area, setArea] = useState(""),
    [coverageFilter, setCoverageFilter] = useState("all"),
    [person, setPerson] = useState(""),
    [work, setWork] = useState(""),
    [peopleQuery, setPeopleQuery] = useState(""),
    [peopleOffset, setPeopleOffset] = useState(0),
    [graph, setGraph] = useState(emptyGraph),
    [inspection, setInspection] = useState<Inspection | null>(null),
    [human, setHuman] = useState(false),
    [layers, setLayers] = useState(LAYERS),
    [view, setView] = useState<"map" | "list">("map"),
    [challenge, setChallenge] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [compare, setCompare] = useState<
      (Contribution & { snapshot_id: string })[]
    >([]),
    [comparison, setComparison] = useState<ReleaseChanges | null>(null),
    [from, setFrom] = useState(""),
    [traceSeed, setTraceSeed] = useState(""),
    [traceHops, setTraceHops] = useState(1),
    [topicLimit, setTopicLimit] = useState(40),
    [direction, setDirection] = useState("both");
  const [explorerVisited, setExplorerVisited] = useState(false);
  const [researchQuestion, setResearchQuestion] = useState("");
  const [providerSettings, setProviderSettings] = useState(loadSettings);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [researchStatus, setResearchStatus] = useState<
    "idle" | "running" | "ready" | "paused"
  >("idle");
  const researchRunning = researchStatus === "running";
  const atlasLocation = useRef("");
  useEffect(() => {
    if (page === "explore") setExplorerVisited(true);
  }, [page]);
  const initialLinkHandled = useRef(false);
  const appliedLocation = useRef(location.hash);
  const inspectionRequest = useRef(0);
  const [locationKey, setLocationKey] = useState(location.hash);
  useEffect(() => {
    const restore = () => {
      if (appliedLocation.current === location.hash) return;
      appliedLocation.current = location.hash;
      initialLinkHandled.current = false;
      inspectionRequest.current++;
      setLocationKey(location.hash);
    };
    window.addEventListener("popstate", restore);
    window.addEventListener("hashchange", restore);
    return () => {
      window.removeEventListener("popstate", restore);
      window.removeEventListener("hashchange", restore);
    };
  }, []);
  function navigate(parameters: Record<string, string>) {
    initialLinkHandled.current = true;
    const target = "#" + new URLSearchParams(parameters).toString();
    if (location.hash !== target) history.pushState(null, "", target);
    appliedLocation.current = target;
    setLocationKey(target);
  }
  function readingContext() {
    return {
      ...(active ? { dossier: active.id } : {}),
      ...(query
        ? { q: query, offset: String(searchOffset), kind: searchKind }
        : {}),
      ...(traceSeed ? { trace: traceSeed } : {}),
      ...(pillar ? { subject: pillar } : {}),
      ...(person ? { person } : {}),
      ...(work ? { work } : {}),
      ...(peopleQuery ? { peopleq: peopleQuery } : {}),
      ...(peopleOffset ? { peopleoffset: String(peopleOffset) } : {}),
      ...(page !== "atlas" ? { page } : {}),
      release: info?.release_id || release || "",
    };
  }
  function changeSearch(value: string) {
    setQuery(value);
    setSearchKind("all");
    setResults(null);
    setSearchOffset(0);
    setInspection(null);
    setPerson("");
    setWork("");
    inspectionRequest.current++;
    const target =
      "#" +
      new URLSearchParams({
        ...readingContext(),
        q: value,
        offset: "0",
        kind: "all",
        person: "",
        work: "",
      }).toString();
    initialLinkHandled.current = true;
    history.replaceState(null, "", target);
    appliedLocation.current = target;
    setLocationKey(target);
  }
  function changeSearchPage(offset: number) {
    inspectionRequest.current++;
    setSearchOffset(offset);
    setResults(null);
    setInspection(null);
    navigate({ ...readingContext(), offset: String(offset) });
    window.scrollTo({ top: 0 });
  }
  function openWork(id: string) {
    setWork(id);
    setInspection(null);
    setPage("atlas");
    inspectionRequest.current++;
    navigate({ ...readingContext(), page: "atlas", work: id });
    window.scrollTo({ top: 0 });
  }
  function leaveWork() {
    setWork("");
    setInspection(null);
    inspectionRequest.current++;
    navigate({ ...readingContext(), work: "" });
    window.scrollTo({ top: 0 });
  }
  function openPerson(id: string) {
    setWork("");
    setPerson(id);
    setInspection(null);
    setPage("atlas");
    inspectionRequest.current++;
    navigate({ ...readingContext(), page: "atlas", person: id, work: "" });
    window.scrollTo({ top: 0 });
  }
  function changePeople(query: string, offset: number, replace = false) {
    setPeopleQuery(query);
    setPeopleOffset(offset);
    const parameters = {
      ...readingContext(),
      peopleq: query,
      peopleoffset: String(offset),
    };
    if (replace) {
      const target = "#" + new URLSearchParams(parameters).toString();
      initialLinkHandled.current = true;
      history.replaceState(null, "", target);
      appliedLocation.current = target;
      setLocationKey(target);
    } else navigate(parameters);
  }
  function leavePerson() {
    inspectionRequest.current++;
    setPerson("");
    setWork("");
    setInspection(null);
    setPage(query ? "atlas" : "people");
    navigate({
      ...readingContext(),
      person: "",
      page: query ? "atlas" : "people",
    });
  }
  async function openTopic(id: string) {
    const snapshot = inspection?.release_id || info?.release_id || release;
    const topic =
      info?.release_id === snapshot && dossiers.find((d) => d.id === id);
    if (topic) {
      openDossier(topic, snapshot);
      return;
    }
    // Search/record responses can arrive before the catalogue. A visible topic
    // link must still work, while a later navigation cancels this pending intent.
    const request = ++inspectionRequest.current;
    try {
      const data = await api<{ dossiers: Dossier[]; release_id: string }>(
        "dossiers",
        { release: snapshot },
      );
      if (request !== inspectionRequest.current) return;
      const found = data.dossiers.find((d) => d.id === id);
      if (!found)
        throw new Error("This topic is unavailable in the selected snapshot.");
      openDossier(found, data.release_id || snapshot);
    } catch (e) {
      if (request === inspectionRequest.current) setError(String(e));
    }
  }
  function closeInspector() {
    inspectionRequest.current++;
    setInspection(null);
    navigate(readingContext());
  }
  useEffect(() => {
    inspectionRequest.current++;
    setInspection(null);
    setCompare([]);
    setComparison(null);
    const controller = new AbortController();
    Promise.all([
      api<Info>("info", { release }, controller.signal),
      api<{ dossiers: Dossier[] }>("dossiers", { release }, controller.signal),
    ])
      .then(([i, d]) => {
        setInfo(i);
        setDossiers(d.dossiers);
        setActive((current) =>
          current ? d.dossiers.find((x) => x.id === current.id) || null : null,
        );
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      });
    return () => controller.abort();
  }, [release]);
  useEffect(() => {
    if (!query.trim()) {
      setResults(null);
      return;
    }
    setResults(null);
    const controller = new AbortController();
    const timer = setTimeout(
      () =>
        api<SearchData>(
          "search",
          { q: query, pillar, human, release, offset: searchOffset },
          controller.signal,
        )
          .then(setResults)
          .catch((e) => {
            if (e.name !== "AbortError") setError(e.message);
          }),
      180,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, pillar, human, release, searchOffset]);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setBusy(true);
    api<Neighborhood>(
      "neighborhood",
      {
        dossier: traceSeed ? undefined : active.id,
        seed: traceSeed || undefined,
        hops: traceSeed ? traceHops : 1,
        direction,
        limit: traceSeed ? 200 : topicLimit,
        layers: LAYERS.join(","),
        human,
        release,
      },
      controller.signal,
    )
      .then((data) => {
        if (!controller.signal.aborted) setGraph(data);
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [active?.id, traceSeed, traceHops, topicLimit, direction, human, release]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (document.querySelector("dialog[open]")) return;
      if (
        e.key === "/" &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(
          (e.target as HTMLElement)?.tagName,
        )
      ) {
        e.preventDefault();
        document
          .querySelector<HTMLInputElement>(
            page === "explore"
              ? "#research-query"
              : '[aria-label="Search the atlas"]',
          )
          ?.focus();
      }
      if (e.key === "Escape" && page !== "explore") {
        closeInspector();
        setCompare([]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active?.id, info?.release_id, query, person, page, pillar]);
  useEffect(() => {
    // A passive effect from the previous render must not consume a newer URL.
    if (locationKey !== location.hash) return;
    if (!dossiers.length || !info || initialLinkHandled.current) return;
    const hash = new URLSearchParams(locationKey.slice(1));
    const linkedRelease = hash.get("release");
    if (linkedRelease) {
      // A release can be installed while this tab is open. The backend, not
      // the cached list, validates links; a later valid link recovers cleanly.
      if (release !== linkedRelease) {
        setError("");
        setRelease(linkedRelease);
        return;
      }
      if (info.release_id !== linkedRelease) return;
    }
    initialLinkHandled.current = true;
    setTopicLimit(40);
    setTraceSeed("");
    setInspection(null);
    setCompare([]);
    setPillar(hash.get("subject") || "");
    setQuery(hash.get("q") || "");
    setSearchOffset(Math.max(0, Number(hash.get("offset")) || 0));
    const kind = hash.get("kind");
    setSearchKind(
      kind === "ideas" ||
        kind === "people" ||
        kind === "topics" ||
        kind === "works"
        ? kind
        : "all",
    );
    setTraceSeed(hash.get("trace") || "");
    setPerson(hash.get("person") || "");
    setWork(hash.get("work") || "");
    setPeopleQuery(hash.get("peopleq") || "");
    setPeopleOffset(Math.max(0, Number(hash.get("peopleoffset")) || 0));
    setPage(
      hash.get("page") === "tours"
        ? "tours"
        : hash.get("page") === "changes"
          ? "changes"
          : hash.get("page") === "people"
            ? "people"
            : hash.get("page") === "explore"
              ? "explore"
              : "atlas",
    );
    const assignment = dossiers.find((d) => d.id === hash.get("dossier"));
    setActive(assignment || null);
    const id = hash.get("node") || hash.get("relation");
    if (id) inspect(id, hash.has("relation"), linkedRelease || release, false);
  }, [dossiers, locationKey]);
  async function inspect(
    id: string,
    relation = false,
    snapshot = release,
    updateHistory = true,
  ) {
    const request = ++inspectionRequest.current;
    // Commit navigation with the click, before the optimistic inspector appears.
    // A fast Back action must never race a later network response into history.
    if (updateHistory)
      navigate({
        ...readingContext(),
        [relation ? "relation" : "node"]: id,
        release: snapshot || info?.release_id || release,
      });
    const preview = relation
      ? graph.relations.find((r) => r.id === id)
      : [...graph.contributions, ...(results?.results || [])].find(
          (n) => n.id === id,
        );
    if (preview && (!snapshot || snapshot === info?.release_id)) {
      setInspection({
        record: preview,
        release_id: info?.release_id || snapshot,
        sources: [],
        reviews: [],
        pending: true,
      });
    }
    try {
      const d = await api<Inspection>(
        `${relation ? "relations" : "contributions"}/${encodeURIComponent(id)}`,
        { release: snapshot },
      );
      if (request !== inspectionRequest.current) return;
      setInspection(d);
    } catch (e) {
      if (request === inspectionRequest.current) {
        setError(String(e));
        setInspection(null);
      }
    }
  }
  async function trace(id: string, snapshot = release) {
    try {
      const data = await api<Inspection>(`contributions/${id}`, {
        release: snapshot,
      });
      const n = data.record as Contribution;
      // Search can finish before the catalogue, or refer to another snapshot.
      const topics =
        dossiers.length && info?.release_id === data.release_id
          ? dossiers
          : (
              await api<{ dossiers: Dossier[] }>("dossiers", {
                release: data.release_id,
              })
            ).dossiers;
      if (data.release_id !== release) setRelease(data.release_id);
      setPage("atlas");
      setActive(topics.find((d) => n.dossiers.includes(d.id)) || null);
      setTraceSeed(id);
      setTraceHops(1);
      setDirection("both");
      setQuery("");
      setPerson("");
      setWork("");
      setInspection(null);
      setView("map");
      navigate({
        trace: id,
        dossier: n.dossiers[0] || "",
        release: data.release_id,
      });
      window.scrollTo({ top: 0 });
    } catch (e) {
      setError(String(e));
    }
  }
  async function addCompare(id: string, snapshot = release) {
    try {
      const data = await api<Inspection>(`contributions/${id}`, {
        release: snapshot,
      });
      const n = {
        ...(data.record as Contribution),
        snapshot_id: data.release_id,
      };
      setCompare((old) =>
        [
          ...old.filter(
            (x) => !(x.id === id && x.snapshot_id === n.snapshot_id),
          ),
          n,
        ].slice(-2),
      );
    } catch (e) {
      setError(String(e));
    }
  }
  function openDossier(
    d: Dossier,
    snapshot = info?.release_id || release || "",
  ) {
    setGraph(emptyGraph);
    setTopicLimit(40);
    setTraceSeed("");
    window.scrollTo({ top: 0 });
    setActive(d);
    setPerson("");
    setWork("");
    setInspection(null);
    setQuery("");
    setPage("atlas");
    setChallenge(false);
    inspectionRequest.current++;
    if (snapshot && snapshot !== info?.release_id && snapshot !== release)
      setRelease(snapshot);
    navigate({ dossier: d.id, release: snapshot });
  }
  function chooseSubject(id: string) {
    inspectionRequest.current++;
    setPerson("");
    setWork("");
    setPillar(id);
    setCatalogLimit(60);
    setArea("");
    setSearchOffset(0);
    setActive(null);
    setInspection(null);
    setTraceSeed("");
    setPage("atlas");
    navigate({
      ...(id ? { subject: id } : {}),
      ...(query ? { q: query } : {}),
      release: info?.release_id || release || "",
    });
    window.scrollTo({ top: 0 });
  }
  function reset() {
    setPerson("");
    setWork("");
    setTraceSeed("");
    window.scrollTo({ top: 0 });
    setActive(null);
    setInspection(null);
    setQuery("");
    setPage("atlas");
    inspectionRequest.current++;
    setPillar("");
    navigate({ release: info?.release_id || release || "" });
  }
  function downloadBrief() {
    api("brief", {
      q: query || active?.title || "",
      dossier: active?.id,
      release,
    })
      .then((data) => {
        const url = URL.createObjectURL(
          new Blob([JSON.stringify(data, null, 2)], {
            type: "application/json",
          }),
        );
        const a = document.createElement("a");
        a.href = url;
        a.download = "principia-evidence-brief.json";
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch((e) => setError(e.message));
  }
  const subjectTopics = dossiers.filter((d) => !pillar || d.pillar === pillar);
  const areas = [
    ...new Set(subjectTopics.map((d) => d.area || "Frontier research")),
  ].sort();
  const filtered = subjectTopics.filter(
    (d) =>
      (!area || (d.area || "Frontier research") === area) &&
      (coverageFilter === "all" ||
        (coverageFilter === "available"
          ? d.contribution_count > 0
          : !d.contribution_count)),
  );
  const nodes = challenge
    ? graph.contributions.filter(
        (n) => n.limits.length || n.kind === "negative_result",
      )
    : graph.contributions;
  function openResearch(question?: string) {
    if (page === "atlas") atlasLocation.current = location.hash;
    if (question && !researchRunning && !researchQuestion.trim())
      setResearchQuestion(question.slice(0, 500));
    inspectionRequest.current++;
    setInspection(null);
    setPage("explore");
    if (!researchRunning && info?.current_release_id)
      setRelease(info.current_release_id);
    navigate({ page: "explore" });
  }
  function returnToAtlas() {
    initialLinkHandled.current = false;
    if (atlasLocation.current) location.hash = atlasLocation.current;
    else {
      setPage("atlas");
      navigate({ page: "atlas", release: info?.release_id || release });
    }
  }
  return (
    <>
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
          document
            .getElementById("main-content")
            ?.scrollIntoView({ block: "start" });
        }}
      >
        Skip to content
      </a>
      <header className="topbar">
        <button className="brand" onClick={reset}>
          <span className="brand-mark">
            P<span>∴</span>
          </span>
          <span>
            Principia<span className="brand-sub">LEGACY</span>
          </span>
        </button>
        <nav aria-label="Main navigation">
          {(["atlas", "people", "tours", "changes"] as const).map((p) => (
            <button
              key={p}
              className={
                page === p || (p === "atlas" && page === "explore")
                  ? "active"
                  : ""
              }
              onClick={() => {
                inspectionRequest.current++;
                setPage(p);
                setPerson("");
                setWork("");
                navigate({
                  page: p,
                  ...(pillar ? { subject: pillar } : {}),
                  release: info?.release_id || release || "",
                });
                setActive(null);
                setInspection(null);
                setQuery("");
              }}
            >
              {p === "atlas"
                ? "Explore"
                : p === "people"
                  ? "Scientists"
                  : p === "tours"
                    ? "Guided journeys"
                    : "What changed"}
            </button>
          ))}
        </nav>
        <div className="header-actions">
          {researchStatus !== "idle" && page !== "explore" && (
            <button
              className="research-status-link"
              onClick={() => openResearch()}
            >
              <span className="live-dot" />
              {researchRunning
                ? "Tracing…"
                : researchStatus === "ready"
                  ? "Map ready ↗"
                  : "Trace paused ↗"}
            </button>
          )}
          <div className="local-status">
            <span className="live-dot" />
            {import.meta.env.MODE === "hosted"
              ? "Public · read-only"
              : "Local · offline ready"}
          </div>
          <button
            className="settings-trigger"
            aria-label="Settings"
            aria-haspopup="dialog"
            onClick={() => setSettingsOpen(true)}
          >
            <span aria-hidden="true">⚙</span> Settings
            {providerSettings.key && (
              <span className="settings-ready" aria-label="API configured" />
            )}
          </button>
        </div>
      </header>
      {settingsOpen && (
        <Settings
          value={providerSettings}
          running={researchRunning}
          atlasRelease={info?.release_id}
          onApply={setProviderSettings}
          onClose={() => setSettingsOpen(false)}
        />
      )}
      <div className="maturity-bar">
        <span>
          {page === "explore" ? "PERSONAL RESEARCH" : "EXPLORATORY EDITION"}
        </span>
        <p>
          {page === "explore"
            ? "Your question, your API key, your local map. Generated results remain unverified drafts."
            : "A sourced research catalog with machine-screened insights. Human review is shown separately."}
        </p>
        {info?.current_release_id &&
          info.current_release_id !== info.release_id && (
            <button
              className="current-version"
              onClick={() => {
                setRelease(info.current_release_id!);
                navigate({
                  ...(active ? { dossier: active.id } : {}),
                  release: info.current_release_id!,
                });
              }}
            >
              Reading an earlier version · Open current version ↗
            </button>
          )}
        {page !== "explore" && (
          <label>
            <input
              type="checkbox"
              checked={human}
              onChange={(e) => setHuman(e.target.checked)}
            />{" "}
            Human-reviewed only
          </label>
        )}
      </div>
      {error && (
        <div className="error" role="alert">
          {error}
          <button onClick={() => setError("")}>Dismiss</button>
        </div>
      )}
      <div
        className={`app-layout ${active && page === "atlas" ? "exploring" : ""}`}
      >
        <aside className="sidebar" aria-label="Subject navigation">
          <div className="sidebar-heading">SUBJECTS</div>
          <button
            className={`pillar-button ${!pillar ? "selected" : ""}`}
            onClick={() => chooseSubject("")}
          >
            <span className="all-icon">✳</span> All subjects{" "}
            <span>{info?.counts.contribution ?? "…"}</span>
          </button>
          {info &&
            Object.entries(info.pillars).map(([id, label]) => (
              <button
                key={id}
                className={`pillar-button ${pillar === id ? "selected" : ""}`}
                onClick={() => {
                  chooseSubject(id);
                }}
              >
                <i style={{ background: COLORS[id] }} />
                {label}
                <span>{info.subject_counts?.[id] ?? "…"}</span>
              </button>
            ))}
          <div className="sidebar-rule" />
          <div className="sidebar-heading">HOW TO READ THE MAP</div>
          <p className="sidebar-copy">
            Every point records a specific idea or discovery.
            <br />
            <br />
            Every arrow carries a reason you can inspect.
          </p>
          <ConnectionLegend />
          <div className="sidebar-bottom">
            <p>
              An open record of understanding,
              <br />
              including what remains unknown.
            </p>
          </div>
        </aside>
        <main id="main-content" tabIndex={-1}>
          {(page === "atlas" || page === "explore") && (
            <>
              {!active &&
                !person &&
                !work &&
                (!query || page === "explore") && (
                  <section className="hero">
                    <span className="eyebrow">
                      A LIVING ATLAS OF HUMAN UNDERSTANDING
                    </span>
                    <h1>Ideas do not stand alone.</h1>
                    <p>
                      Trace the insights, arguments, and discoveries that
                      brought us here.
                      <br className="desktop-break" /> Follow their connections.
                      Examine their limits. See what comes next.
                    </p>
                    <div className="hero-stats">
                      <span>
                        <strong>
                          {(info?.counts.contribution ?? "…").toLocaleString()}
                        </strong>{" "}
                        contributions
                      </span>
                      <span>
                        <strong>
                          {(info?.counts.relation ?? "…").toLocaleString()}
                        </strong>{" "}
                        evidenced connections
                      </span>
                      {info?.catalog_counts && (
                        <>
                          <span>
                            <strong>
                              {info.catalog_counts.works.toLocaleString()}
                            </strong>{" "}
                            catalogued works
                          </span>
                          <span>
                            <strong>
                              {info.catalog_counts.people.toLocaleString()}
                            </strong>{" "}
                            contributors
                          </span>
                        </>
                      )}
                    </div>
                    <div className="hero-art" aria-hidden="true">
                      <svg viewBox="0 0 300 230">
                        <g
                          stroke="#9685ba"
                          strokeWidth="1"
                          fill="none"
                          opacity=".55"
                        >
                          <path d="M30 170 L90 140 L125 60 L190 115 L265 40 M90 140 L180 195 L190 115 L255 170 M125 60 L200 30 M30 170 L65 60 L125 60 M180 195 L255 170" />
                        </g>
                        {[
                          [30, 170],
                          [90, 140],
                          [125, 60],
                          [190, 115],
                          [265, 40],
                          [180, 195],
                          [255, 170],
                          [65, 60],
                          [200, 30],
                        ].map(([x, y], i) => (
                          <g key={i}>
                            <circle
                              cx={x}
                              cy={y}
                              r={i === 3 ? 17 : 9}
                              fill={i === 3 ? "#e4dbf4" : "#eee9f6"}
                            />
                            <circle
                              cx={x}
                              cy={y}
                              r={i === 3 ? 7 : 4}
                              fill={Object.values(COLORS)[i % 5]}
                            />
                          </g>
                        ))}
                      </svg>
                      <span>Evidence connects the dots.</span>
                    </div>
                  </section>
                )}
              <section className="explore-composer" aria-label="Explore input">
                <div
                  className="explore-modes"
                  role="group"
                  aria-label="Explore mode"
                >
                  <button
                    className={page === "atlas" ? "active" : ""}
                    aria-pressed={page === "atlas"}
                    onClick={returnToAtlas}
                  >
                    Browse the atlas
                  </button>
                  <button
                    className={page === "explore" ? "active" : ""}
                    aria-pressed={page === "explore"}
                    onClick={() =>
                      openResearch(
                        page === "atlas" && query ? query : undefined,
                      )
                    }
                  >
                    Trace a discovery
                  </button>
                </div>
                <div className="explore-input-area">
                  {page === "atlas" ? (
                    <>
                      <div className="searchbar">
                        <span aria-hidden="true">⌕</span>
                        <input
                          aria-label="Search the atlas"
                          placeholder="Search topics, works, ideas or scientists…"
                          value={query}
                          maxLength={500}
                          onChange={(e) => changeSearch(e.target.value)}
                        />
                        <kbd>/</kbd>
                        {query && (
                          <button
                            aria-label="Clear search"
                            onClick={() => changeSearch("")}
                          >
                            ×
                          </button>
                        )}
                      </div>
                      <p className="composer-hint">
                        Explore topics, works, ideas and scientists already in
                        the atlas.
                      </p>
                    </>
                  ) : (
                    <>
                      <label htmlFor="research-query">
                        Which discovery would you like to trace?
                      </label>
                      <textarea
                        id="research-query"
                        form="research-run"
                        rows={3}
                        minLength={2}
                        maxLength={500}
                        required
                        value={researchQuestion}
                        disabled={researchRunning}
                        onChange={(e) => setResearchQuestion(e.target.value)}
                        placeholder="Name a frontier advance or technique, for example: plasma-enhanced chemical vapour deposition"
                      />
                      <p className="composer-hint">
                        Follow its foundations, the ideas that shaped it, and
                        what remains unresolved.
                      </p>
                      <div className="trace-start">
                        <button
                          type="submit"
                          form="research-run"
                          className="primary"
                          disabled={
                            !info ||
                            researchRunning ||
                            !providerSettings.key.trim() ||
                            !providerSettings.model.trim() ||
                            researchQuestion.trim().length < 2
                          }
                        >
                          {researchRunning
                            ? "Tracing discovery…"
                            : "Build research map"}
                        </button>
                        {!providerSettings.key ? (
                          <button
                            className="settings-nudge"
                            onClick={() => setSettingsOpen(true)}
                          >
                            Set up your API key ↗
                          </button>
                        ) : (
                          <span>
                            Using {providerSettings.model.split("/").at(-1)} ·
                            your account
                          </span>
                        )}
                      </div>
                      <p className="trace-privacy">
                        Online research uses your provider balance. Your
                        question and evidence go directly to SiliconFlow,
                        scholarly indexes and Wikipedia. Nothing is uploaded to
                        the atlas server.
                      </p>
                    </>
                  )}
                </div>
              </section>
            </>
          )}
          {explorerVisited && info && (
            <div hidden={page !== "explore"}>
              <Explorer
                info={info}
                query={researchQuestion}
                settings={providerSettings}
                onStatus={setResearchStatus}
                onAtlas={(id, snapshot) => {
                  initialLinkHandled.current = false;
                  location.hash = new URLSearchParams({
                    node: id,
                    release: snapshot,
                  }).toString();
                }}
              />
            </div>
          )}
          {page === "atlas" && (
            <>
              {work ? (
                <WorkPage
                  id={work}
                  release={info?.release_id || release}
                  human={human}
                  onBack={leaveWork}
                  onTopic={openTopic}
                  onPerson={openPerson}
                  onIdea={(id) => inspect(id)}
                  onWork={openWork}
                />
              ) : person ? (
                <PersonPage
                  id={person}
                  release={info?.release_id || release}
                  hasSearch={!!query}
                  human={human}
                  onBack={leavePerson}
                  onIdea={(id) => inspect(id)}
                  onTopic={openTopic}
                  onWork={openWork}
                />
              ) : query.trim() && results === null ? (
                <p role="status">
                  Searching topics, works, ideas and scientists…
                </p>
              ) : results !== null ? (
                <SearchResults
                  data={results}
                  filter={searchKind}
                  onFilter={(kind) => {
                    setSearchKind(kind);
                    if (searchOffset) {
                      setSearchOffset(0);
                      setResults(null);
                    }
                    navigate({ ...readingContext(), kind, offset: "0" });
                  }}
                  query={query}
                  human={human}
                  onIdea={(id) => inspect(id)}
                  onPerson={openPerson}
                  onTopic={openTopic}
                  onWork={openWork}
                  selected={inspection?.record.id}
                  onPage={changeSearchPage}
                />
              ) : active ? (
                <section className="dossier-view">
                  <button
                    className="back-link"
                    onClick={() => {
                      setActive(null);
                      setInspection(null);
                      navigate({
                        page: "atlas",
                        ...(pillar ? { subject: pillar } : {}),
                        release,
                      });
                    }}
                  >
                    ← All topics
                  </button>
                  <div className="dossier-heading">
                    <div>
                      <span className="eyebrow">
                        {active.id} / {words(active.pillar)}
                        {active.tags?.some((tag) => tag !== active.pillar)
                          ? ` · ${active.tags
                              .filter((tag) => tag !== active.pillar)
                              .map(words)
                              .join(" / ")}`
                          : ""}
                      </span>
                      <h1>{shortTitles[active.id] || active.title}</h1>
                      <p>{active.title}</p>
                    </div>
                    <button onClick={downloadBrief}>
                      Export evidence brief ↓
                    </button>
                  </div>
                  <div className="dossier-stats">
                    <span>
                      <strong>{active.contribution_count}</strong> contributions
                    </span>
                    <span>
                      <strong>{active.relation_count}</strong> warranted
                      connections
                    </span>
                    <span>{active.source_count || 0} sources</span>
                    <span className="open-gap">
                      ◌ Earlier ideas still being added
                    </span>
                  </div>
                  <details
                    className="topic-work-toggle"
                    open={!active.contribution_count}
                  >
                    <summary>
                      Works in this topic · {active.work_count || 0}
                    </summary>
                    <TopicWorks
                      topic={active.id}
                      release={info?.release_id || release}
                      human={human}
                      onWork={openWork}
                    />
                  </details>
                  {!active.contribution_count && (
                    <p className="notice">
                      This topic has documented works. Passage-grounded insight
                      extraction is still pending; its scientific map is not yet
                      available.
                    </p>
                  )}
                  {!!active.contribution_count && (
                    <>
                      <div className="map-toolbar">
                        {active.endpoint && !traceSeed && (
                          <button
                            className="primary"
                            onClick={() => inspect(active.endpoint!)}
                          >
                            Start with the main result ↗
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
                        <ConnectionFilter value={layers} onChange={setLayers} />
                        <button
                          className={challenge ? "selected" : ""}
                          onClick={() => {
                            setChallenge(!challenge);
                            if (!challenge) setView("list");
                          }}
                        >
                          ◒{" "}
                          {challenge
                            ? "Showing limitations"
                            : "Explore limitations"}
                        </button>
                        {traceSeed && (
                          <>
                            <select
                              aria-label="Trace direction"
                              value={direction}
                              onChange={(e) => setDirection(e.target.value)}
                            >
                              <option value="both">All connections</option>
                              <option value="ancestors">Follow premises</option>
                              <option value="descendants">
                                Follow consequences
                              </option>
                            </select>
                            <button
                              disabled={traceHops >= 6}
                              onClick={() =>
                                setTraceHops((n) => Math.min(6, n + 1))
                              }
                            >
                              Expand · {traceHops} of 6 steps
                            </button>
                            <button onClick={() => setTraceSeed("")}>
                              Back to this topic
                            </button>
                          </>
                        )}
                        {!traceSeed &&
                          (graph.available_count ?? 0) >
                            graph.contributions.length && (
                            <button
                              disabled={busy || topicLimit >= 200}
                              onClick={() =>
                                setTopicLimit((n) => Math.min(200, n + 40))
                              }
                            >
                              {topicLimit < 200
                                ? "Show more ideas"
                                : "200-idea view limit"}{" "}
                              · {graph.contributions.length} of{" "}
                              {graph.available_count}
                            </button>
                          )}
                        {busy && <span className="muted">Loading…</span>}
                      </div>
                      {view === "map" ? (
                        <Graph
                          key={active.id}
                          loading={busy}
                          visibleLayers={layers}
                          nodes={nodes}
                          predicates={info?.predicates || {}}
                          relations={graph.relations.filter(
                            (e) =>
                              nodes.some((n) => n.id === e.conclusion.id) &&
                              e.premises.every((p) =>
                                nodes.some((n) => n.id === p.id),
                              ),
                          )}
                          selected={
                            inspection?.record.id ||
                            traceSeed ||
                            active.endpoint ||
                            undefined
                          }
                          onSelect={(id) => inspect(id)}
                          onRelation={(id) => inspect(id, true)}
                        />
                      ) : (
                        <div className="node-list">
                          {nodes.map((n) => (
                            <button key={n.id} onClick={() => inspect(n.id)}>
                              <span>{n.date.year || "—"}</span>
                              <div>
                                <h3>
                                  <RichText text={n.title} />
                                </h3>
                                <p>
                                  <RichText
                                    text={
                                      challenge ? n.limits.join(" ") : n.claim
                                    }
                                  />
                                </p>
                              </div>
                              <span>↗</span>
                            </button>
                          ))}
                        </div>
                      )}
                      <details className="accessible-connections">
                        <summary>
                          Browse contributions and relationships as text (
                          {graph.contributions.length} /{" "}
                          {
                            graph.relations.filter((r) =>
                              layers.includes(r.layer),
                            ).length
                          }
                          )
                        </summary>
                        <div className="text-records">
                          {graph.contributions.map((n) => (
                            <button key={n.id} onClick={() => inspect(n.id)}>
                              {n.title} ↗
                            </button>
                          ))}
                        </div>
                        {graph.relations
                          .filter((r) => layers.includes(r.layer))
                          .map((e) => (
                            <button
                              className="text-edge"
                              key={e.id}
                              onClick={() => inspect(e.id, true)}
                            >
                              <RichText
                                text={e.premises
                                  .map(
                                    (p) =>
                                      graph.contributions.find(
                                        (n) => n.id === p.id,
                                      )?.title || p.id,
                                  )
                                  .join(" + ")}
                              />
                              {e.premises.length > 1 ? " (together) " : " "}→{" "}
                              {words(e.predicate)} →{" "}
                              {
                                graph.contributions.find(
                                  (n) => n.id === e.conclusion.id,
                                )?.title
                              }
                            </button>
                          ))}
                      </details>
                    </>
                  )}
                  <div className="coverage-panel">
                    <div>
                      <h3>What this topic covers</h3>
                      <p>
                        Coverage describes this topic, never a percentage of
                        human knowledge.
                      </p>
                      {!!active.isolated_contribution_count && (
                        <p>
                          {active.isolated_contribution_count}{" "}
                          {active.isolated_contribution_count === 1
                            ? "insight has"
                            : "insights have"}{" "}
                          no checked connection within this topic yet. Their
                          evidence remains available; missing links are research
                          gaps.
                        </p>
                      )}
                      {active.checklist.map((c) => (
                        <div className="check-item" key={c.id}>
                          <span>{c.supported ? "✓" : "◌"}</span>
                          {c.requirement}
                        </div>
                      ))}
                    </div>
                    <details>
                      <summary>
                        {active.gaps.length} open questions & evidence gaps
                      </summary>
                      {active.gaps.map((g, i) => (
                        <p key={i}>{g}</p>
                      ))}
                      <h4>Search record</h4>
                      {Object.entries(active.search_outcomes).map(([k, v]) => (
                        <p key={k}>
                          <strong>{words(k)}:</strong> {v}
                        </p>
                      ))}
                    </details>
                  </div>
                </section>
              ) : (
                <>
                  <section className="flagships">
                    <div className="section-head">
                      <div>
                        <span className="eyebrow">
                          NEW HERE? START WITH ONE OF THESE
                        </span>
                        <h2>Explore a discovery</h2>
                      </div>
                      <span className="muted">
                        Choose a discovery to see the ideas behind it.
                      </span>
                    </div>
                    <div className="flagship-grid">
                      {dossiers
                        .filter((d) =>
                          pillar
                            ? d.pillar === pillar && d.contribution_count > 0
                            : d.flagship,
                        )
                        .sort((a, b) => Number(b.flagship) - Number(a.flagship))
                        .slice(0, 5)
                        .map((d, i) => (
                          <button
                            className="flagship-card"
                            key={d.id}
                            onClick={() => openDossier(d)}
                            style={
                              {
                                "--pillar": COLORS[d.pillar],
                              } as React.CSSProperties
                            }
                          >
                            <span className="card-number">
                              0{i + 1} <span>↗</span>
                            </span>
                            <span className="eyebrow">
                              {info?.pillars[d.pillar]}
                            </span>
                            <h3>{shortTitles[d.id] || d.title}</h3>
                            <div className="card-bottom">
                              <span>{d.contribution_count} insights</span>
                              <span>
                                {d.contribution_count
                                  ? "Open the map"
                                  : "See what is missing"}
                              </span>
                            </div>
                          </button>
                        ))}
                    </div>
                  </section>
                  <section className="all-dossiers">
                    <div className="section-head">
                      <div>
                        <span className="eyebrow">THE COLLECTION</span>
                        <h2>
                          {pillar ? info?.pillars[pillar] : "Browse all topics"}
                        </h2>
                      </div>
                      <span className="count-pill">
                        {filtered.length} topics
                      </span>
                    </div>
                    <p className="section-description">
                      Each topic connects a scientific achievement to its
                      foundations. Incomplete topics show what is still missing.
                    </p>
                    <div className="catalog-filters">
                      <label>
                        Area{" "}
                        <select
                          value={area}
                          onChange={(e) => {
                            setArea(e.target.value);
                            setCatalogLimit(60);
                          }}
                        >
                          <option value="">All areas</option>
                          {areas.map((a) => (
                            <option key={a}>{a}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Coverage{" "}
                        <select
                          value={coverageFilter}
                          onChange={(e) => {
                            setCoverageFilter(e.target.value);
                            setCatalogLimit(60);
                          }}
                        >
                          <option value="all">
                            All topics, including gaps
                          </option>
                          <option value="available">Ideas available</option>
                          <option value="pending">Awaiting evidence</option>
                        </select>
                      </label>
                    </div>
                    <div className="dossier-grid">
                      {filtered.slice(0, catalogLimit).map((d) => (
                        <button
                          className="dossier-tile"
                          key={d.id}
                          onClick={() => openDossier(d)}
                        >
                          <span
                            className="dossier-id"
                            aria-hidden={d.id.startsWith("T-")}
                            style={{ color: COLORS[d.pillar] }}
                          >
                            {d.id.startsWith("T-") ? "▤" : d.id}
                          </span>
                          <div>
                            <h3>{d.title}</h3>
                            <span>
                              {d.contribution_count} contributions ·{" "}
                              {d.contribution_count === 0
                                ? d.work_count
                                  ? `${d.work_count} ${d.work_count === 1 ? "work" : "works"} · insights pending`
                                  : "Awaiting sources"
                                : d.endpoint
                                  ? "Ready to explore · growing"
                                  : "Foundations available"}
                            </span>
                          </div>
                          <span className="tile-arrow">↗</span>
                        </button>
                      ))}
                    </div>
                    {filtered.length > catalogLimit && (
                      <button
                        className="load-more"
                        onClick={() => setCatalogLimit((n) => n + 60)}
                      >
                        Show more topics ·{" "}
                        {Math.min(catalogLimit, filtered.length)} of{" "}
                        {filtered.length} shown
                      </button>
                    )}
                  </section>
                </>
              )}
            </>
          )}
          {page === "people" && (
            <PeopleDirectory
              pillar={pillar}
              release={info?.release_id || release}
              onPerson={openPerson}
              human={human}
              query={peopleQuery}
              offset={peopleOffset}
              onQuery={(value) => changePeople(value, 0, true)}
              onPage={(offset) => changePeople(peopleQuery, offset)}
            />
          )}
          {page === "tours" && (
            <section className="page-section">
              <span className="eyebrow">CROSS-DISCIPLINARY JOURNEYS</span>
              <h1>Different fields. Shared questions.</h1>
              <p className="lede">
                Editorial routes through the atlas. The themes connect your
                reading; only evidenced arrows connect historical claims.
              </p>
              {info?.tours.map((t, i) => (
                <article className="tour-card" key={t.id}>
                  <span className="tour-number">0{i + 1}</span>
                  <div>
                    <h2>{t.title}</h2>
                    <p>{t.description}</p>
                    <div className="tour-stops">
                      {t.dossiers.map((id) => {
                        const d = dossiers.find((x) => x.id === id);
                        return d ? (
                          <button key={id} onClick={() => openDossier(d)}>
                            {id} · {shortTitles[id] || d.title} ↗
                          </button>
                        ) : null;
                      })}
                    </div>
                  </div>
                </article>
              ))}
            </section>
          )}
          {page === "changes" && (
            <section className="page-section">
              <span className="eyebrow">A RECORD THAT CAN BE CORRECTED</span>
              <h1>Understanding evolves.</h1>
              <p className="lede">
                Releases preserve what the atlas said at a particular time.
                Corrections create new revisions; earlier records remain
                inspectable.
              </p>
              <div className="change-selector">
                <label>
                  Compare with{" "}
                  <select
                    value={from}
                    onChange={(e) => setFrom(e.target.value)}
                  >
                    <option value="">Choose a snapshot</option>
                    {info?.releases
                      .filter((r) => r !== info.release_id)
                      .map((r) => (
                        <option key={r}>{r}</option>
                      ))}
                  </select>
                </label>
                <button
                  disabled={!from}
                  onClick={() =>
                    api<ReleaseChanges>("changes", { from, release })
                      .then(setComparison)
                      .catch((e) => setError(e.message))
                  }
                >
                  Compare releases
                </button>
              </div>
              {comparison ? (
                <Changes
                  key={`${comparison.from_release}:${comparison.release_id}`}
                  data={comparison}
                  onInspect={inspect}
                />
              ) : (
                <div className="empty-state">
                  <h3>
                    {info?.releases.length === 1
                      ? "The founding snapshot"
                      : "Select a release to compare"}
                  </h3>
                  <p>
                    Record additions, corrections, and changed evidence will
                    appear here as the atlas grows.
                  </p>
                </div>
              )}
              <div className="notice">
                Corrections are proposed and applied through the local CLI. The
                reader cannot approve records or modify the archive.
              </div>
            </section>
          )}
          <footer className="main-footer">
            <span>PRINCIPIA—LEGACY</span>
            <p>Human understanding, with its reasons intact.</p>
            <span>
              {info?.human_reviewed || 0} human-reviewed contributions · Atlas
              snapshot {info?.release_id || "Loading"}
            </span>
          </footer>
        </main>
        {inspection && (
          <Inspector
            key={`${inspection.release_id}:${inspection.record.id}:${inspection.record.revision}`}
            data={inspection}
            onClose={closeInspector}
            onTrace={(id) => trace(id, inspection.release_id)}
            onCompare={(id) => addCompare(id, inspection.release_id)}
            onSelect={(id) => inspect(id, false, inspection.release_id)}
            onTopic={openTopic}
            onWork={openWork}
            onPerson={openPerson}
            searchNavigation={
              results &&
              !person &&
              results.results.some((n) => n.id === inspection.record.id)
                ? (() => {
                    const i = results.results.findIndex(
                      (n) => n.id === inspection.record.id,
                    );
                    return {
                      index: i,
                      total: results.results.length,
                      previous:
                        i > 0
                          ? () => inspect(results.results[i - 1].id)
                          : undefined,
                      next:
                        i + 1 < results.results.length
                          ? () => inspect(results.results[i + 1].id)
                          : undefined,
                    };
                  })()
                : undefined
            }
          />
        )}
      </div>
      {!!compare.length && (
        <Compare
          records={compare}
          suggestions={graph.contributions}
          release={info?.release_id || release}
          onAdd={addCompare}
          onRemove={(id, snapshot) =>
            setCompare((old) =>
              old.filter((n) => !(n.id === id && n.snapshot_id === snapshot)),
            )
          }
          onClose={() => setCompare([])}
          onInspect={(id, snapshot) => {
            setCompare([]);
            inspect(id, false, snapshot);
          }}
        />
      )}
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
