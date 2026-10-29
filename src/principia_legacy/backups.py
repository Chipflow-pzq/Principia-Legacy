"""Checksummed data-home backups and public review snapshots with safe restoration.

Private backups contain authoring evidence and receipts and are never served by
the reader. Explicit review snapshots exclude private caches and pin a frozen
release. Credentials stay outside the data home in both cases.
"""

from hashlib import sha256
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tarfile
import tempfile

from .authoring_store import writer, recover
from .common import now, write_json

PUBLIC_DIRS = (
    "corpus",
    "manifests",
    "config",
    "prompts",
    "schemas",
    "tours",
    "reports",
)
PRIVATE_DIRS = (
    "sources",
    "jobs",
    "receipts",
    "curated",
    "quarantine",
    "expansion",
    "commits",
    "recovery-1.5",
)


def file_hash(path):
    value = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


class HashingReader:
    def __init__(self, stream):
        self.stream, self.hash = stream, sha256()

    def read(self, size):
        data = self.stream.read(size)
        self.hash.update(data)
        return data


def backup(root, output, review_release=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root) or output.exists():
        raise ValueError("Choose a new backup path outside the data home")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".partial")
    if temporary.exists():
        raise ValueError(
            "An interrupted backup exists; preserve it and choose a new path"
        )
    with writer(root):
        recover(root)
        if review_release and (
            Path(review_release).name != review_release
            or not (root / "manifests/releases" / (review_release + ".json")).is_file()
        ):
            raise ValueError("Review snapshots require an existing frozen release")
        roots = [root / d for d in PUBLIC_DIRS]
        if not review_release:
            roots += [root / ".work" / d for d in PRIVATE_DIRS]
        files = sorted(
            {p for directory in roots for p in directory.rglob("*") if p.is_file()}
        )
        if any(p.is_symlink() or not p.resolve().is_relative_to(root) for p in files):
            raise ValueError("Backup refuses symlinks and files outside its data home")
        with tempfile.TemporaryDirectory(
            prefix="principia-ledger-"
        ) as temporary_ledger:
            ledger = Path(temporary_ledger) / "coordination.sqlite"
            entries = [(str(p.relative_to(root)), p) for p in files]
            if not review_release:
                with sqlite3.connect(
                    (root / ".work/coordination.sqlite").as_uri() + "?mode=ro", uri=True
                ) as source:
                    with sqlite3.connect(ledger) as destination:
                        source.backup(destination)
                entries.append((".work/coordination.sqlite", ledger))
            manifest = {
                "format": "principia-review-snapshot/v1"
                if review_release
                else "principia-private-backup/v1",
                "created_at": now(),
                "review_release": review_release,
                "files": {},
                "notice": "Explicit offline review copy; no private source cache, jobs or usage ledger. Canonical authoring remains on the server."
                if review_release
                else "Private source evidence and authoring receipts; never publish this archive.",
            }
            with tarfile.open(temporary, "w:gz", compresslevel=3) as archive:
                for name, path in entries:
                    # One open descriptor pins an atomically replaced job file.
                    # Hash exactly the bytes archived, not a preceding version.
                    with path.open("rb") as stream:
                        stat = os.fstat(stream.fileno())
                        info = tarfile.TarInfo(name)
                        info.size, info.mtime, info.mode = (
                            stat.st_size,
                            stat.st_mtime,
                            0o600,
                        )
                        reader = HashingReader(stream)
                        archive.addfile(info, reader)
                        manifest["files"][name] = reader.hash.hexdigest()
                content = json.dumps(manifest, sort_keys=True).encode()
                info = tarfile.TarInfo("BACKUP_MANIFEST.json")
                info.size = len(content)
                archive.addfile(info, io.BytesIO(content))
    temporary.rename(output)
    receipt = {
        "archive": output.name,
        "sha256": file_hash(output),
        "bytes": output.stat().st_size,
        "files": len(entries),
        "created_at": manifest["created_at"],
        "private": not bool(review_release),
        "review_release": review_release,
    }
    write_json(output.with_name(output.name + ".receipt.json"), receipt)
    return receipt


def restore(archive_path, destination, expected_hash):
    archive_path, destination = (
        Path(archive_path).resolve(),
        Path(destination).resolve(),
    )
    if destination.exists():
        raise ValueError("Restore destination must not exist")
    if file_hash(archive_path) != expected_hash:
        raise ValueError("Backup checksum mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=".principia-restore-", dir=destination.parent)
    )
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            names = set()
            for item in members:
                name = PurePosixPath(item.name)
                if (
                    not item.isfile()
                    or name.is_absolute()
                    or ".." in name.parts
                    or item.name in names
                ):
                    raise ValueError("Unsafe or duplicate backup member")
                if item.size > 2 * 1024**3:
                    raise ValueError("Oversized backup member")
                names.add(item.name)
            manifest = json.load(archive.extractfile("BACKUP_MANIFEST.json"))
            if manifest.get("format") not in {
                "principia-private-backup/v1",
                "principia-review-snapshot/v1",
            } or names != set(manifest["files"]) | {"BACKUP_MANIFEST.json"}:
                raise ValueError("Invalid backup inventory")
            archive.extractall(temporary, filter="data")
        for name, expected in manifest["files"].items():
            if file_hash(temporary / name) != expected:
                raise ValueError("Restored file checksum mismatch: " + name)
        with writer(temporary):
            recover(temporary)
        temporary.rename(destination)
        return {
            "restored_files": len(manifest["files"]),
            "destination": str(destination),
            "archive_sha256": expected_hash,
            "verified": True,
            "review_release": manifest.get("review_release"),
            "index_rebuild_required": True,
        }
    except BaseException:
        shutil.rmtree(temporary)
        raise
