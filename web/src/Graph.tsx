import { useEffect, useRef, useState } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import {
  COLORS,
  CONNECTIONS,
  LAYERS,
  Contribution,
  Relation,
  Info,
  words,
} from "./types";
export function Graph({
  nodes,
  relations,
  predicates,
  selected,
  loading = false,
  onSelect,
  onRelation,
  visibleLayers = LAYERS,
  autoFit = false,
}: {
  nodes: Contribution[];
  relations: Relation[];
  predicates: Info["predicates"];
  selected?: string;
  loading?: boolean;
  onSelect: (id: string) => void;
  onRelation: (id: string) => void;
  visibleLayers?: string[];
  autoFit?: boolean;
}) {
  const container = useRef<HTMLDivElement>(null),
    instance = useRef<Core | null>(null),
    positions = useRef<Record<string, { x: number; y: number }>>({});
  const [hovered, setHovered] = useState("");
  const viewportTouched = useRef(false),
    columns = useRef(0);
  const fit = (cy: Core) => {
    if (!cy.nodes().length || !cy.width() || !cy.height()) return;
    cy.fit(undefined, 65);
    cy.zoom(Math.min(cy.zoom(), 1.1));
    cy.center();
  };
  const fingerprint =
    nodes.map((n) => `${n.id}:${n.revision}`).join("|") +
    "/" +
    relations.map((r) => `${r.id}:${r.revision}`).join("|");
  const select = useRef(onSelect),
    relationSelect = useRef(onRelation);
  select.current = onSelect;
  relationSelect.current = onRelation;
  useEffect(() => {
    if (!container.current) return;
    const cy = cytoscape({
      container: container.current,
      elements: [],
      minZoom: 0.22,
      maxZoom: 2.5,
      wheelSensitivity: 0.22,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            width: 20,
            height: 20,
            label: "data(shortLabel)",
            color: "#dad8e9",
            "font-family": "system-ui, sans-serif",
            "font-size": 12,
            "text-wrap": "wrap",
            "text-max-width": "110px",
            "text-valign": "bottom",
            "text-margin-y": 9,
            // Keep personal-map labels readable when a long arrow crosses them.
            "text-background-color": "#242333",
            "text-background-opacity": autoFit ? 0.94 : 0,
            "text-background-padding": "3px",
            "border-color": "#202135",
            "border-width": 3,
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-color": "#ffffff",
            "border-width": 3,
            width: 24,
            height: 24,
            color: "#ffffff",
            "font-weight": 600,
            label: "data(label)",
            "text-background-color": "#242333",
            "text-background-opacity": 0.92,
            "text-background-padding": "5px",
          },
        },
        {
          selector: ".joint",
          style: {
            shape: "diamond",
            width: 11,
            height: 11,
            "background-color": "#d0c4ed",
            label: "joint premises",
            "font-size": 9,
          },
        },
        {
          selector: "edge",
          style: {
            width: 2.1,
            "line-color": "data(color)",
            "target-arrow-color": "data(color)",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.9,
            opacity: 0.9,
          },
        },
        {
          selector: "edge[bend][bend != 0]",
          style: {
            "curve-style": "unbundled-bezier",
            "control-point-distances": "data(bend)",
            "control-point-weights": "0.5",
          },
        },
        ...Object.entries(CONNECTIONS).map(([layer, value]) => ({
          selector: `edge[layer="${layer}"]`,
          style: { "line-style": value.style, "line-dash-pattern": value.dash },
        })),
        { selector: ".filtered", style: { display: "none" } },
        {
          selector: 'edge[symmetric="true"]',
          style: { "target-arrow-shape": "none" },
        },
        {
          selector: "edge:selected",
          style: {
            width: 4,
            opacity: 1,
            label: "data(label)",
            color: "white",
            "font-size": 10,
            "text-background-color": "#202034",
            "text-background-opacity": 1,
            "text-background-padding": "5px",
          },
        },
      ],
    });
    instance.current = cy;
    cy.on("tap", "node", (event) => {
      const d = event.target.data();
      if (d.relation) relationSelect.current(d.relation);
      else select.current(d.id);
    });
    cy.on("tap", "edge", (event) =>
      relationSelect.current(event.target.data("relation")),
    );
    cy.on("mouseover", "node, edge", (event) =>
      setHovered(event.target.data("label") || ""),
    );
    cy.on("mouseout", "node, edge", () => setHovered(""));
    cy.on("dragfree", "node", (event) => {
      positions.current[event.target.id()] = event.target.position();
    });
    const observer = new ResizeObserver(() => {
      cy.resize();
      if (autoFit && !viewportTouched.current) fit(cy);
    });
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      cy.destroy();
      instance.current = null;
    };
  }, []);
  useEffect(() => {
    const cy = instance.current;
    if (!cy) return;
    cy.nodes().forEach((n) => {
      positions.current[n.id()] = n.position();
    });
    let nextPosition = Object.keys(positions.current).length;
    if (!columns.current) columns.current = cy.width() < 600 ? 2 : 3;
    const elements: ElementDefinition[] = [...nodes]
      .sort(
        (a, b) =>
          (a.date.year ?? 9999) - (b.date.year ?? 9999) ||
          a.title.localeCompare(b.title),
      )
      .map((n, i) => ({
        data: {
          id: n.id,
          label: n.title,
          shortLabel:
            n.title.length > 50 ? n.title.slice(0, 47) + "…" : n.title,
          color: COLORS[n.pillar] || "#aa8df3",
        },
        position:
          positions.current[n.id] ||
          (autoFit
            ? (() => {
                const slot = nextPosition++;
                return {
                  x: (slot % columns.current) * 220,
                  y: Math.floor(slot / columns.current) * 120,
                };
              })()
            : {
                x: Math.cos(i * 2.399) * Math.sqrt(i + 1) * 47,
                y: Math.sin(i * 2.399) * Math.sqrt(i + 1) * 47,
              }),
      }));
    for (const e of relations) {
      const joint = e.premises.length > 1;
      const symmetric = predicates[e.predicate]?.symmetric ?? false;
      if (joint) {
        const endpoints = [...e.premises, e.conclusion].map(
          (ref) =>
            elements.find((node) => node.data.id === ref.id)?.position || {
              x: 0,
              y: 0,
            },
        );
        elements.push({
          data: {
            id: `joint-${e.id}`,
            relation: e.id,
            label: "joint premises",
            color: "#d0c4ed",
          },
          classes: "joint",
          position: positions.current[`joint-${e.id}`] || {
            x: endpoints.reduce((sum, p) => sum + p.x, 0) / endpoints.length,
            y:
              endpoints.reduce((sum, p) => sum + p.y, 0) / endpoints.length -
              60,
          },
        });
      }
      e.premises.forEach((p, i) =>
        elements.push({
          data: {
            id: `${e.id}-${i}`,
            source: p.id,
            target: joint ? `joint-${e.id}` : e.conclusion.id,
            relation: e.id,
            layer: e.layer,
            color: CONNECTIONS[e.layer]?.color || "#d0c4ed",
            label: words(e.predicate),
            symmetric: String(symmetric),
          },
        }),
      );
      if (joint)
        elements.push({
          data: {
            id: `${e.id}-out`,
            source: `joint-${e.id}`,
            target: e.conclusion.id,
            relation: e.id,
            layer: e.layer,
            color: CONNECTIONS[e.layer]?.color || "#d0c4ed",
            label: words(e.predicate),
            symmetric: "false",
          },
        });
    }
    if (autoFit) {
      // Stable grid positions keep streaming maps readable, but a straight
      // chord can pass through a third node and imply a nonexistent link.
      // Bend only those chords; keep parallel relationships distinguishable.
      const points = new Map(
        elements
          .filter((e) => e.position)
          .map((e) => [e.data.id!, e.position!]),
      );
      const lanes = new Map<string, number>();
      for (const e of elements) {
        const { source, target } = e.data;
        if (!source || !target) continue;
        const a = points.get(source),
          b = points.get(target);
        if (!a || !b) continue;
        const dx = b.x - a.x,
          dy = b.y - a.y,
          length2 = dx * dx + dy * dy;
        const blocked =
          length2 > 0 &&
          [...points].some(([id, p]) => {
            if (id === source || id === target) return false;
            const t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / length2;
            return (
              t > 0.05 &&
              t < 0.95 &&
              Math.hypot(p.x - a.x - t * dx, p.y - a.y - t * dy) < 24
            );
          });
        const pair = [source, target].sort().join("/");
        const lane = lanes.get(pair) || 0;
        lanes.set(pair, lane + 1);
        e.data.bend = blocked ? (dx < 0 ? 1 : -1) * (72 + 28 * lane) : 0;
      }
    }
    const fresh = nodes.every((n) => !positions.current[n.id]);
    const viewport = { zoom: cy.zoom(), pan: { ...cy.pan() } };
    // Update only changed elements: keep positions, selection and the canvas alive.
    const ids = new Set(elements.map((e) => e.data.id));
    cy.batch(() => {
      cy.elements()
        .filter((e) => !ids.has(e.id()))
        .remove();
      for (const element of elements) {
        const existing = cy.getElementById(element.data.id!);
        if (existing.length) existing.data(element.data);
        else cy.add(element);
      }
    });
    if (autoFit && !viewportTouched.current) fit(cy);
    else if (fresh && nodes.length === 1) {
      cy.zoom(1);
      cy.center();
    } else if (fresh && nodes.length > 1 && !autoFit) {
      cy.layout({
        name: "cose",
        animate: false,
        randomize: false,
        nodeDimensionsIncludeLabels: true,
        nodeRepulsion: () => 40000,
        idealEdgeLength: () => 100,
        componentSpacing: 100,
        numIter: 400,
        fit: true,
        padding: 55,
      }).run();
      cy.nodes().forEach((n) => {
        positions.current[n.id()] = n.position();
      });
      // Start at a readable scale around the selected result. The overview
      // control is available without making every initial label microscopic.
      cy.zoom(Math.max(cy.zoom(), 0.82));
      const focus = selected ? cy.getElementById(selected) : cy.nodes().first();
      if (focus.length) cy.center(focus);
    } else if (nodes.length) cy.viewport(viewport);
    if (selected) {
      cy.getElementById(selected).select();
      cy.edges()
        .filter((e) => e.data("relation") === selected)
        .select();
    }
  }, [fingerprint]);
  useEffect(() => {
    const cy = instance.current;
    if (!cy) return;
    cy.batch(() => {
      cy.edges().forEach((edge) => {
        edge.toggleClass(
          "filtered",
          !visibleLayers.includes(edge.data("layer")),
        );
      });
      cy.nodes(".joint").forEach((node) => {
        node.toggleClass(
          "filtered",
          node
            .connectedEdges()
            .toArray()
            .every((edge) => edge.hasClass("filtered")),
        );
      });
    });
  }, [visibleLayers, fingerprint]);
  useEffect(() => {
    const cy = instance.current;
    if (!cy) return;
    cy.elements().unselect();
    if (selected) {
      cy.getElementById(selected).select();
      cy.edges()
        .filter((e) => e.data("relation") === selected)
        .select();
    }
  }, [selected]);
  return (
    <div className="graph-shell">
      <div
        ref={container}
        className="graph"
        role="img"
        aria-label={`Knowledge graph with ${nodes.length} contributions and ${relations.filter((r) => visibleLayers.includes(r.layer)).length} relationships. Use the adjacent list for keyboard navigation.`}
        onPointerDown={() => {
          viewportTouched.current = true;
        }}
        onWheel={() => {
          viewportTouched.current = true;
        }}
      />
      <div className="graph-caption">
        <span className="live-dot" />{" "}
        {hovered ||
          "Drag to move · click an idea or arrow · use List for full titles"}
      </div>
      <div className="graph-controls">
        <button
          aria-label="Zoom in"
          onClick={() => {
            viewportTouched.current = true;
            instance.current?.zoom((instance.current?.zoom() || 1) * 1.25);
          }}
        >
          +
        </button>
        <button
          aria-label="Zoom out"
          onClick={() => {
            viewportTouched.current = true;
            instance.current?.zoom((instance.current?.zoom() || 1) / 1.25);
          }}
        >
          −
        </button>
        <button
          aria-label="Fit graph"
          onClick={() => {
            viewportTouched.current = true;
            instance.current?.fit(undefined, 65);
          }}
        >
          Overview
        </button>
        <button
          aria-label="Focus selected idea"
          onClick={() => {
            viewportTouched.current = true;
            const cy = instance.current;
            if (!cy) return;
            const target = selected
              ? cy.getElementById(selected)
              : cy.nodes().first();
            if (target.length) {
              cy.zoom(1);
              cy.center(target);
            }
          }}
        >
          Focus
        </button>
      </div>
      {!nodes.length && (
        <div className="graph-empty" role="status">
          {loading
            ? "Loading this map…"
            : "No screened contributions match these filters."}
          {!loading && (
            <>
              <br />
              <span>Open gaps remain part of the atlas.</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
