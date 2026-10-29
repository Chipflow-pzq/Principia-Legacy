"""Bounded offline query expansion: named concepts, aliases and small typos.

No embeddings, model service or user-query cache. A deletion index over catalog
titles and aliases narrows spelling candidates before edit-distance comparison.
This is transparent concept matching, not an unrestricted semantic reasoner.
"""

import re
import unicodedata

STOP = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "what",
    "with",
    "who",
    "do",
    "does",
    "was",
    "were",
    "about",
}


def normalize(value):
    value = "".join(
        c
        for c in unicodedata.normalize("NFKD", value).casefold()
        if not unicodedata.combining(c)
    )
    return " ".join(re.findall(r"[^\W_]+", value, re.UNICODE))


def tokens(value):
    return normalize(value).split()[:16]


def deletes(word):
    return {word, *(word[:i] + word[i + 1 :] for i in range(len(word)))}


def distance(a, b, maximum=2):
    """Bounded optimal-string-alignment distance, including adjacent swaps."""
    if abs(len(a) - len(b)) > maximum:
        return maximum + 1
    prior = list(range(len(b) + 1))
    before = None
    for i, char in enumerate(a, 1):
        row = [i]
        for j, other in enumerate(b, 1):
            value = min(row[-1] + 1, prior[j] + 1, prior[j - 1] + (char != other))
            if before is not None and j > 1 and char == b[j - 2] and a[i - 2] == other:
                value = min(value, before[j - 2] + 1)
            row.append(value)
        if min(row) > maximum:
            return maximum + 1
        before, prior = prior, row
    return prior[-1]


def install(db):
    db.executescript("""
    CREATE TABLE spelling(snapshot TEXT,token TEXT,variant TEXT,PRIMARY KEY(snapshot,variant,token));
    CREATE INDEX spelling_token ON spelling(snapshot,token);
    """)


def index(db, snapshot, labels):
    words = {
        t
        for label in labels
        for t in tokens(label)
        if 3 <= len(t) <= 32 and t not in STOP and not t.isdigit()
    }
    db.executemany(
        "INSERT INTO spelling VALUES(?,?,?)",
        (
            (snapshot, word, variant)
            for word in sorted(words)
            for variant in sorted(deletes(word))
        ),
    )


