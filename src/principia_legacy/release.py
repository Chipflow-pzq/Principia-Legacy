"""Allowlisted, reproducible release archives with integrity and coverage reports."""

import json
import os
import platform
import re
import zipfile
from pathlib import Path

from . import __version__
from .common import digest, internal_snapshot, read_json, read_lines, write_json
from .records import validate, visible
from .storage import Atlas, build, corpus, manifest


def freeze(root, release_id):
    from .authoring_store import Commit, recover, writer

    with writer(root):
        recover(root)
        commit = Commit(root, "freeze:" + release_id)
        result = _freeze(root, release_id, commit)
        commit.publish()
        return result


def promote(root, source_release, release_id):
    """Name an accepted frozen snapshot without including later authoring changes."""
    from .authoring_store import Commit, recover, writer

    root = Path(root)
    for name in (source_release, release_id):
        if not re.fullmatch(r"[A-Za-z0-9._-]+", name) or name in (".", "..", "working"):
            raise ValueError("Use safe immutable release identifiers")
    with writer(root):
        recover(root)
        source = read_json(root / "manifests/releases" / (source_release + ".json"))
        if not source or source.get("release_id") != source_release:
            raise ValueError("Unknown frozen source release")
        promoted = {**source, "release_id": release_id}
        path = root / "manifests/releases" / (release_id + ".json")
        previous = read_json(path)
        if previous is not None and previous != promoted:
            raise ValueError("Release identifier already frozen with different content")
        if previous is None:
            commit = Commit(root, "promote:" + source_release + ":" + release_id)
            commit.json(path, promoted)
            commit.publish()
        return promoted


def _freeze(root, release_id, commit):
    if not re.fullmatch(r"[A-Za-z0-9._-]+", release_id) or release_id in (
        ".",
        "..",
        "working",
    ):
        raise ValueError("Use a safe immutable release identifier")
    root = Path(root)
    m = manifest(root, release_id)
    path = root / "manifests/releases" / f"{release_id}.json"
    old = read_json(path)
    if old and old != m:
        raise ValueError("Release identifier already frozen with different content")
    commit.json(path, m)
    return m


