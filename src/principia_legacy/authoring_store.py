"""One private writer, recoverable multi-file admissions, and conservative usage estimates."""

from contextlib import closing, contextmanager
import json
from pathlib import Path
import sqlite3
import uuid
import os
import time
from .common import atomic_write, digest, now, read_json, write_json


@contextmanager
def writer(root):
    path = Path(root) / ".work/coordination.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=60)
    try:
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def recover(root):
    """Roll prepared writes forward; refuse to overwrite an unrelated edit."""
    root = Path(root).resolve()
    for path in sorted((root / ".work/commits").glob("*/journal.json")):
        journal = read_json(path)
        if journal["state"] == "committed":
            continue
        for item in journal["files"]:
            dest = (root / item["path"]).resolve()
            if not dest.is_relative_to(root) or item["path"].startswith(".work/"):
                raise ValueError("Invalid journal destination")
            current = digest(dest.read_bytes()) if dest.exists() else None
            if current == item["after"]:
                continue
            if current != item["before"]:
                raise ValueError(
                    "Authoring recovery conflicts with another edit: " + item["path"]
                )
            blob = path.parent / item["blob"]
            if blob.is_symlink() or blob.resolve().parent != path.parent.resolve():
                raise ValueError("Invalid journal payload")
            text = blob.read_text(encoding="utf-8")
            if digest(text.encode()) != item["after"]:
                raise ValueError("Damaged authoring journal")
            atomic_write(dest, text)
        journal.update(state="committed", completed_at=now())
        write_json(path, journal)


class Commit:
    """Collect writes under writer(); publish only after validation has finished."""

    def __init__(self, root, reason):
        self.root, self.reason, self.files = Path(root).resolve(), reason, {}

    def lines(self, path, values):
        self.text(
            path,
            "".join(
                json.dumps(v, ensure_ascii=False, sort_keys=True) + "\n" for v in values
            ),
        )

    def json(self, path, value):
        self.text(
            path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )

    def text(self, path, text):
        path = Path(path).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Authoring destination is outside data home")
        self.files[str(path.relative_to(self.root))] = text

    def publish(self):
        folder = self.root / ".work/commits" / str(uuid.uuid4())
        folder.mkdir(parents=True)
        entries = []
        for i, (relative, text) in enumerate(sorted(self.files.items())):
            dest, blob = self.root / relative, str(i) + ".txt"
            atomic_write(folder / blob, text)
            entries.append(
                {
                    "path": relative,
                    "before": digest(dest.read_bytes()) if dest.exists() else None,
                    "after": digest(text.encode()),
                    "blob": blob,
                }
            )
        write_json(
            folder / "journal.json",
            {
                "state": "prepared",
                "reason": self.reason,
                "created_at": now(),
                "files": entries,
            },
        )
        recover(self.root)


def reserve(root, model, request, trace):
    config = read_json(Path(root) / "config/provider_budget.json")
    if not config:
        return None  # Existing offline fixtures and legacy authoring remain compatible.
    price = config.get("models", {}).get(model)
    if not price:
        raise ValueError("No verified planning price for this model")
    # UTF-8 bytes deliberately overestimate input tokens; output reserves the cap.
    maximum = (
        (len(json.dumps(request["messages"], ensure_ascii=False).encode()) + 512)
        * price["input_cny_per_million"]
        + request["max_tokens"] * price["output_cny_per_million"]
    ) / 1_000_000
    with writer(root) as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS charges(trace TEXT PRIMARY KEY,reserved REAL,estimate REAL,state TEXT)"
        )
        exposure, unknown, uncertain = db.execute(
            "SELECT COALESCE(SUM(COALESCE(estimate,reserved)),0),COALESCE(SUM(state='unknown'),0),COALESCE(SUM(CASE WHEN state='unknown' THEN reserved ELSE 0 END),0) FROM charges"
        ).fetchone()
        if (
            exposure + maximum > config["working_ceiling_cny"]
            or unknown >= config.get("unknown_attempt_pause", 5)
            or uncertain >= config.get("uncertain_exposure_pause_cny", float("inf"))
        ):
            raise RuntimeError(
                "Provider spending or uncertain-usage pause; inspect the campaign ledger"
            )
        db.execute(
            "INSERT INTO charges VALUES(?,?,NULL,?)", (trace, maximum, "reserved")
        )
    return {
        **price,
        "reserved_cny": maximum,
        "notice": "Conservative planning estimate, not a provider bill; no cache or off-peak discount assumed.",
    }


