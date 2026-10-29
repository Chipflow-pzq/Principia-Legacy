"""Small shared serialization and filesystem helpers; no network imports."""

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def root_path(value=None):
    return Path(
        value
        or os.environ.get("PRINCIPIA_DATA_HOME")
        or os.environ.get("PRINCIPIA_HOME")
        or Path(__file__).resolve().parents[2]
    ).resolve()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def internal_snapshot(release_id):
    """Keep development checkpoints reproducible without indexing each by default."""
    return release_id.startswith("before-") or bool(
        re.fullmatch(r"\d+\.\d+\.\d+-(?:qa|review)\d+", release_id)
    )


def digest(value):
    data = (
        value
        if isinstance(value, bytes)
        else json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode()
    )
    return hashlib.sha256(data).hexdigest()


def record_hash(record):
    return digest({k: v for k, v in record.items() if k != "content_hash"})


def seal(record):
    record["content_hash"] = record_hash(record)
    return record


def read_json(path, default=None):
    return (
        json.loads(Path(path).read_text(encoding="utf-8"))
        if Path(path).exists()
        else default
    )


def read_lines(path):
    if not Path(path).exists():
        return []
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path, value):
    atomic_write(
        path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def write_lines(path, values):
    atomic_write(
        path,
        "".join(
            json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n" for v in values
        ),
    )


def accepts_gzip(value):
    """Honor an explicit gzip preference, including q=0 refusal."""
    for entry in value.lower().split(","):
        parts = [part.strip() for part in entry.split(";")]
        if parts[0] != "gzip":
            continue
        try:
            quality = next(
                (float(p.split("=", 1)[1]) for p in parts[1:] if p.startswith("q=")),
                1.0,
            )
            return 0 < quality <= 1
        except ValueError:
            return False
    return False


def encode_snapshot(value):
    """Compress rebuildable SQLite metadata; canonical manifests stay untouched."""
    import zlib

    return b"PLZ1" + zlib.compress(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode(),
        level=6,
    )


def decode_snapshot(value):
    """Read current compressed indexes and earlier text indexes."""
    import zlib

    if isinstance(value, bytes) and value.startswith(b"PLZ1"):
        decoder = zlib.decompressobj()
        value = decoder.decompress(value[4:], 512 * 1024**2 + 1)
        if len(value) > 512 * 1024**2 or not decoder.eof or decoder.unused_data:
            raise ValueError("Invalid or oversized compiled snapshot")
    return json.loads(value)
