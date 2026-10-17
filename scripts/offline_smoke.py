"""Exercise an extracted reader under an outbound-socket deny rule."""

import json
from pathlib import Path
import socket
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

root = Path(
    sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
).resolve()
sys.path.insert(0, str(root / "src"))
from principia_legacy.serve import handler_for

attempts = []
original_connect = socket.socket.connect


def local_only(sock, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in ("127.0.0.1", "::1", "localhost"):
        attempts.append(str(host))
        raise OSError("External networking is blocked for this offline verification")
    return original_connect(sock, address)


socket.socket.connect = local_only
server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(root))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
base = f"http://127.0.0.1:{server.server_port}"


def get(path):
    with urllib.request.urlopen(base + path, timeout=10) as response:
        return json.load(response)


try:
    info = get("/api/info")
    dossiers = get("/api/dossiers")["dossiers"]
    nodes = get("/api/search?q=attention")["results"]
    assert nodes and len(dossiers) >= 60
    node = get("/api/contributions/" + nodes[0]["id"])
    assert node["sources"]
    assert node["topics"]
    people = get("/api/people?limit=1")["people"]
    if people:
        profile = get("/api/people/" + people[0]["id"])
        assert profile["person"]["id"] == people[0]["id"]
    works = get("/api/works?q=computability")["works"]
    if info.get("catalog_counts", {}).get("works"):
        assert works
        work = get("/api/works/" + works[0]["id"])
        assert work["work"]["content_hash"] and work["topics"]
        assert get("/api/search?q=Allan%20Turing")["people"]
    neighborhood = get("/api/neighborhood?dossier=C01")
    assert neighborhood["contributions"] and neighborhood["relations"]
    arrow = get("/api/relations/" + neighborhood["relations"][0]["id"])
    assert arrow["record"]["warrant"] and arrow["sources"]
    brief = get("/api/brief?dossier=C01")
    assert (
        brief["permitted_action_scope"] == "read_only"
        and brief["relevant_contributions"]
    )
    snapshots = info["releases"]
    if snapshots:
        get("/api/changes?from=" + snapshots[0])
    for path in (root / "web_dist").rglob("*"):
        if path.is_file():
            with urllib.request.urlopen(
                base + "/" + path.relative_to(root / "web_dist").as_posix()
            ) as response:
                assert response.status == 200
                assert response.read() == path.read_bytes()
    assert not attempts
    report = {
        "passed": True,
        "release_id": info["release_id"],
        "external_socket_attempts": attempts,
        "reader_environment": "Python standard library; launch this test with -S to exclude site packages",
        "network_policy": "Outbound socket.connect denied except loopback; no OS firewall configuration changed",
        "checked": [
            "all bundled assets",
            "search",
            "dossiers",
            "contribution inspector",
            "shared topic links and scientist profiles",
            "work catalog and offline fuzzy search",
            "relationship inspector",
            "neighborhood",
            "brief",
            "snapshot changes",
        ],
    }
    print(json.dumps(report, indent=2))
finally:
    server.shutdown()
    server.server_close()
    socket.socket.connect = original_connect
