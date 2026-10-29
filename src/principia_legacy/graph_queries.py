"""Bounded graph traversal with complete joint-premise groups and typed directions."""

from .records import PREDICATES


class GraphQueries:
    def adjacent_relations(
        self, ids, layers, complete=False, limit=None, direction="both"
    ):
        if not ids or not layers:
            return []
        placeholders = ",".join("?" for _ in ids)
        layer_placeholders = ",".join("?" for _ in layers)
        query = f"SELECT DISTINCT r.id FROM adjacency a JOIN members m ON m.snapshot=a.snapshot AND m.id=a.relation_id JOIN records r ON r.id=m.id AND r.revision=m.revision WHERE a.snapshot=? AND a.endpoint_id IN ({placeholders}) AND a.layer IN ({layer_placeholders})"
        params = (self.release, *sorted(ids), *sorted(layers))
        if complete:
            query += f" AND NOT EXISTS(SELECT 1 FROM adjacency missing WHERE missing.snapshot=a.snapshot AND missing.relation_id=a.relation_id AND missing.endpoint_id NOT IN ({placeholders}))"
            params += tuple(sorted(ids))
        if direction != "both":
            symmetric = [name for name, meaning in PREDICATES.items() if meaning[1]]
            marks = ",".join("?" for _ in symmetric)
            query += (
                f" AND (a.role=? OR json_extract(r.payload,'$.predicate') IN ({marks}))"
            )
            params += (
                "conclusion" if direction == "ancestors" else "premise",
                *symmetric,
            )
        query += " ORDER BY a.relation_id"
        if limit is not None:
            query += " LIMIT ?"
            params += (limit,)
        ids = [row[0] for row in self.db.execute(query, params)]
        return self.get_many(ids, "relation")

    def neighborhood(
        self,
        dossier=None,
        seed=None,
        layers=None,
        human=False,
        limit=80,
        hops=1,
        direction="both",
    ):
        limit = min(max(int(limit), 1), 200)
        hops = min(max(int(hops), 0), 6)
        valid_layers = {p[0] for p in PREDICATES.values()}
        layers = set(valid_layers if layers is None else layers)
        if not layers <= valid_layers:
            raise ValueError("Unknown relationship layer")
        if direction not in ("both", "ancestors", "descendants"):
            raise ValueError("Invalid traversal direction")

        def allowed(ids):
            result = set()
            ids = sorted(ids)
            for start in range(0, len(ids), 400):
                batch = ids[start : start + 400]
                marks = ",".join("?" for _ in batch)
                result.update(
                    r[0]
                    for r in self.db.execute(
                        f"SELECT id FROM visible_nodes WHERE snapshot=? AND id IN ({marks})"
                        + (" AND human!='not_reviewed'" if human else ""),
                        (self.release, *batch),
                    )
                )
            return result

        truncated = False

        def eligible(ids, complete=False):
            nonlocal truncated
            edge_limit = None if complete or not seed else max(400, limit * 4)
            edges = self.adjacent_relations(
                ids, layers, complete, edge_limit, direction if not complete else "both"
            )
            if edge_limit and len(edges) >= edge_limit:
                truncated = True
            ends = {x["id"] for e in edges for x in [*e["premises"], e["conclusion"]]}
            available = allowed(ends)
            return [
                e
                for e in edges
                if (not human or self.human_state(e) != "not_reviewed")
                and all(x["id"] in available for x in [*e["premises"], e["conclusion"]])
            ]

        available_count = None
        if seed:
            if seed not in allowed({seed}):
                raise KeyError(seed)
            selected = {seed}
            for _ in range(hops):
                for e in eligible(selected):
                    premises = {x["id"] for x in e["premises"]}
                    conclusion = e["conclusion"]["id"]
                    symmetric = PREDICATES[e["predicate"]][1]
                    if (
                        (direction in ("both", "ancestors") or symmetric)
                        and conclusion in selected
                    ) or (
                        (direction in ("both", "descendants") or symmetric)
                        and premises & selected
                    ):
                        addition = (premises | {conclusion}) - selected
                        if len(selected) + len(addition) <= limit:
                            selected.update(addition)
                        else:
                            truncated = True
                if len(selected) == limit:
                    break
        elif dossier:
            self.dossier(dossier)
            clause = (
                " FROM topic_positions p JOIN visible_nodes n ON n.snapshot=p.snapshot AND n.id=p.id WHERE p.snapshot=? AND p.topic=?"
                + (" AND n.human!='not_reviewed'" if human else "")
            )
            available_count = self.db.execute(
                "SELECT COUNT(*)" + clause, (self.release, dossier)
            ).fetchone()[0]
            selected = {
                r[0]
                for r in self.db.execute(
                    "SELECT p.id" + clause + " ORDER BY p.position LIMIT ?",
                    (self.release, dossier, limit),
                )
            }
        else:
            selected = {
                r[0]
                for r in self.db.execute(
                    "SELECT id FROM visible_nodes WHERE snapshot=?"
                    + (" AND human!='not_reviewed'" if human else "")
                    + " ORDER BY id LIMIT ?",
                    (self.release, min(limit, 40)),
                )
            }
        included = [
            e
            for e in eligible(selected, complete=True)
            if e["conclusion"]["id"] in selected
            and all(x["id"] in selected for x in e["premises"])
        ]
        return self.response(
            contributions=self.get_many(sorted(selected), "contribution"),
            relations=included,
            layers=sorted(layers),
            limit=limit,
            available_count=available_count,
            traversal_bounded=truncated,
            notice="Paths describe the recorded relationship layers, not exclusive ancestry or transitive proof.",
        )