def report(root):
    root = Path(root)
    a = Atlas(root)
    info = a.info()
    admitted_nodes = [r for r in a.contributions() if visible(r)]
    dossiers = a.dossiers()["dossiers"]
    coverage_targets = a.manifest.get("coverage_targets", {})
    a.close()
    receipts = list(
        {
            r["trace_id"]: r
            for r in [
                *read_lines(root / "reports/usage-receipts.jsonl"),
                *(read_json(p) for p in (root / ".work/receipts").glob("*.json")),
            ]
        }.values()
    )
    interruption_markers = [
        r for r in receipts if r.get("kind") == "batch_interruption_marker"
    ]
    attempt_receipts = [
        r for r in receipts if r.get("kind") != "batch_interruption_marker"
    ]
    usage = {
        "requests": len(attempt_receipts),
        "unreceipted_interruption_upper_bound": sum(
            r.get("upper_bound_in_flight_requests", 0) for r in interruption_markers
        ),
        "interruption_markers": len(interruption_markers),
        "successful": sum(r.get("state") == "succeeded" for r in receipts),
        "unknown_possible_charge": sum(
            r.get("state") in {"unknown_possible_charge", "running"}
            for r in attempt_receipts
        ),
        "prompt_tokens": sum(
            (r.get("usage") or {}).get("prompt_tokens", 0) for r in receipts
        ),
        "completion_tokens": sum(
            (r.get("usage") or {}).get("completion_tokens", 0) for r in receipts
        ),
        "planning_allowance_usd": 300,
        "cost_status": "Account charges managed manually by owner; tokens are receipts, not an exact bill.",
    }
    budget = read_json(root / "config/provider_budget.json", {})
    rates = {
        model: (price["input_cny_per_million"], price["output_cny_per_million"])
        for model, price in budget.get("models", {}).items()
    } or {
        "deepseek-ai/DeepSeek-V4-Flash": (3, 9),
        "deepseek-ai/DeepSeek-V4-Pro": (12, 24),
    }
    usage["current_campaign"] = read_json(root / "reports/usage-1.5.json", {})
    usage["planning_estimate"] = {
        "currency": "CNY",
        "known_token_subtotal": round(
            sum(
                (
                    (r.get("usage") or {}).get("prompt_tokens", 0)
                    * rates[r["requested_model"]][0]
                    + (r.get("usage") or {}).get("completion_tokens", 0)
                    * rates[r["requested_model"]][1]
                )
                / 1_000_000
                for r in attempt_receipts
                if r.get("requested_model") in rates
            ),
            3,
        ),
        "rates_per_million_input_output": rates,
        "pricing_source": "https://www.siliconflow.cn/pricing",
        "rates_checked": budget.get("checked_at", "2026-10-13"),
        "unpriced_requests": sum(
            r.get("requested_model") not in rates for r in attempt_receipts
        ),
        "unpriced_model_ids": sorted(
            {
                r.get("requested_model", "unknown")
                for r in attempt_receipts
                if r.get("requested_model") not in rates
            }
        ),
        "notice": "Planning estimate using dated standard rates, before cache/time discounts. Excludes models without a verified rate, unreported and unknown request usage. Unpriced requests are not free. Not the account bill or an enforcement of the USD allowance.",
    }
    outcomes = list(
        {
            (r["dossier"], r["url"]): r
            for r in [
                *read_json(root / "reports/source-attempts.json", []),
                *(read_json(p) for p in (root / ".work/curated").glob("*.json")),
                *(
                    o
                    for p in sorted((root / "reports/expansion").glob("*.json"))
                    for o in read_json(p, {}).get("outcomes", [])
                    if "dossier" in o and "url" in o
                ),
            ]
        }.values()
    )
    per_pillar = {
        p: {
            "dossiers": len([d for d in dossiers if d["pillar"] == p]),
            "populated_topics": sum(
                d["contribution_count"] > 0 for d in dossiers if d["pillar"] == p
            ),
            "initial_neighborhoods": sum(
                d["status"] == "initial_neighborhood"
                for d in dossiers
                if d["pillar"] == p
            ),
            "contributions": sum(n["pillar"] == p for n in admitted_nodes),
            "macro_checklist_coverage": sum(
                d["checklist_coverage"] for d in dossiers if d["pillar"] == p
            )
            / max(1, len([d for d in dossiers if d["pillar"] == p])),
        }
        for p in info["pillars"]
    }
    if coverage_targets.get("topic_counting_mode") == "route_ready":
        from .coverage import coverage_report

        route_report = coverage_report(root)
        for subject, row in per_pillar.items():
            row.update(
                {
                    k: v
                    for k, v in route_report["subjects"][subject].items()
                    if k
                    in {
                        "route_ready_topics",
                        "structural_route_candidates",
                        "topics_with_eight_insights",
                    }
                }
            )
    topic_metric = (
        "route_ready_topics"
        if coverage_targets.get("topic_counting_mode") == "route_ready"
        else "populated_topics"
    )
    return {
        "release_id": info["release_id"],
        "software_version": __version__,
        "maturity": "exploratory",
        "counts": info["counts"],
        "human_reviewed_contributions": info["human_reviewed"],
        "independent_human_audit": "not performed",
        "coverage": per_pillar,
        "target": coverage_targets
        or {
            "dossiers": 60,
            "contributions": [1500, 2500],
            "relations": [3000, 5000],
        },
        "content_target_met": (
            all(
                v[topic_metric] >= coverage_targets.get("topics_per_subject", 200)
                and v["contributions"]
                >= coverage_targets.get("insights_per_subject", 2000)
                for v in per_pillar.values()
            )
            if coverage_targets
            else info["counts"]["contribution"] >= 1500
            and info["counts"]["relation"] >= 3000
            and all(d["status"] == "initial_neighborhood" for d in dossiers)
        ),
        "shortfall_by_subject": {
            p: {
                topic_metric: max(
                    0,
                    coverage_targets.get("topics_per_subject", 200) - v[topic_metric],
                ),
                "unique_primary_subject_insights": max(
                    0,
                    coverage_targets.get("insights_per_subject", 2000)
                    - v["contributions"],
                ),
            }
            for p, v in per_pillar.items()
        }
        if coverage_targets
        else {},
        "gaps": {d["id"]: d["gaps"] for d in dossiers},
        "source_attempts": [
            {
                k: value
                for k, value in outcome.items()
                if k
                in {
                    "dossier",
                    "url",
                    "state",
                    "source_title",
                    "error",
                    "reason",
                    "screened",
                    "gaps",
                    "admission",
                    "previous_attempts",
                }
            }
            for outcome in outcomes
        ],
        "usage": usage,
        "test_machine": {
            "system": platform.system(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
        },
        "limitations": [
            "Machine screening is not expert approval.",
            "No claim of complete human knowledge coverage or solved alignment.",
            "Source access and historical ancestry remain incomplete.",
        ],
        "performance": read_json(root / "build/performance.json", {}),
        "calibration": read_json(root / "build/calibration-summary.json", {}),
        "evaluation": read_json(root / "build/evaluation-summary.json", {}),
    }


ALLOW_DIRS = {
    "src",
    "schemas",
    "corpus",
    "manifests",
    "tours",
    "policy_profiles",
    "prompts",
    "config",
    "docs",
    "scripts",
    "tests",
    ".github",
    "web_dist",
    "reports",
    "hosting",
}
ALLOW_FILES = {
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "AGENTS.md",
    "LICENSE",
    "DATA_LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
    "GOVERNANCE.md",
    "SAFETY.md",
    "BUILD_STATUS.md",
    "CHANGELOG.md",
    "pyproject.toml",
    ".gitignore",
    ".gitattributes",
    "start.py",
    "start.command",
    "start.bat",
    "start.sh",
}
WEB_FILES = {
    "package.json",
    "pnpm-lock.yaml",
    "pnpm-workspace.yaml",
    "tsconfig.json",
    "vite.config.ts",
    "index.html",
    "playwright.config.ts",
    "playwright.hosted.config.ts",
    "scripts-check-math.mjs",
}


def package(root, release_id, report_path=None, kind="full"):
    if kind not in {"full", "reader", "source"}:
        raise ValueError("Choose full, reader or source packaging")
    root = Path(root)
    errors = validate(corpus(root))
    if errors:
        raise ValueError("\n".join(errors[:20]))
    freeze(root, release_id)
    build(root, release_id)
    release_report = report(root)
    release_report["package_kind"] = kind
    release_report["history_scope"] = (
        "All public releases and canonical record revisions; internal correction and development checkpoints remain in the full source archive and authoritative data home."
        if kind == "reader"
        else "All canonical records and immutable manifests, including internal correction checkpoints."
    )
    files = []
    # Prune ignored trees before walking: source caches and node_modules may be
    # much larger than the release and must never enter the packaging scan.
    excluded = {
        "node_modules",
        "__pycache__",
        ".work",
        ".venv",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        "test-results",
        "playwright-report",
        ".secrets",
    }
    candidates = []
    for directory, children, names in os.walk(root, followlinks=False):
        children[:] = [
            name
            for name in children
            if name not in excluded and not (Path(directory) / name).is_symlink()
        ]
        candidates.extend(Path(directory) / name for name in names)
    for p in candidates:
        if not p.is_file() or p.is_symlink():
            continue
        relative = p.relative_to(root)
        parts = relative.parts
        if kind == "source" and parts[0] == "build":
            continue
        if (
            kind == "reader"
            and parts[:2] == ("manifests", "releases")
            and internal_snapshot(p.stem)
            and p.stem != release_id
        ):
            continue
        if any(
            x
            in {
                "node_modules",
                "__pycache__",
                ".work",
                ".venv",
                ".git",
                ".pytest_cache",
                ".ruff_cache",
                "test-results",
                "playwright-report",
                ".DS_Store",
                ".secrets",
            }
            for x in parts
        ):
            continue
        if parts[:2] == ("hosting", "evidence"):
            continue
        if p.name.startswith(".env") or p.suffix.lower() in {
            ".pem",
            ".key",
            ".p12",
            ".pfx",
        }:
            continue
        allowed = (
            parts[0] in ALLOW_DIRS
            or str(relative) in ALLOW_FILES
            or (
                parts[0] == "web"
                and (parts[1] in WEB_FILES or parts[1] in {"src", "tests"})
            )
            or relative.as_posix()
            in {
                "build/atlas.sqlite",
                "build/performance.json",
                "build/calibration-summary.json",
                "build/evaluation-summary.json",
                "build/evaluation-results.jsonl",
                "build/audit-sample.json",
                "build/test-report.txt",
                "build/usage-receipts.jsonl",
                "build/bridge-screening.json",
                "build/offline-verification.json",
                "build/living-verification.json",
                "build/coverage.json",
                "build/browser-performance.json",
            }
        )
        if not allowed:
            continue
        # A release is allowlisted and must not include credential-shaped strings.
        if p.suffix in {
            ".json",
            ".jsonl",
            ".md",
            ".txt",
            ".py",
            ".ts",
            ".tsx",
            ".html",
            ".yaml",
            ".toml",
        }:
            text = p.read_text(errors="replace")
            if re.search(r"\bsk-[A-Za-z0-9_-]{24,}\b", text):
                raise ValueError(f"Credential-shaped content in {relative}")
        files.append((relative, p))
    size = sum(p.stat().st_size for _, p in files)
    if size > 5_000_000_000:
        raise ValueError("Release exceeds hard 5 GB ceiling")
    if size > 3_000_000_000:
        raise ValueError(
            "Release exceeds 3 GB soft ceiling; reduce package before publishing"
        )
    release_report["sizes"] = {
        "installed_bytes": size,
        "source_cache_bytes": sum(
            p.stat().st_size for p in (root / ".work/sources").rglob("*") if p.is_file()
        ),
        "database_bytes": 0
        if kind == "source"
        else (root / "build/atlas.sqlite").stat().st_size,
        "size_investigation_required": size > 1_000_000_000,
    }
    checksums = {rel.as_posix(): digest(p.read_bytes()) for rel, p in sorted(files)}
    checksum_bytes = json.dumps(checksums, indent=2, sort_keys=True).encode()
    # Stabilize the self-described installed size before writing the archive.
    for _ in range(4):
        report_bytes = json.dumps(release_report, indent=2, sort_keys=True).encode()
        release_report["sizes"]["installed_bytes"] = (
            size + len(checksum_bytes) + len(report_bytes)
        )
    out = root / "dist"
    out.mkdir(exist_ok=True)
    suffix = "" if kind == "full" else "-" + kind
    destination = out / f"principia-legacy-{release_id}{suffix}.zip"
    with zipfile.ZipFile(
        destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for rel, p in sorted(files):
            z = zipfile.ZipInfo(
                f"principia-legacy/{rel.as_posix()}", (2026, 10, 12, 0, 0, 0)
            )
            z.compress_type = zipfile.ZIP_DEFLATED
            z.external_attr = (
                0o755 if rel.suffix in (".sh", ".command") else 0o644
            ) << 16
            archive.writestr(z, p.read_bytes())
        for name, value in [
            ("CHECKSUMS.json", checksums),
            ("RELEASE_REPORT.json", release_report),
        ]:
            z = zipfile.ZipInfo("principia-legacy/" + name, (2026, 10, 12, 0, 0, 0))
            z.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(z, json.dumps(value, indent=2, sort_keys=True))
    with zipfile.ZipFile(destination) as archive:
        release_report["sizes"]["installed_bytes"] = sum(
            info.file_size for info in archive.infolist()
        )
    release_report["sizes"]["download_bytes"] = destination.stat().st_size
    release_report["archive_sha256"] = digest(destination.read_bytes())
    write_json(
        report_path or root / "build" / ("release-report" + suffix + ".json"),
        release_report,
    )
    (out / (destination.name + ".sha256")).write_text(
        release_report["archive_sha256"] + "  " + destination.name + "\n"
    )
    return {
        "archive": str(destination),
        "report": str(
            report_path or root / "build" / ("release-report" + suffix + ".json")
        ),
        "counts": release_report["counts"],
        "sizes": release_report["sizes"],
        "content_target_met": release_report["content_target_met"],
    }