def plan(db, snapshot, query, concepts):
    original = tokens(query)
    if not original:
        return {"queries": [], "corrections": [], "concepts": []}
    corrected, corrections = [], []
    for word in original:
        replacement = word
        if (
            4 <= len(word) <= 32
            and word not in STOP
            and not db.execute(
                "SELECT 1 FROM spelling WHERE snapshot=? AND token=? LIMIT 1",
                (snapshot, word),
            ).fetchone()
        ):
            variants = sorted(deletes(word))
            placeholders = ",".join("?" for _ in variants)
            candidates = db.execute(
                f"SELECT DISTINCT token FROM spelling WHERE snapshot=? AND variant IN ({placeholders}) LIMIT 120",
                (snapshot, *variants),
            ).fetchall()
            threshold = 2 if len(word) >= 8 else 1
            ranked = sorted(
                (distance(word, row[0], threshold), row[0]) for row in candidates
            )
            # Ambiguity stays visible as an ordinary gap, never an arbitrary name merge.
            best = [
                w for d, w in ranked if ranked and d == ranked[0][0] and d <= threshold
            ]
            if len(best) == 1:
                replacement = best[0]
                corrections.append({"from": word, "to": replacement})
        corrected.append(replacement)
    query_forms = [" ".join(original)]
    if corrected != original:
        query_forms.append(" ".join(corrected))
    # An example is an alternative entry point, not an extra word that every
    # document must contain (e.g. "language models such as ChatGPT").
    example_parts = re.split(
        r"\b(?:such as|for example)\b", " ".join(corrected), maxsplit=1
    )
    if len(example_parts) == 2 and all(part.strip() for part in example_parts):
        query_forms = [part.strip() for part in example_parts]
    # A known word can still be a misspelled name (Allan vs Alan Turing).
    # Compare a bounded set of whole-name candidates selected by FTS tokens.
    if len(original) > 1:
        candidates = db.execute(
            "SELECT title FROM catalog_search WHERE catalog_search MATCH ? AND snapshot=? AND kind='person' LIMIT 80",
            (expression([" ".join(original)], True), snapshot),
        ).fetchall()
        ranked = sorted(
            (distance(" ".join(original), normalize(row[0]), 2), normalize(row[0]))
            for row in candidates
        )
        best = list(
            dict.fromkeys(
                w for d, w in ranked if ranked and d == ranked[0][0] and 0 < d <= 2
            )
        )
        if (
            ranked
            and ranked[0][0] > 0
            and len(best) == 1
            and best[0] not in query_forms
        ):
            query_forms.append(best[0])
            corrections.append({"from": " ".join(original), "to": best[0]})
    for form in list(query_forms):
        meaningful = " ".join(w for w in tokens(form) if w not in STOP)
        if meaningful and meaningful not in query_forms:
            query_forms.append(meaningful)
        # Add a singular form only when this snapshot already contains it.
        # Keep the original too; records and people's identities are untouched.
        singular = [
            word[:-1]
            if len(word) > 4
            and word.endswith("s")
            and not word.endswith("ss")
            and db.execute(
                "SELECT 1 FROM spelling WHERE snapshot=? AND token=? LIMIT 1",
                (snapshot, word[:-1]),
            ).fetchone()
            else word
            for word in tokens(meaningful)
        ]
        alternate = " ".join(singular)
        if alternate and alternate not in query_forms:
            query_forms.append(alternate)
    expanded, related = [], []
    for concept in concepts:
        forms = [normalize(x) for x in concept["terms"]]
        for form in sorted(query_forms, key=lambda value: len(tokens(value))):
            for term in forms:
                if term and (" " + term + " ") in (" " + form + " "):
                    # These are deliberately weaker navigation suggestions. They
                    # may be tried only after all precise forms return no matches.
                    related.extend(concept.get("related", []))
                    for alternate in forms:
                        candidate = (
                            (" " + form + " ")
                            .replace(" " + term + " ", " " + alternate + " ")
                            .strip()
                        )
                        if candidate not in query_forms and candidate not in expanded:
                            expanded.append(candidate)
                    break
    queries = list(dict.fromkeys([*query_forms, *expanded]))[:6]
    return {
        "queries": queries,
        "primary_queries": [q for q in queries if q in query_forms],
        "corrections": corrections,
        "concepts": expanded[:4],
        "related_queries": list(dict.fromkeys(related))[:4],
        "match_mode": "direct",
        "method": "offline aliases, curated concepts and bounded spelling distance",
    }


def expression(queries, match_any=False):
    return " OR ".join(
        "("
        + (" OR " if match_any else " AND ").join('"' + t + '"*' for t in tokens(q))
        + ")"
        for q in queries
        if tokens(q)
    )


def planned_expression(plan, match_any=False):
    """Keep expanded scientific phrases together; scattered terms are not synonyms."""
    if match_any or "primary_queries" not in plan:
        return expression(plan["queries"], match_any)
    primary = plan["primary_queries"]
    phrases = [q for q in plan["queries"] if q not in primary]
    return " OR ".join(
        filter(
            None,
            [
                expression(primary),
                " OR ".join(
                    '"' + " ".join(tokens(q)) + '"*' for q in phrases if tokens(q)
                ),
            ],
        )
    )


def phrase_expression(plan):
    """Prefer contiguous multiword matches when the current snapshot has them.

    Scattered occurrences of 'difference' must not outrank difference-in-differences.
    This is a bounded FTS query, independent of the optional semantic encoder.
    """
    if not any(len(tokens(q)) > 1 for q in plan["queries"]):
        return ""
    return " OR ".join(
        '"' + " ".join(tokens(q)) + '"*' for q in plan["queries"] if tokens(q)
    )
