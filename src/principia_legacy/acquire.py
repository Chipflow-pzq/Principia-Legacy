"""Bounded public-source acquisition. Raw text stays in the private cache."""

import ipaddress
import http.client
import re
import socket
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from .common import digest, now, read_json, write_json
from .providers import tls_context

MAX_BYTES = 12_000_000
CACHE_CAP = 512_000_000


def bounded_body(response, byte_cap=MAX_BYTES, seconds=90):
    """Cap both body size and total time, including a slowly trickling source."""
    deadline = time.monotonic() + seconds
    chunks, size = [], 0
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("Source download exceeded total time cap")
        chunk = response.read1(min(65536, byte_cap + 1 - size))
        if time.monotonic() >= deadline:
            raise TimeoutError("Source download exceeded total time cap")
        if not chunk:
            return b"".join(chunks)
        size += len(chunk)
        if size > byte_cap:
            raise ValueError("Source exceeds download cap")
        chunks.append(chunk)


def public_url(url, allowed_hosts):
    p = urlparse(url)
    if (
        p.scheme != "https"
        or p.username
        or p.password
        or p.port not in (None, 443)
        or p.hostname not in allowed_hosts
    ):
        raise ValueError("Source URL is outside the explicit HTTPS allowlist")
    addresses = socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise ValueError("Private, reserved, or local source destination blocked")
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        public_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class PublicHTTPSConnection(http.client.HTTPSConnection):
    """Pin the connection to a checked public address; preserve TLS hostname checks."""

    def connect(self):
        if self._tunnel_host:
            raise ValueError("Source proxy tunnels are not supported")
        addresses = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        if not addresses or any(
            not ipaddress.ip_address(a[4][0]).is_global for a in addresses
        ):
            raise ValueError("Private, reserved, or local source destination blocked")
        last_error = None
        for family, kind, protocol, _, address in addresses[:4]:
            sock = socket.socket(family, kind, protocol)
            try:
                sock.settimeout(min(self.timeout, 12))
                sock.connect(address)
                self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
                return
            except OSError as exc:
                last_error = exc
                sock.close()
        raise last_error or OSError("No public source address connected")


class PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(PublicHTTPSConnection, request, context=tls_context())


class ArticleParser(HTMLParser):
    def __init__(self, book_content_only=False):
        super().__init__()
        self.book_content_only = book_content_only
        self.book_depth = 0
        self.math = None
        self.skip = 0
        self.parts, self.lines, self.meta = [], [], {}
        self.title_parts, self.in_title = [], False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.book_content_only and tag == "div":
            if self.book_depth or attrs.get("data-book-content") == "true":
                self.book_depth += 1
        if tag in ("script", "style", "nav", "footer"):
            self.skip += 1
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = attrs.get("name", attrs.get("property", ""))
            if key:
                self.meta.setdefault(key, []).append(attrs.get("content", ""))
        if self.book_content_only and not self.book_depth:
            return
        if tag == "math" and not self.skip:
            self.math = []
        if self.math is not None:
            self.math.append(self.get_starttag_text())
        if tag == "img" and attrs.get("alt") and not self.skip:
            self.parts.append(attrs["alt"])

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in ("script", "style", "nav", "footer"):
            self.skip = max(0, self.skip - 1)
        if self.book_content_only and not self.book_depth:
            return
        if self.math is not None:
            self.math.append("</" + tag + ">")
            if tag == "math":
                self.parts.append(" [MathML: " + "".join(self.math) + "] ")
                self.math = None
            return
        if (
            tag
            in ("p", "li", "h1", "h2", "h3", "h4", "blockquote", "tr", "section", "div")
            and self.parts
        ):
            text = re.sub(r"\s+", " ", "".join(self.parts)).strip()
            if len(text) > 30:
                self.lines.append(text)
            self.parts = []
        if self.book_content_only and tag == "div":
            self.book_depth = max(0, self.book_depth - 1)

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
            return
        if not self.skip:
            if self.book_content_only and not self.book_depth:
                return
            if self.math is not None:
                self.math.append(data)
            else:
                self.parts.append(data)


def acquire(root, url, allowed_hosts, force=False):
    root = Path(root)
    cache = root / ".work/sources" / (digest(url) + ".json")
    existing = read_json(cache)
    if existing and not force:
        return existing
    public_url(url, allowed_hosts)
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        SafeRedirect(allowed_hosts),
        PublicHTTPSHandler(),
    )
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Principia-Legacy/1.0 (scholarly source inspection; local research)",
            "Accept": "application/xml,text/xml,text/html,application/pdf,*/*",
        },
    )
    with opener.open(request, timeout=50) as response:
        public_url(response.url, allowed_hosts)
        raw = bounded_body(response)
        final_url = response.url
        content_type = response.headers.get("Content-Type", "")
    title, authors, date, license_url = "", [], "", ""
    if raw.startswith(b"%PDF"):
        import json
        import os
        import subprocess
        import sys

        env = dict(os.environ)
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
        parsed = subprocess.run(
            [sys.executable, "-m", "principia_legacy.pdf_text"],
            input=raw,
            capture_output=True,
            timeout=65,
            env=env,
        )
        if parsed.returncode:
            raise ValueError(
                "PDF parser failed or exceeded its CPU budget; use a lawful HTML/text alternative"
            )
        extracted = json.loads(parsed.stdout)
        lines, title = extracted["lines"], extracted["title"]
    else:
        html = raw.decode("utf-8", errors="replace")
        parser = ArticleParser(book_content_only='data-book-content="true"' in html)
        parser.feed(html)
        meta = parser.meta
        title = (
            meta.get("citation_title")
            or meta.get("DC.title")
            or ["".join(parser.title_parts)]
        )[0]
        authors = meta.get("citation_author", meta.get("DC.creator", []))
        date = (
            meta.get("citation_date") or meta.get("citation_publication_date") or [""]
        )[0]
        license_url = (meta.get("DC.rights") or [""])[0]
        # Parse publisher metadata as JSON, never execute embedded JavaScript.
        if (
            urlparse(url).hostname == "openstax.org"
            and "window.__PRELOADED_STATE__ = " in html
        ):
            import json

            state, _ = json.JSONDecoder().raw_decode(
                html.split("window.__PRELOADED_STATE__ = ", 1)[1]
            )
            license_url = (
                state.get("content", {})
                .get("book", {})
                .get("license", {})
                .get("url", license_url)
            )
        lines = [
            {
                "selector": f"HTML text block {i + 1}; inspect text selector",
                "text": text,
            }
            for i, text in enumerate(parser.lines)
        ]
    if sum(len(x["text"]) for x in lines) < 1000:
        raise ValueError("Insufficient readable source text")
    result = {
        "url": url,
        "resolved_url": final_url,
        "title": title,
        "creators": authors,
        "date": date,
        "license": license_url,
        "retrieved_at": now(),
        "bytes_hash": digest(raw),
        "content_type": content_type,
        "passages": [{**x, "id": f"p{i + 1}"} for i, x in enumerate(lines)],
    }
    cache.parent.mkdir(parents=True, exist_ok=True)
    if (
        sum(p.stat().st_size for p in cache.parent.rglob("*") if p.is_file()) + len(raw)
        > CACHE_CAP
    ):
        raise ValueError("Source cache cap reached; explicitly clean old cache entries")
    if existing and existing["bytes_hash"] != result["bytes_hash"]:
        write_json(
            cache.parent / "history" / (existing["bytes_hash"] + ".json"), existing
        )
    write_json(cache, result)
    return result
