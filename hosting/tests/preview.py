"""Loopback-only preview of the hosted build for browser tests; not a deployment server."""

import json
import mimetypes
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "hosting"))
from app import CSP, HostedReader
from principia_legacy.storage import Atlas

PREFIX = "/web/legacy/"
PORT = 18766


def preview(reader):
    assets = (ROOT / "web_hosted").resolve()

    def application(environ, start_response):
        path = environ.get("PATH_INFO", "")
        if not path.startswith(PREFIX):
            start_response("404 Not Found", [])
            return [b"Use /web/legacy/"]
        local = path[len(PREFIX):]
        if local.startswith("api/") or local == "healthz":
            return reader({**environ, "PATH_INFO": "/" + local}, start_response)
        file = (assets / (local or "index.html")).resolve()
        if not file.is_relative_to(assets) or not file.is_file():
            start_response("404 Not Found", [])
            return [b"Missing hosted asset"]
        body = file.read_bytes()
        start_response("200 OK", [
            ("Content-Type", mimetypes.guess_type(file)[0] or "application/octet-stream"),
            ("Content-Length", str(len(body))),
            ("Content-Security-Policy", CSP),
        ])
        return [b"" if environ.get("REQUEST_METHOD") == "HEAD" else body]

    return application


if __name__ == "__main__":
    if not (ROOT / "web_hosted/index.html").is_file():
        raise SystemExit("Build first: pnpm --dir web build:hosted")
    with TemporaryDirectory(prefix="principia-hosted-test-") as temporary:
        bundle = Path(temporary)
        (bundle / "build").mkdir()
        shutil.copyfile(ROOT / "build/atlas.sqlite", bundle / "build/atlas.sqlite")
        config = json.loads((ROOT / "hosting/hosting.example.json").read_text())
        config["hosts"] = [f"127.0.0.1:{PORT}"]
        (bundle / "hosting.json").write_text(json.dumps(config))
        reader = HostedReader(bundle, atlas_class=Atlas)
        with make_server("127.0.0.1", PORT, preview(reader)) as server:
            server.serve_forever()
