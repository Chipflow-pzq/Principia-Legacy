"""Create a small cloud-connected preview, without canonical data or dependencies."""

import argparse
from pathlib import Path
import shutil
import json
import hashlib

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path)
args = parser.parse_args()
dest = args.destination.resolve()
if dest.exists():
    raise SystemExit("Use a new destination to preserve existing previews.")
dest.mkdir(parents=True)
shutil.copytree(root / "web_dist", dest / "web_dist")
shutil.copytree(root / "docs/licenses", dest / "docs/licenses")
(dest / "scripts").mkdir()
shutil.copyfile(
    root / "scripts/install_cloud_login.py", dest / "scripts/install_cloud_login.py"
)
package = dest / "src/principia_legacy"
package.mkdir(parents=True)
for name in ["__init__.py", "cloud.py", "common.py", "serve.py"]:
    shutil.copyfile(root / "src/principia_legacy" / name, package / name)
for name in [
    "start-cloud.py",
    "start-cloud.command",
    "LICENSE",
    "DATA_LICENSE.md",
    "THIRD_PARTY_NOTICES.md",
]:
    shutil.copyfile(root / name, dest / name)
(dest / "README.txt").write_text(
    "Principia-Legacy private cloud preview\n\nRun: python3 start-cloud.py\nOpen: http://127.0.0.1:8767/\n\nRequires Python 3.12+, SSH, and the configured principia-hk host.\nThe data stay on the private server. Network/SSH is required to browse.\nPersonal exploration prompts and saved maps remain browser-local.\nNo API key is needed to browse. Public deployment is unchanged.\nReconnection is automatic after network interruptions.\nOptional macOS login startup: python3 scripts/install_cloud_login.py .\n"
)
(dest / "start-cloud.command").chmod(0o755)
files = {
    str(p.relative_to(dest)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in dest.rglob("*")
    if p.is_file()
}
(dest / "checksums.json").write_text(json.dumps(files, indent=2) + "\n")
print(
    json.dumps(
        {
            "path": str(dest),
            "bytes": sum(p.stat().st_size for p in dest.rglob("*") if p.is_file()),
            "files": len(files),
        }
    )
)
