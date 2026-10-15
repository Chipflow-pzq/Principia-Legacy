"""Small command surface; the default reader never imports authoring providers."""

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from .common import read_json, read_lines, root_path, write_json
from .storage import Atlas, build, corpus
from .records import validate


def parser():
    p = argparse.ArgumentParser(
        prog="principia",
        description="A living atlas of human understanding. Browsing is local and read-only.",
    )
    p.add_argument("--root", type=Path, help="Atlas directory (or PRINCIPIA_HOME)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    v = sub.add_parser("validate")
    v.add_argument("corpus", nargs="?")
    b = sub.add_parser("build")
    b.add_argument("--offline", action="store_true")
    b.add_argument("--release")
    s = sub.add_parser("serve")
    s.add_argument("--offline", action="store_true")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    scout = sub.add_parser("scout")
    scout.add_argument("--registry")
    scout.add_argument("--dry-run", action="store_true")
    scout.add_argument("--dossier", default="all")
    scout.add_argument(
        "--allow-network",
        action="store_true",
        help="Inspect configured public sources; never admit records",
    )
    for name in ("curate", "refresh"):
        c = sub.add_parser(name)
        c.add_argument(
            "--dossier", required=True, help="Comma-separated dossier IDs, or all"
        )
        c.add_argument("--allow-network", action="store_true")
        c.add_argument("--env-file")
        c.add_argument("--model", default="deepseek-ai/DeepSeek-V4-Flash")
        c.add_argument("--workers", type=int, default=4)
        c.add_argument(
            "--budget-usd",
            type=float,
            help="Planning estimate only; spending is owner-managed",
        )
    pro = sub.add_parser("propose")
    pro.add_argument("--patch", required=True)
    pro.add_argument("--output", default="build/proposed-patch.json")
    ap = sub.add_parser("apply")
    ap.add_argument("--patch", required=True)
    rev = sub.add_parser("review")
    rev.add_argument("--target", required=True)
    rev.add_argument("--revision", type=int, required=True)
    rev.add_argument("--reviewer")
    rev.add_argument("--attestation-file")
    rev.add_argument("--machine", action="store_true")
    rev.add_argument("--allow-network", action="store_true")
    rev.add_argument("--env-file")
    rev.add_argument("--model", default="deepseek-ai/DeepSeek-V4-Flash")
    rev.add_argument("--scope", default="editorial")
    rev.add_argument("--judgment", default="accepted")
    im = sub.add_parser("impact")
    im.add_argument("--target", required=True)
    im.add_argument("--revision", type=int)
    brief = sub.add_parser("brief")
    brief.add_argument("--query", default="")
    brief.add_argument("--dossier")
    brief.add_argument(
        "--policy-profile",
        help="Explicitly supplied JSON; never grants action authority",
    )
    brief.add_argument("--release")
    brief.add_argument("--offline", action="store_true")
    brief.add_argument("--output")
    rel = sub.add_parser("release")
    rel.add_argument("--id", required=True, help="Explicit immutable release identifier")
    rel.add_argument("--report")
    ev = sub.add_parser("evaluate")
    ev.add_argument("--allow-network", action="store_true")
    ev.add_argument("--env-file")
    ev.add_argument("--split", choices=["dev", "heldout", "all"], default="dev")
    ex = sub.add_parser("expand", help="Execute a frozen, bounded source expansion plan")
    ex.add_argument("--plan", required=True)
    ex.add_argument("--allow-network", action="store_true")
    ex.add_argument("--env-file")
    ex.add_argument("--workers", type=int, default=4)
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    root = root_path(args.root)
    try:
        if args.command == "doctor":
            db = sqlite3.connect(":memory:")
            db.execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
            db.close()
            result = {
                "python": sys.version.split()[0],
                "sqlite": sqlite3.sqlite_version,
                "fts5": True,
                "web_assets": (root / "web_dist/index.html").exists(),
                "database": (root / "build/atlas.sqlite").exists(),
                "network_required_for_reader": False,
                "root": str(root),
            }
        elif args.command == "validate":
            records = (
                corpus(root)
                if not args.corpus
                else [
                    r
                    for p in sorted(Path(args.corpus).rglob("*.jsonl"))
                    for r in read_lines(p)
                ]
            )
            errors = validate(records)
            result = {"valid": not errors, "records": len(records), "errors": errors}
            if errors:
                print(json.dumps(result, indent=2))
                return 1
        elif args.command == "build":
            result = build(root, args.release)
        elif args.command == "serve":
            from .serve import serve

            if not (root / "build/atlas.sqlite").exists():
                default_release = read_json(root / "config/curation.json", {}).get(
                    "initial_release_id"
                )
                if (
                    not default_release
                    or not (
                        root / "manifests/releases" / (default_release + ".json")
                    ).exists()
                ):
                    default_release = None
                print(
                    "Building the local index from bundled records (offline)…",
                    flush=True,
                )
                build(root, default_release)
            serve(root, args.host, args.port)
            return 0
        elif args.command == "scout":
            assignments = read_lines(
                args.registry or root / "manifests/FRONTIER_REGISTRY.jsonl"
            )
            assignments = [
                d
                for d in assignments
                if args.dossier == "all" or d["id"] in args.dossier.split(",")
            ]
            result = {
                "mode": "dry_run"
                if args.dry_run or not args.allow_network
                else "source_access_inspection",
                "dossiers": assignments,
                "notice": "Registry assignments are a scouting backlog, not verified endpoint claims.",
            }
            if args.allow_network and not args.dry_run:
                from .acquire import acquire
                from urllib.parse import urlparse

                candidates = read_json(root / "config/source_candidates.json", {})
                hosts = {
                    urlparse(url).hostname
                    for urls in candidates.values()
                    for url in urls
                }
                result["sources"] = []
                for d in assignments:
                    for url in candidates.get(d["id"], []):
                        try:
                            source = acquire(root, url, hosts)
                            result["sources"].append(
                                {
                                    "dossier": d["id"],
                                    "url": url,
                                    "title": source["title"],
                                    "source_version": source["bytes_hash"],
                                    "readable_passages": len(source["passages"]),
                                    "status": "obtained; relevance not yet established",
                                }
                            )
                        except Exception as exc:
                            result["sources"].append(
                                {
                                    "dossier": d["id"],
                                    "url": url,
                                    "status": "unavailable",
                                    "reason": str(exc)[:200],
                                }
                            )
                write_json(root / ".work/scout/latest.json", result)
        elif args.command in ("curate", "refresh"):
            if not args.allow_network:
                raise ValueError(
                    "Curation requires explicit --allow-network; reader remains offline"
                )
            from .curate import run_batch

            ids = (
                [
                    r["id"]
                    for r in read_lines(root / "manifests/FRONTIER_REGISTRY.jsonl")
                ]
                if args.dossier == "all"
                else args.dossier.split(",")
            )
            if args.command == "refresh":
                from .acquire import acquire
                from .common import digest, now
                from urllib.parse import urlparse

                candidates = read_json(root / "config/source_candidates.json", {})
                hosts = {
                    urlparse(url).hostname
                    for urls in candidates.values()
                    for url in urls
                }
                outcomes = []
                for id in ids:
                    for url in candidates.get(id, []):
                        previous = read_json(
                            root / ".work/sources" / (digest(url) + ".json")
                        )
                        try:
                            fresh = acquire(root, url, hosts, force=True)
                            outcomes.append(
                                {
                                    "dossier": id,
                                    "url": url,
                                    "previous_version": previous.get("bytes_hash")
                                    if previous
                                    else None,
                                    "retrieved_version": fresh["bytes_hash"],
                                    "changed": bool(
                                        previous
                                        and previous["bytes_hash"]
                                        != fresh["bytes_hash"]
                                    ),
                                }
                            )
                        except Exception as exc:
                            outcomes.append(
                                {
                                    "dossier": id,
                                    "url": url,
                                    "state": "failed",
                                    "error": str(exc)[:200],
                                }
                            )
                result = {
                    "time": now(),
                    "refresh_proposal": outcomes,
                    "applied": False,
                    "next_step": "Inspect changed sources and submit explicit revision patches; accepted records are untouched.",
                }
                write_json(root / ".work/refresh" / (digest(result) + ".json"), result)
            else:
                run_batch(root, ids, args.env_file, args.workers, args.model)
                return 0
        elif args.command == "expand":
            if not args.allow_network:
                raise ValueError("Expansion is an explicit authoring action; add --allow-network")
            from .expansion import expand
            result = expand(root, root / args.plan, args.env_file, args.workers)
        elif args.command == "propose":
            from .lifecycle import prepare_patch

            result = prepare_patch(root, read_json(args.patch))
            write_json(root / args.output, result)
        elif args.command == "apply":
            from .lifecycle import apply_patch

            result = apply_patch(root, args.patch)
        elif args.command == "review":
            if args.machine:
                if not args.allow_network:
                    raise ValueError(
                        "Machine recheck requires explicit --allow-network"
                    )
                from .curate import review_revision

                result = review_revision(
                    root, args.target, args.revision, args.env_file, args.model
                )
            else:
                if not args.reviewer or not args.attestation_file:
                    raise ValueError(
                        "Human review requires --reviewer and --attestation-file"
                    )
                from .lifecycle import human_review

                result = human_review(
                    root,
                    args.target,
                    args.revision,
                    args.reviewer,
                    args.attestation_file,
                    args.scope,
                    args.judgment,
                )
        elif args.command == "impact":
            from .lifecycle import impact

            result = impact(root, args.target, args.revision)
        elif args.command == "brief":
            a = Atlas(root, args.release)
            try:
                result = a.brief(
                    args.query,
                    dossier=args.dossier,
                    policy=read_json(args.policy_profile)
                    if args.policy_profile
                    else None,
                )
            finally:
                a.close()
            if args.output:
                write_json(args.output, result)
        elif args.command == "release":
            from .release import package

            result = package(root, args.id, args.report)
        elif args.command == "evaluate":
            from .evaluation import evaluate

            result = evaluate(root, args.split, args.allow_network, args.env_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (
        ValueError,
        RuntimeError,
        OSError,
        KeyError,
        sqlite3.Error,
    ) as exc:
        print(f"principia: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
