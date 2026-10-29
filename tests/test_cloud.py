"""The thin reader is a fixed, bounded, read-only tunnel, never an open proxy."""

from contextlib import contextmanager
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import gzip
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pytest
from principia_legacy.serve import handler_for


@contextmanager
def server(handler):
    s = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=s.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{s.server_port}"
    finally:
        s.shutdown()
        s.server_close()
        thread.join()


class Upstream(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        assert self.headers.get("Cookie") is None
        assert self.headers.get("Authorization") is None
        data = json.dumps({"release_id": "test", "path": self.path}).encode()
        if self.path.startswith("/api/compressed"):
            assert "gzip" in self.headers.get("Accept-Encoding", "")
            data = gzip.compress(data)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        if self.path.startswith("/api/compressed"):
            self.send_header("Content-Encoding", "gzip")
        self.end_headers()
        self.wfile.write(data)


def test_fixed_loopback_origin_and_remote_api(tmp_path):
    for url in [
        "https://127.0.0.1:80",
        "http://localhost:80",
        "http://169.254.169.254:80",
        "http://user:secret@127.0.0.1:80",
        "http://127.0.0.1:80/private",
    ]:
        with pytest.raises(ValueError):
            handler_for(tmp_path, url)
    (tmp_path / "web_dist").mkdir()
    (tmp_path / "web_dist/index.html").write_text("thin reader")
    with server(Upstream) as remote, server(handler_for(tmp_path, remote)) as local:
        request = Request(
            local + "/api/info",
            headers={"Cookie": "private", "Authorization": "secret"},
        )
        with urlopen(request) as response:
            value = json.load(response)
            assert (
                value["connection_mode"] == "private_cloud"
                and value["release_id"] == "test"
            )
            assert response.headers["Cache-Control"] == "no-store"
        with urlopen(local + "/api/compressed?q=word") as response:
            assert json.load(response)["path"] == "/api/compressed?q=word"
        with urlopen(local) as response:
            assert response.read() == b"thin reader"
        with pytest.raises(HTTPError) as e:
            urlopen(Request(local + "/api/info", data=b"write"))
        assert e.value.code == 405
        with pytest.raises(HTTPError) as e:
            urlopen(local + "/%2e%2e/config/secret")
        assert e.value.code == 404
    assert not (tmp_path / "build").exists()


def test_unavailable_tunnel_is_explicit(tmp_path):
    with server(Upstream) as remote:
        pass
    with server(handler_for(tmp_path, remote)) as local:
        with pytest.raises(HTTPError) as e:
            urlopen(local + "/api/search?q=test")
        assert e.value.code == 503
        assert json.load(e.value)["code"] == "cloud_unavailable"


class ResettingUpstream(BaseHTTPRequestHandler):
    def do_GET(self):
        self.close_connection = True


def test_upstream_disconnect_is_an_explicit_503(tmp_path):
    with (
        server(ResettingUpstream) as remote,
        server(handler_for(tmp_path, remote)) as local,
    ):
        with pytest.raises(HTTPError) as e:
            urlopen(local + "/api/info", timeout=3)
        assert e.value.code == 503


def test_managed_connection_has_retryable_status(tmp_path):
    from threading import Event
    from types import SimpleNamespace

    state = SimpleNamespace(ready=Event(), status=lambda: {"state": "reconnecting"})
    with server(handler_for(tmp_path, "http://127.0.0.1:9", state)) as local:
        with urlopen(local + "/api/connection") as response:
            assert json.load(response)["state"] == "reconnecting"
        with pytest.raises(HTTPError) as e:
            urlopen(local + "/api/search?q=test")
        assert json.load(e.value)["code"] == "cloud_reconnecting"


def test_supervisor_recovers_dead_and_stalled_ssh_without_parallel_children(
    monkeypatch,
):
    from threading import Event
    import time
    from principia_legacy.cloud import Tunnel

    made = []
    available = Event()

    class Process:
        def __init__(self):
            assert not any(p.poll() is None for p in made)
            self.dead = False
            made.append(self)

        def poll(self):
            return 1 if self.dead else None

        def terminate(self):
            self.dead = True

        def wait(self, timeout=None):
            return 0

    def until(condition):
        deadline = time.monotonic() + 4
        while not condition() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert condition()

    tunnel = Tunnel("trusted-test-host", 18765, interval=0.03, retry_cap=0.03)
    monkeypatch.setattr(tunnel, "_spawn", Process)
    monkeypatch.setattr(tunnel, "_probe", lambda: available.is_set())
    tunnel.start()
    try:
        assert not tunnel.ready.is_set()  # UI can start before any connectivity.
        available.set()
        until(tunnel.ready.is_set)
        probe_calls = []

        def miss_once():
            probe_calls.append(True)
            return len(probe_calls) > 1 and available.is_set()

        monkeypatch.setattr(tunnel, "_probe", miss_once)
        tunnel.wake.set()
        until(lambda: len(probe_calls) >= 2)
        assert len(made) == 1 and tunnel.ready.is_set()
        # Heavy reads and probes share one SSH transport. Two missed probes
        # cannot invalidate an actual successful response during that check.
        concurrent = []

        def missed_probe_with_live_traffic():
            concurrent.append(True)
            tunnel.note_response()
            return False

        monkeypatch.setattr(tunnel, "_probe", missed_probe_with_live_traffic)
        tunnel.invalidate()
        assert tunnel.ready.is_set()
        until(lambda: len(concurrent) >= 2)
        assert len(made) == 1 and tunnel.ready.is_set()
        monkeypatch.setattr(tunnel, "_probe", lambda: available.is_set())
        made[-1].dead = True
        until(lambda: len(made) == 2 and tunnel.ready.is_set())
        available.clear()
        tunnel.invalidate()  # Half-open connection, not merely an exited process.
        until(lambda: len(made) == 3)
        available.set()
        until(tunnel.ready.is_set)
        assert sum(p.poll() is None for p in made) == 1
    finally:
        tunnel.close()
    assert not tunnel.thread.is_alive()
    assert all(p.poll() is not None for p in made)
