"""Derive a GitHub-ready source archive from a verified offline distribution."""

import hashlib
import json
from pathlib import Path
import sys
import zipfile

archive_path = Path(sys.argv[1]).resolve()
destination = archive_path.with_name(archive_path.stem + "-source.zip")
prefix = "principia-legacy/"
with zipfile.ZipFile(archive_path) as original:
    report = json.loads(original.read(prefix + "RELEASE_REPORT.json"))
    members = {
        info.filename[len(prefix) :]: original.read(info)
        for info in original.infolist()
        if info.filename.startswith(prefix)
        and not info.filename.startswith(prefix + "build/")
        and info.filename
        not in (prefix + "CHECKSUMS.json", prefix + "RELEASE_REPORT.json")
        and not info.is_dir()
    }
checksums = {
    name: hashlib.sha256(data).hexdigest() for name, data in sorted(members.items())
}
checksum_data = json.dumps(checksums, indent=2, sort_keys=True).encode()
report["distribution"] = (
    "source with prebuilt reader assets; database rebuilt offline on first launch"
)
report["sizes"]["database_bytes"] = 0
size = sum(len(data) for data in members.values()) + len(checksum_data)
for _ in range(4):
    report_data = json.dumps(report, indent=2, sort_keys=True).encode()
    report["sizes"]["installed_bytes"] = size + len(report_data)
members["CHECKSUMS.json"] = checksum_data
members["RELEASE_REPORT.json"] = json.dumps(report, indent=2, sort_keys=True).encode()
with zipfile.ZipFile(
    destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9
) as archive:
    for name, data in sorted(members.items()):
        info = zipfile.ZipInfo(prefix + name, (2026, 10, 12, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = (
            0o755 if name.endswith((".sh", ".command")) else 0o644
        ) << 16
        archive.writestr(info, data)
checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
destination.with_suffix(".zip.sha256").write_text(
    checksum + "  " + destination.name + "\n", encoding="utf-8"
)
print(
    json.dumps(
        {
            "archive": str(destination),
            "sha256": checksum,
            "download_bytes": destination.stat().st_size,
            "installed_bytes": sum(len(d) for d in members.values()),
            "files": len(members),
        },
        indent=2,
    )
)
