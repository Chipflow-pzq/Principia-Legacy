"""Small shared serialization and filesystem helpers; no network imports."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def root_path(value=None):
    return Path(
        value or os.environ.get("PRINCIPIA_HOME") or Path(__file__).resolve().parents[2]
    ).resolve()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
