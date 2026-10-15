"""Measure warm HTTP latency on the running local reader; no third-party packages."""

import json
import platform
import statistics
import sys
import time
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
if not base.startswith("http://127.0.0.1:"):
    raise SystemExit("Measure a loopback reader")


def fetch(route):
    with urllib.request.urlopen(base + route, timeout=30) as response:
        return json.load(response)


info = fetch("/api/info")
results = {}
for name, route in (
    ("search", "/api/search?q=attention"),
    ("neighborhood", "/api/neighborhood?dossier=C01&limit=200"),
    ("dossiers", "/api/dossiers"),
):
    fetch(route)
    timings = []
    for _ in range(30):
        start = time.perf_counter()
        fetch(route)
        timings.append((time.perf_counter() - start) * 1000)
    results[name] = {
        "samples": len(timings),
        "p50_ms": round(statistics.median(timings), 2),
        "p95_ms": round(sorted(timings)[28], 2),
        "max_ms": round(max(timings), 2),
    }
report = {
    "release_id": info["release_id"],
    "counts": info["counts"],
    "machine": {
        "os": platform.platform(),
        "python": platform.python_version(),
        "architecture": platform.machine(),
    },
    "warm_http": results,
    "targets": {
        "search_p95_ms": 500,
        "neighborhood_p95_ms": 1000,
        "first_view_ms": 5000,
        "combined_memory_bytes_approx": 1_000_000_000,
    },
    "browser": json.loads((root / "build/browser-performance.json").read_text())
    if (root / "build/browser-performance.json").exists()
    else {"status": "not yet measured"},
}
(root / "build/performance.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