def settle(root, trace, price, receipt):
    if price is None:
        return
    usage = receipt.get("usage") or {}
    known = receipt.get("state") != "unknown_possible_charge" and all(
        isinstance(usage.get(k), (int, float))
        for k in ("prompt_tokens", "completion_tokens")
    )
    value = (
        (
            usage["prompt_tokens"] * price["input_cny_per_million"]
            + usage["completion_tokens"] * price["output_cny_per_million"]
        )
        / 1_000_000
        if known
        else None
    )
    with writer(root) as db:
        db.execute(
            "UPDATE charges SET estimate=?,state=? WHERE trace=?",
            (value, "known" if known else "unknown", trace),
        )


class QueueBusy(RuntimeError):
    """The request never acquired a transmission slot."""


def _process_alive(pid):
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        # os.kill(pid, 0) can terminate a Windows process. Query its status instead.
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel.GetExitCodeProcess.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return (
                ctypes.get_last_error() != 87
            )  # Invalid PID; access denial is not death.
        try:
            code = wintypes.DWORD()
            return (
                not kernel.GetExitCodeProcess(handle, ctypes.byref(code))
                or code.value == 259
            )
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


@contextmanager
def provider_slot(root, model="", wait_seconds=600):
    """Four shared slots, FIFO among models not in a provider cooldown."""
    path = Path(root) / ".work/provider-slots.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    token = str(uuid.uuid4())
    deadline = time.monotonic() + wait_seconds
    with closing(sqlite3.connect(path, timeout=30)) as db, db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS slots(token TEXT PRIMARY KEY,pid INTEGER);
        CREATE TABLE IF NOT EXISTS cooldowns(model TEXT PRIMARY KEY,until REAL);
        CREATE TABLE IF NOT EXISTS waiting(sequence INTEGER PRIMARY KEY AUTOINCREMENT,token TEXT UNIQUE,pid INTEGER,model TEXT);
        """)
        db.execute(
            "INSERT INTO waiting(token,pid,model) VALUES(?,?,?)",
            (token, os.getpid(), model),
        )
    try:
        while True:
            with closing(sqlite3.connect(path, timeout=30)) as db, db:
                db.execute("BEGIN IMMEDIATE")
                for table in ("slots", "waiting"):
                    for old, pid in db.execute(
                        "SELECT token,pid FROM " + table
                    ).fetchall():
                        if not _process_alive(pid):
                            db.execute(
                                "DELETE FROM " + table + " WHERE token=?", (old,)
                            )
                first = db.execute(
                    "SELECT w.token FROM waiting w LEFT JOIN cooldowns c ON w.model=c.model WHERE coalesce(c.until,0)<=? ORDER BY w.sequence LIMIT 1",
                    (time.time(),),
                ).fetchone()
                if (
                    first
                    and first[0] == token
                    and db.execute("SELECT COUNT(*) FROM slots").fetchone()[0] < 4
                ):
                    db.execute("INSERT INTO slots VALUES(?,?)", (token, os.getpid()))
                    db.execute("DELETE FROM waiting WHERE token=?", (token,))
                    break
            if time.monotonic() >= deadline:
                raise QueueBusy("Authoring request queue is busy; no request submitted")
            time.sleep(0.1)
        yield
    finally:
        with closing(sqlite3.connect(path, timeout=30)) as db, db:
            db.execute("DELETE FROM slots WHERE token=?", (token,))
            db.execute("DELETE FROM waiting WHERE token=?", (token,))


def provider_cooldown(root, model, seconds):
    """An explicit 429 pauses this model for every local authoring worker."""
    path = Path(root) / ".work/provider-slots.sqlite"
    with closing(sqlite3.connect(path, timeout=30)) as db, db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS cooldowns(model TEXT PRIMARY KEY,until REAL)"
        )
        db.execute(
            "INSERT INTO cooldowns VALUES(?,?) ON CONFLICT(model) DO UPDATE SET until=MAX(until,excluded.until)",
            (model, time.time() + min(max(seconds, 30), 180)),
        )
