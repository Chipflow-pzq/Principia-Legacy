"""Read-only smoke check of actual Nginx HTML, assets, CSP and public snapshot."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


def check(base, assets, release=None):
    base = base.rstrip("/") + "/"
    root = Path(assets)
    results = []

    def request(path, method="GET"):
        req = urllib.request.Request(base + path, method=method)
        try:
            response = urllib.request.urlopen(req, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    for path in ("", "index.html"):
        status, headers, content = request(path)
        assert status == 200, (path, status)
        assert content == (root / "index.html").read_bytes(), path
        policies = headers.get_all("Content-Security-Policy") or []
        assert len(policies) == 1, ("intersecting or missing HTML policies", policies)
        assert "https://api.siliconflow.cn" in policies[0], "exploration blocked"
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("Referrer-Policy") == "no-referrer"
        assert "no-cache" in headers.get("Cache-Control", ""), "HTML must revalidate"
        results.append({"path": path or "/", "status": status, "bytes": len(content)})
    prefix = urllib.parse.urlsplit(base).path
    for asset in re.findall(r'(?:src|href)="([^"]+)"', content.decode()):
        assert asset.startswith(prefix + "assets/"), asset
        relative = asset[len(prefix):]
        status, _, body = request(relative)
        assert status == 200, (relative, status)
        assert body == (root / relative).read_bytes(), relative
        results.append({"path": relative, "status": status,
                        "sha256": hashlib.sha256(body).hexdigest()})
    for path in (".env", ".git/config", "assets/.env", "assets/missing-file.js"):
        status, _, _ = request(path)
        assert status in (403, 404), (path, status)
        results.append({"path": path, "status": status})
    status, _, _ = request("", method="POST")
    assert status in (403, 405), ("static POST", status)
    results.append({"path": "/", "method": "POST", "status": status})
    if release:
        status, _, body = request("healthz")
        assert status == 200 and json.loads(body)["release_id"] == release
        results.append({"path": "healthz", "status": status, "release_id": release})
    return {"passed": True, "base_url": base, "checks": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument("assets")
    parser.add_argument("--release")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check(args.base_url, args.assets, args.release)
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload)
    print(payload, end="")
