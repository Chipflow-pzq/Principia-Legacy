"""Thin local reader with a supervised, private read-only SSH connection."""

import argparse
import json
import re
import signal
import socket
import subprocess
import time
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from threading import Event, Thread

from .serve import serve


class Tunnel:
    """One owner for SSH, including startup offline, sleep/wake and dropped links.

    Requests only read readiness and wake the supervisor; they never spawn SSH.
    Backoff bounds authentication/server failures without weakening host checks.
    """

    def __init__(self, host, remote_port, *, interval=15, retry_cap=15):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.host, self.remote_port = host, remote_port
        self.interval, self.retry_cap = interval, retry_cap
        self.ready = Event()
        self.stopped = Event()
        self.wake = Event()
        self.process = None
        self.last_response = 0.0
        self.thread = Thread(target=self._run, name="atlas-cloud", daemon=True)

    def start(self):
        self.thread.start()
        return self

    def invalidate(self):
        # One failed request is not proof that every channel is disconnected.
        # The supervisor confirms loss; other in-flight reads may still succeed.
        self.wake.set()

    def note_response(self):
        self.last_response = time.monotonic()

    def status(self):
        return {"state": "connected" if self.ready.is_set() else "reconnecting"}

    def _spawn(self):
        return subprocess.Popen(
            [
                "ssh",
                "-N",
                "-T",
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                "ExitOnForwardFailure=yes",
                "-o",
                "ConnectTimeout=8",
                "-o",
                "ConnectionAttempts=1",
                "-o",
                "ServerAliveInterval=10",
                "-o",
                "ServerAliveCountMax=2",
                "-o",
                "ControlMaster=no",
                "-o",
                "ControlPath=none",
                "-L",
                f"127.0.0.1:{self.port}:127.0.0.1:{self.remote_port}",
                self.host,
            ],
            stdin=subprocess.DEVNULL,
        )

    def _probe(self):
        connection = HTTPConnection("127.0.0.1", self.port, timeout=6)
        try:
            connection.request("GET", "/api/info")
            response = connection.getresponse()
            data = response.read(65537)
            return (
                response.status == 200
                and len(data) <= 65536
                and bool(json.loads(data).get("release_id"))
            )
        except (OSError, HTTPException, ValueError, AttributeError):
            return False
        finally:
            connection.close()

    def _stop_process(self):
        process, self.process = self.process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def _run(self):
        delay = 1
        try:
            while not self.stopped.is_set():
                try:
                    self.process = self._spawn()
                except OSError:
                    self.process = None
                # Give SSH time to authenticate, without preventing the UI opening.
                connected = False
                deadline = time.monotonic() + 12
                while time.monotonic() < deadline:
                    if (
                        self.stopped.is_set()
                        or self.process is None
                        or self.process.poll() is not None
                    ):
                        break
                    if self._probe():
                        connected = True
                        break
                    if self.stopped.wait(0.25):
                        break
                if connected:
                    delay = 1
                    self.ready.set()
                    print("Cloud connection ready.", flush=True)
                    while not self.stopped.is_set():
                        self.wake.wait(self.interval)
                        self.wake.clear()
                        if self.stopped.is_set():
                            break
                        if self.process.poll() is not None:
                            break
                        checked_since = time.monotonic()
                        if not self._probe():
                            # One slow response must not tear down a healthy
                            # tunnel and interrupt every in-flight browser read.
                            if self.stopped.wait(0.5):
                                break
                            if not self._probe() and self.last_response < checked_since:
                                break
                        self.ready.set()
                self.ready.clear()
                self._stop_process()
                if not self.stopped.is_set():
                    print(f"Cloud unavailable; reconnecting in {delay}s.", flush=True)
                # Requests cannot bypass the backoff or start parallel SSH jobs.
                if self.stopped.wait(delay):
                    break
                delay = min(delay * 2, self.retry_cap)
        finally:
            self.ready.clear()
            self._stop_process()

    def close(self):
        self.stopped.set()
        self.wake.set()
        self.thread.join(timeout=8)


def main(root=None):
    def stop(_signal, _frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ssh-host", default="principia-hk", help="Existing trusted SSH config alias"
    )
    parser.add_argument("--remote-port", type=int, default=18765)
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.ssh_host):
        parser.error("Use a configured SSH host alias")
    if not all(1 <= port <= 65535 for port in (args.port, args.remote_port)):
        parser.error("Invalid port")
    existing = HTTPConnection("127.0.0.1", args.port, timeout=1)
    try:
        existing.request("GET", "/api/connection")
        response = existing.getresponse()
        if response.status == 200 and json.loads(response.read(65536)).get("state") in (
            "connected",
            "reconnecting",
        ):
            print(f"Cloud preview is already running at http://127.0.0.1:{args.port}/")
            return
    except (OSError, HTTPException, ValueError, AttributeError):
        pass
    finally:
        existing.close()
    tunnel = Tunnel(args.ssh_host, args.remote_port).start()
    try:
        print(
            "Cloud preview reconnects automatically. No database is downloaded.",
            flush=True,
        )
        serve(
            Path(root or Path(__file__).resolve().parents[2]),
            port=args.port,
            api_origin=f"http://127.0.0.1:{tunnel.port}",
            cloud_connection=tunnel,
        )
    finally:
        tunnel.close()
