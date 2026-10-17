"""Loopback-only GET/HEAD reader. No authoring or outbound-network routes."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from .storage import Atlas


def handler_for(root):
    root = Path(root).resolve()
    assets = (root / "web_dist").resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "PrincipiaLegacy/1.0"

        def log_message(self, *args):
            pass

        def do_POST(self):
            self.reply(405, {"error": "Reader is read-only"})

        do_PUT = do_PATCH = do_DELETE = do_POST

        def do_HEAD(self):
            self.do_GET()

        def reply(self, status, value, content_type="application/json; charset=utf-8"):
            data = (
                json.dumps(value, ensure_ascii=False).encode()
                if not isinstance(value, bytes)
                else value
            )
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; connect-src 'self' https://api.siliconflow.cn https://api.crossref.org https://www.ebi.ac.uk https://en.wikipedia.org; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.send_header(
                "Cache-Control",
                "no-store"
                if content_type.startswith("application/json")
                else "no-cache",
            )
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def do_GET(self):
            host = self.headers.get("Host", "").split(":")[0]
            if host not in ("127.0.0.1", "localhost"):
                return self.reply(403, {"error": "Invalid local Host"})
            parsed = urlparse(self.path)
            if len(self.path) > 8192:
                return self.reply(414, {"error": "URL too long"})
            q = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
            atlas = None
            try:
                if parsed.path.startswith("/api/"):
                    atlas = Atlas(root, q.get("release"))
                    path = parsed.path
                    if path == "/api/info":
                        out = atlas.info()
                    elif path == "/api/dossiers":
                        out = atlas.dossiers()
                    elif path == "/api/exploration-index":
                        out = atlas.exploration_index(
                            q.get("offset", 0), q.get("limit", 200)
                        )
                    elif path == "/api/people":
                        out = atlas.people(
                            q.get("q", ""),
                            q.get("limit", 60),
                            q.get("offset", 0),
                            q.get("human") == "true",
                            q.get("pillar"),
                        )
                    elif path.startswith("/api/people/"):
                        out = atlas.person(
                            unquote(path.rsplit("/", 1)[1]), q.get("human") == "true"
                        )
                    elif path == "/api/works":
                        out = atlas.works(
                            q.get("q", ""),
                            q.get("pillar"),
                            q.get("topic"),
                            q.get("person"),
                            q.get("human") == "true",
                            q.get("limit", 40),
                            q.get("offset", 0),
                        )
                    elif path.startswith("/api/works/"):
                        out = atlas.work(
                            unquote(path.rsplit("/", 1)[1]), q.get("human") == "true"
                        )
                    elif path == "/api/search":
                        out = atlas.search(
                            q.get("q", ""),
                            q.get("pillar"),
                            q.get("human") == "true",
                            q.get("limit", 40),
                            offset=q.get("offset", 0),
                        )
                    elif path == "/api/neighborhood":
                        out = atlas.neighborhood(
                            q.get("dossier"),
                            q.get("seed"),
                            (
                                []
                                if q.get("layers") == "none"
                                else q["layers"].split(",")
                            )
                            if q.get("layers")
                            else None,
                            q.get("human") == "true",
                            q.get("limit", 80),
                            q.get("hops", 1),
                            q.get("direction", "both"),
                        )
                    elif path.startswith("/api/contributions/"):
                        out = atlas.inspect(
                            unquote(path.rsplit("/", 1)[1]), "contribution"
                        )
                    elif path.startswith("/api/relations/"):
                        out = atlas.inspect(unquote(path.rsplit("/", 1)[1]), "relation")
                    elif path == "/api/brief":
                        out = atlas.brief(q.get("q", ""), dossier=q.get("dossier"))
                    elif path == "/api/changes":
                        out = atlas.changes(q.get("from", ""))
                    else:
                        return self.reply(
                            404,
                            {"error": "Unknown API route", "release_id": atlas.release},
                        )
                    return self.reply(200, out)
                relative = unquote(parsed.path).lstrip("/") or "index.html"
                file = (assets / relative).resolve()
                if (
                    not file.is_relative_to(assets)
                    or not file.is_file()
                    or file.is_symlink()
                ):
                    return self.reply(404, {"error": "Asset not found"})
                if file.stat().st_size > 20_000_000:
                    return self.reply(413, {"error": "Asset too large"})
                content_type = (
                    mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                )
                return self.reply(200, file.read_bytes(), content_type)
            except KeyError:
                return self.reply(
                    404,
                    {
                        "error": "Record unavailable in this snapshot",
                        "release_id": atlas.release if atlas else q.get("release"),
                    },
                )
            except (ValueError, TypeError) as exc:
                return self.reply(
                    400,
                    {
                        "error": str(exc)[:300],
                        "release_id": atlas.release if atlas else q.get("release"),
                    },
                )
            except (BrokenPipeError, ConnectionResetError):
                # Closing a tab during a response is a normal client disconnect.
                return
            except Exception:
                return self.reply(
                    500, {"error": "Reader error; run doctor and validate"}
                )
            finally:
                if atlas:
                    atlas.close()

    return Handler


def serve(root, host="127.0.0.1", port=8765):
    if host != "127.0.0.1":
        raise ValueError("Only 127.0.0.1 is supported; this is a local reader")
    server = ThreadingHTTPServer((host, port), handler_for(root))
    server.daemon_threads = True
    print(
        f"Principia-Legacy is ready at http://{host}:{server.server_port}", flush=True
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
