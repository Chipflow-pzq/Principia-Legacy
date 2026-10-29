"""Bounded SQL reader queries; no provider, private query cache or ORM."""

import base64
import json

from . import retrieval
from .common import digest


class ReaderQueries:
    def coverage_summary(self):
        """Small indexed inventory, not a scientific-completeness certificate."""
        subjects = {}
        for pillar, total, populated, ready in self.db.execute(
            "SELECT pillar,COUNT(*),SUM(populated),SUM(COALESCE(json_extract(payload,'$.reading_route.ready'),0)) FROM topic_summaries WHERE snapshot=? GROUP BY pillar",
            (self.release,),
        ):
            subjects[pillar] = {
                "topics": total,
                "topics_with_insights": populated,
                "reading_routes": ready,
                "insights": 0,
            }
        for pillar, count in self.db.execute(
            "SELECT pillar,COUNT(*) FROM visible_nodes WHERE snapshot=? GROUP BY pillar",
            (self.release,),
        ):
            subjects[pillar]["insights"] = count
        for key, table, field in [
            ("works", "works", "insight_count"),
            ("people", "people", "contribution_count"),
        ]:
            for pillar, counts in subjects.items():
                kind = "work" if key == "works" else "person"
                count, populated = self.db.execute(
                    f"SELECT COUNT(*),COALESCE(SUM(json_extract(a.payload,'$.{field}')>0),0) FROM {table} a JOIN catalog_subjects s ON s.snapshot=a.snapshot AND s.id=a.id AND s.kind=? WHERE a.snapshot=? AND s.pillar=?",
                    (kind, self.release, pillar),
                ).fetchone()
                counts[key] = count
                counts[key + "_with_insights"] = populated
        human = self.db.execute(
            "SELECT COUNT(*) FROM visible_nodes WHERE snapshot=? AND human!='not_reviewed'",
            (self.release,),
        ).fetchone()[0]
        return self.response(
            subjects=subjects,
            human_reviewed_insights=human,
            notice="Exploratory, machine-screened content. A catalogue entry is not an extracted explanation; a checked reading route is not complete field coverage.",
        )

    def _page(self, offset, limit, cursor, scope):
        limit = min(max(int(limit), 1), 100)
        offset = max(int(offset), 0)
        signature = digest([self.snapshot_hash, scope, limit])
        if cursor:
            try:
                value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
                if (
                    value["scope"] != signature
                    or type(value["offset"]) is not int
                    or value["offset"] < 0
                ):
                    raise ValueError()
                offset = value["offset"]
            except (KeyError, TypeError, ValueError, UnicodeError):
                raise ValueError("Invalid cursor for this snapshot or filter") from None
        return offset, limit, signature

    def _next(self, offset, limit, total, signature):
        if offset + limit >= total:
            return None
        return base64.urlsafe_b64encode(
            json.dumps({"scope": signature, "offset": offset + limit}).encode()
        ).decode()

    def get_many(self, ids, kind=None):
        ids = list(dict.fromkeys(ids))
        values = {}
        for start in range(0, len(ids), 400):
            batch = ids[start : start + 400]
            marks = ",".join("?" for _ in batch)
            for row in self.db.execute(
                f"SELECT r.payload FROM records r JOIN members m ON r.id=m.id AND r.revision=m.revision WHERE m.snapshot=? AND r.id IN ({marks})",
                (self.release, *batch),
            ):
                r = json.loads(row[0])
                if kind is None or r["type"] == kind:
                    values[r["id"]] = r
        return [values[id] for id in ids if id in values]

    def _catalog_page(
        self,
        kind,
        query,
        limit,
        offset,
        human,
        pillar,
        topic=None,
        person=None,
        cursor=None,
    ):
        scope = [kind, query, human, pillar, topic, person]
        offset, limit, signature = self._page(offset, limit, cursor, scope)
        plan = self.search_plan(query)
        table = "people" if kind == "person" else "works"
        title = "name" if kind == "person" else "title"
        where, params = ["a.snapshot=?"], [self.release]
        source = f"{table} a"
        order = f"json_extract(a.payload,'$.{title}') COLLATE NOCASE,a.id"
        order_params = []
        if query.strip():
            expression = retrieval.planned_expression(plan)
            if not expression:
                return self.response(
                    **{
                        table: [],
                        "total": 0,
                        "offset": offset,
                        "limit": limit,
                        "next_cursor": None,
                    }
                )
            source += " JOIN catalog_search ON catalog_search.snapshot=a.snapshot AND catalog_search.id=a.id"
            where += ["catalog_search MATCH ?", "catalog_search.kind=?"]
            params += [expression, kind]
            order = "CASE WHEN lower(catalog_search.title)=lower(?) THEN 0 WHEN instr(lower(catalog_search.title),lower(?))=1 THEN 1 ELSE 2 END,bm25(catalog_search,0,0,0,8,1),a.id"
            order_params = [query.strip(), query.strip()]
        if pillar:
            where.append(
                "EXISTS(SELECT 1 FROM catalog_subjects c WHERE c.snapshot=a.snapshot AND c.id=a.id AND c.kind=? AND c.pillar=?)"
            )
            params += [kind, pillar]
        if human:
            membership, key = (
                ("person_members", "person")
                if kind == "person"
                else ("work_members", "work")
            )
            where.append(
                f"EXISTS(SELECT 1 FROM {membership} m JOIN visible_nodes n ON n.snapshot=m.snapshot AND n.id=m.id WHERE m.snapshot=a.snapshot AND m.{key}=a.id AND n.human!='not_reviewed')"
            )
        for value, relation, key in [
            (topic, "work_topics", "topic"),
            (person, "work_people", "person"),
        ]:
            if value:
                where.append(
                    f"EXISTS(SELECT 1 FROM {relation} m WHERE m.snapshot=a.snapshot AND m.work=a.id AND m.{key}=?)"
                )
                params.append(value)
        clause = " FROM " + source + " WHERE " + " AND ".join(where)
        total = self.db.execute("SELECT COUNT(*)" + clause, params).fetchone()[0]
        rows = [
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT a.payload"
                + clause
                + " ORDER BY "
                + order
                + " LIMIT ? OFFSET ?",
                (*params, *order_params, limit, offset),
            )
        ]
        return self.response(
            **{
                table: rows,
                "total": total,
                "offset": offset,
                "limit": limit,
                "next_cursor": self._next(offset, limit, total, signature),
            }
        )

    def people(
        self, query="", limit=60, offset=0, human=False, pillar=None, cursor=None
    ):
        return self._catalog_page(
            "person", query, limit, offset, human, pillar, cursor=cursor
        )

    def works(
        self,
        query="",
        pillar=None,
        topic=None,
        person=None,
        human=False,
        limit=40,
        offset=0,
        cursor=None,
    ):
        return self._catalog_page(
            "work", query, limit, offset, human, pillar, topic, person, cursor
        )

    def dossiers(
        self,
        limit=None,
        offset=0,
        pillar=None,
        area=None,
        status=None,
        query="",
        cursor=None,
        summary=False,
    ):
        # No pagination arguments preserves the original API for existing clients.
        offset, page_size, signature = self._page(
            offset, limit or 100, cursor, ["topics", pillar, area, status, query]
        )
        where, params = ["snapshot=?"], [self.release]
        for field, value in [("pillar", pillar), ("area", area), ("status", status)]:
            if value:
                if value in {"populated", "pending"} and field == "status":
                    where.append("populated=" + ("1" if value == "populated" else "0"))
                elif value == "route_ready" and field == "status":
                    where.append("json_extract(payload,'$.reading_route.ready')=1")
                else:
                    where.append(field + "=?")
                    params.append(value)
        if query:
            if len(query) > 500:
                raise ValueError("Search query is too long")
            where.append("instr(lower(title),lower(?))>0")
            params.append(query)
        clause = " FROM topic_summaries WHERE " + " AND ".join(where)
        total = self.db.execute("SELECT COUNT(*)" + clause, params).fetchone()[0]
        suffix = " LIMIT ? OFFSET ?" if limit is not None or cursor else ""
        order = (
            " ORDER BY ROW_NUMBER() OVER (PARTITION BY pillar ORDER BY populated DESC,json_extract(payload,'$.flagship') DESC,id),pillar,id"
            if suffix
            else " ORDER BY populated DESC,id"
        )
        rows = [
            json.loads(r[0])
            for r in self.db.execute(
                "SELECT payload" + clause + order + suffix,
                (*params, page_size, offset) if suffix else params,
            )
        ]
        if summary:
            fields = (
                "id",
                "title",
                "pillar",
                "flagship",
                "area",
                "endpoint",
                "status",
                "work_count",
                "contribution_count",
                "relation_count",
                "source_count",
                "reading_route",
            )
            rows = [{k: d[k] for k in fields if k in d} for d in rows]
        areas = [
            r[0] or "Frontier research"
            for r in self.db.execute(
                "SELECT DISTINCT area FROM topic_summaries WHERE snapshot=? AND (? IS NULL OR pillar=?) ORDER BY area",
                (self.release, pillar, pillar),
            )
        ]
        return self.response(
            dossiers=rows,
            total=total,
            areas=areas,
            offset=offset,
            limit=page_size if suffix else total,
            next_cursor=self._next(offset, page_size, total, signature)
            if suffix
            else None,
        )

    def topic_overview(self):
        rows = []
        for (pillar,) in self.db.execute(
            "SELECT DISTINCT pillar FROM topic_summaries WHERE snapshot=? ORDER BY pillar",
            (self.release,),
        ).fetchall():
            rows.extend(
                json.loads(r[0])
                for r in self.db.execute(
                    "SELECT payload FROM topic_summaries WHERE snapshot=? AND pillar=? ORDER BY json_extract(payload,'$.flagship') DESC,populated DESC,json_extract(payload,'$.contribution_count') DESC,id LIMIT 5",
                    (self.release, pillar),
                )
            )
        selected = {d["id"]: d for d in rows}
        for tour in self.context.get("tours", []):
            for id in tour.get("dossiers", []):
                if id not in selected:
                    selected[id] = self.dossier(id)["dossier"]
        return self.response(dossiers=list(selected.values()))

    def dossier(self, id):
        row = self.db.execute(
            "SELECT payload FROM topic_summaries WHERE snapshot=? AND id=?",
            (self.release, id),
        ).fetchone()
        if not row:
            raise KeyError(id)
        return self.response(dossier=json.loads(row[0]))

    def topic_contributions(self, topic, limit=40, offset=0, human=False, cursor=None):
        self.dossier(topic)
        offset, limit, signature = self._page(
            offset, limit, cursor, ["topic-insights", topic, human]
        )
        clause = " FROM topic_members m JOIN visible_nodes n ON n.snapshot=m.snapshot AND n.id=m.id WHERE m.snapshot=? AND m.topic=?"
        if human:
            clause += " AND n.human!='not_reviewed'"
        params = (self.release, topic)
        total = self.db.execute("SELECT COUNT(*)" + clause, params).fetchone()[0]
        ids = [
            r[0]
            for r in self.db.execute(
                "SELECT n.id"
                + clause
                + " ORDER BY n.year IS NULL,n.year,n.title,n.id LIMIT ? OFFSET ?",
                (*params, limit, offset),
            )
        ]
        return self.response(
            contributions=self.get_many(ids, "contribution"),
            total=total,
            limit=limit,
            offset=offset,
            next_cursor=self._next(offset, limit, total, signature),
        )

    def search(
        self,
        query="",
        pillar=None,
        human=False,
        limit=40,
        match_any=False,
        offset=0,
        cursor=None,
        _plan=None,
    ):
        offset, limit, signature = self._page(
            offset, limit, cursor, ["search", query, pillar, human, match_any]
        )
        plan = _plan or self.search_plan(query)
        expression = retrieval.planned_expression(plan, match_any)
        named_expression = expression
        phrase = retrieval.phrase_expression(plan) if not match_any else ""
        if phrase and (
            self.db.execute(
                "SELECT 1 FROM search JOIN visible_nodes n ON n.id=search.id AND n.revision=search.revision WHERE search MATCH ? AND n.snapshot=? AND (? IS NULL OR n.pillar=?) AND (NOT ? OR n.human!='not_reviewed') LIMIT 1",
                (phrase, self.release, pillar, pillar, human),
            ).fetchone()
            or (
                not human
                and self.db.execute(
                    "SELECT 1 FROM catalog_search c WHERE catalog_search MATCH ? AND c.snapshot=? AND (? IS NULL OR EXISTS(SELECT 1 FROM catalog_subjects s WHERE s.snapshot=c.snapshot AND s.id=c.id AND s.kind=c.kind AND s.pillar=?)) LIMIT 1",
                    ("title : (" + phrase + ")", self.release, pillar, pillar),
                ).fetchone()
            )
        ):
            expression = phrase
            plan = {**plan, "phrase_priority": True}
            core = [
                w.removesuffix("s")
                for w in retrieval.tokens(query)
                if w not in retrieval.STOP
            ]
            if len(core) > 1 and len(set(core)) == 1:
                # Repeated-word method names must not become a generic single
                # word search in the catalogue either.
                named_expression = phrase
        if query.strip() and not expression:
            return self.response(
                results=[],
                people=[],
                works=[],
                topics=[],
                totals=dict.fromkeys(["ideas", "people", "works", "topics"], 0),
                offset=offset,
                limit=limit,
                next_cursor=None,
                search_interpretation=plan,
            )
        params = {
            "snapshot": self.release,
            "pillar": pillar,
            "human": human,
            "expr": expression,
            "named_expr": named_expression,
            "query": query.strip(),
        }
        # Only exact text matches generate one navigation hop. A related work or
        # person never recursively expands into another wave of ideas.
        direct = (
            "SELECT n.id,CASE WHEN instr(lower(search.title),lower(:query))=1 THEN 0 WHEN instr(lower(search.title),lower(:query))>0 THEN 1 ELSE 2 END AS priority,bm25(search,0,0,8,3,1) AS score FROM search JOIN eligible n ON n.id=search.id AND n.revision=search.revision WHERE search MATCH :expr"
            if expression
            else "SELECT id,0 AS priority,0 AS score FROM eligible"
        )
        named = (
            "SELECT catalog_search.id,catalog_search.kind,CASE WHEN lower(title)=lower(:query) THEN 0 WHEN instr(lower(title),lower(:query))=1 THEN 1 ELSE 2 END AS priority,bm25(catalog_search,0,0,0,8,1) AS score FROM catalog_search WHERE snapshot=:snapshot AND catalog_search MATCH :named_expr"
            if expression
            else "SELECT id,kind,0 AS priority,0 AS score FROM catalog_search WHERE 0"
        )
        cte = f"""WITH
        eligible AS NOT MATERIALIZED (SELECT id,revision FROM visible_nodes WHERE snapshot=:snapshot AND (:pillar IS NULL OR pillar=:pillar) AND (NOT :human OR human!='not_reviewed')),
        direct AS MATERIALIZED ({direct}),
        named AS MATERIALIZED ({named}),
        named_people AS (SELECT id FROM named WHERE kind='person' AND (:pillar IS NULL OR id IN (SELECT id FROM catalog_subjects WHERE snapshot=:snapshot AND kind='person' AND pillar=:pillar))),
        selected_works AS (SELECT id FROM named WHERE kind='work' UNION SELECT work FROM work_people WHERE snapshot=:snapshot AND person IN named_people),
        selected AS (SELECT id FROM selected_works WHERE :pillar IS NULL OR id IN (SELECT id FROM catalog_subjects WHERE snapshot=:snapshot AND kind='work' AND pillar=:pillar)),
        related_ids AS (SELECT id FROM person_members WHERE snapshot=:snapshot AND person IN named_people UNION SELECT id FROM work_members WHERE snapshot=:snapshot AND work IN selected),
        ideas AS (SELECT id,0 AS tier,priority,score FROM direct UNION ALL SELECT n.id,1,0,0 FROM related_ids r JOIN eligible n ON n.id=r.id WHERE n.id NOT IN (SELECT id FROM direct)),
        work_ids AS (SELECT id FROM selected UNION SELECT work FROM work_members WHERE snapshot=:snapshot AND id IN (SELECT id FROM direct)),
        person_ids AS (SELECT id FROM named_people UNION SELECT person FROM person_members WHERE snapshot=:snapshot AND id IN (SELECT id FROM direct) UNION SELECT person FROM work_people WHERE snapshot=:snapshot AND work IN selected),
        topic_ids AS (SELECT id FROM named WHERE kind='topic' UNION SELECT topic FROM topic_members WHERE snapshot=:snapshot AND id IN (SELECT id FROM ideas) UNION SELECT topic FROM work_topics WHERE snapshot=:snapshot AND work IN work_ids)
        """
        selections = []
        for kind, output, table, ids in [
            ("idea", "results", None, "ideas"),
            ("person", "people", "people", "person_ids"),
            ("work", "works", "works", "work_ids"),
            ("topic", "topics", "topic_summaries", "topic_ids"),
        ]:
            if kind == "idea":
                selection = "SELECT id,tier,priority,score FROM ideas"
            else:
                filter_sql = ""
                if kind == "topic":
                    filter_sql += " AND (:pillar IS NULL OR a.pillar=:pillar)"
                    member, owner = "topic_members", "topic"
                else:
                    filter_sql += f" AND (:pillar IS NULL OR a.id IN (SELECT id FROM catalog_subjects WHERE snapshot=:snapshot AND kind='{kind}' AND pillar=:pillar))"
                    member, owner = (
                        ("person_members", "person")
                        if kind == "person"
                        else ("work_members", "work")
                    )
                filter_sql += f" AND (NOT :human OR EXISTS(SELECT 1 FROM {member} m WHERE m.snapshot=:snapshot AND m.{owner}=a.id AND m.id IN (SELECT id FROM eligible)))"
                selection = (
                    f"SELECT a.id,CASE WHEN n.id IS NULL THEN 1 ELSE 0 END AS tier,COALESCE(n.priority,0) AS priority,COALESCE(n.score,0) AS score FROM {table} a LEFT JOIN named n ON n.id=a.id AND n.kind='{kind}' WHERE a.snapshot=:snapshot AND a.id IN {ids}"
                    + filter_sql
                )
            selections.append(
                "SELECT '"
                + output
                + "' AS category,id,tier,priority,score FROM ("
                + selection
                + ")"
            )
        sql = (
            cte
            + ", combined AS MATERIALIZED ("
            + " UNION ALL ".join(selections)
            + """)
        , ranked AS (SELECT category,id,
            ROW_NUMBER() OVER (PARTITION BY category ORDER BY tier,priority,score,id) AS position FROM combined)
        , totals AS (SELECT category,COUNT(*) AS total FROM combined GROUP BY category)
        SELECT totals.category,ranked.id,totals.total FROM totals LEFT JOIN ranked
          ON ranked.category=totals.category AND ranked.position>:offset AND ranked.position<=:offset+:limit
        ORDER BY totals.category,ranked.position"""
        )
        rows = self.db.execute(
            sql, {**params, "offset": offset, "limit": limit}
        ).fetchall()
        totals = dict.fromkeys(["ideas", "people", "works", "topics"], 0)
        pages = {key: [] for key in ["results", "people", "works", "topics"]}
        for category, id, total in rows:
            totals["ideas" if category == "results" else category] = total
            if id is not None:
                pages[category].append(id)
        if not any(totals.values()) and _plan is None and not match_any:
            from .semantic import search as semantic_search

            semantic = semantic_search(
                self, query, pillar, human, offset, limit, signature
            )
            if semantic:
                return semantic
        if not any(totals.values()) and plan.get("related_queries") and not match_any:
            related = plan["related_queries"]
            return self.search(
                query,
                pillar,
                human,
                limit,
                match_any,
                offset,
                cursor,
                _plan={
                    **plan,
                    "queries": related,
                    "primary_queries": [],
                    "related_queries": [],
                    "concepts": related,
                    "match_mode": "related",
                    "notice": "No direct matches in this snapshot. These related foundations may help; they do not establish coverage of your full question.",
                },
            )
        results = {"results": self.get_many(pages["results"], "contribution")}
        for output, table in [
            ("people", "people"),
            ("works", "works"),
            ("topics", "topic_summaries"),
        ]:
            selected_ids = pages[output]
            marks = ",".join("?" for _ in selected_ids)
            values = (
                {
                    r[0]: json.loads(r[1])
                    for r in self.db.execute(
                        f"SELECT id,payload FROM {table} WHERE snapshot=? AND id IN ({marks})",
                        (self.release, *selected_ids),
                    )
                }
                if selected_ids
                else {}
            )
            results[output] = [
                values[id]
                if output != "topics"
                else {
                    k: values[id][k]
                    for k in (
                        "id",
                        "title",
                        "pillar",
                        "contribution_count",
                        "relation_count",
                        "work_count",
                        "reading_route",
                    )
                }
                for id in selected_ids
            ]
        return self.response(
            **results,
            totals=totals,
            offset=offset,
            limit=limit,
            next_cursor=self._next(offset, limit, max(totals.values()), signature),
            search_interpretation=plan,
        )
