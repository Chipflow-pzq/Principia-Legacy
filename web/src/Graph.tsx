import { useEffect, useRef, useState } from "react";
import cytoscape, { Core, ElementDefinition } from "cytoscape";
import { COLORS, Contribution, Relation, Info, words } from "./types";
export function Graph({
  nodes,
  relations,
  predicates,
  selected,
  loading = false,
  onSelect,
  onRelation,
}: {
  nodes: Contribution[];
  relations: Relation[];
  predicates: Info["predicates"];
  selected?: string;
  loading?: boolean;
  onSelect: (id: string) => void;
  onRelation: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null),
    instance = useRef<Core | null>(null),
    positions = useRef<Record<string, { x: number; y: number }>>({});
  const [hovered, setHovered] = useState("");
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
            width: 1.25,
            "line-color": "#57566b",
            "target-arrow-color": "#8a819c",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.65,
            opacity: 0.7,
          },
        },
        {
          selector: 'edge[layer="conceptual"], edge[layer="pedagogical"]',
          style: { "line-style": "dashed" },
        },
        {
          selector: 'edge[layer="evidential"]',
          style: { "line-color": "#bb9379", "target-arrow-color": "#bb9379" },
        },
        {
          selector: 'edge[symmetric="true"]',
          style: { "target-arrow-shape": "none" },
        },
        {
          selector: "edge:selected",
          style: {
            "line-color": "#d2b5ff",
            "target-arrow-color": "#d2b5ff",
            width: 3,
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
    const observer = new ResizeObserver(() => cy.resize());
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
        position: positions.current[n.id] || {
          x: Math.cos(i * 2.399) * Math.sqrt(i + 1) * 47,
          y: Math.sin(i * 2.399) * Math.sqrt(i + 1) * 47,
        },
      }));
    for (const e of relations) {
      const joint = e.premises.length > 1;
      const symmetric = predicates[e.predicate]?.symmetric ?? false;
      if (joint) {
        elements.push({
          data: {
            id: `joint-${e.id}`,
            relation: e.id,
            label: "joint premises",
            color: "#d0c4ed",
          },
          classes: "joint",
          position: positions.current[`joint-${e.id}`] || { x: 0, y: 0 },
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
            label: words(e.predicate),
            symmetric: "false",
          },
        });
    }
    const fresh = nodes.every((n) => !positions.current[n.id]);
    const viewport = { zoom: cy.zoom(), pan: { ...cy.pan() } };
    cy.elements().remove();
    cy.add(elements);
    if (fresh && nodes.length > 1) {
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
        aria-label={`Knowledge graph with ${nodes.length} contributions and ${relations.length} relationships. Use the adjacent list for keyboard navigation.`}
      />
      <div className="graph-caption">
        <span className="live-dot" />{" "}
        {hovered ||
          "Drag to move · click an idea or arrow · use List for full titles"}
      </div>
      <div className="graph-controls">
        <button
          aria-label="Zoom in"
          onClick={() =>
            instance.current?.zoom((instance.current?.zoom() || 1) * 1.25)
          }
        >
          +
        </button>
        <button
          aria-label="Zoom out"
          onClick={() =>
            instance.current?.zoom((instance.current?.zoom() || 1) / 1.25)
          }
        >
          −
        </button>
        <button
          aria-label="Fit graph"
          onClick={() => instance.current?.fit(undefined, 65)}
        >
          Overview
        </button>
        <button
          aria-label="Focus selected idea"
          onClick={() => {
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
