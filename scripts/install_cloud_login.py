"""Install this Mac user's lightweight preview as a restartable login service."""

import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

LABEL = "net.chipflow.principia-legacy.preview"
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("preview", type=Path, help="Installed thin preview directory")
args = p.parse_args()
if sys.platform != "darwin":
    raise SystemExit("This login-service installer is for macOS only.")
preview = args.preview.resolve()
if not (preview / "start-cloud.py").is_file():
    raise SystemExit("The preview folder must contain start-cloud.py")
agent = Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")
log_dir = Path.home() / "Library/Logs/Principia-Legacy"
agent.parent.mkdir(parents=True, exist_ok=True)
log_dir.mkdir(parents=True, exist_ok=True)
job = {
    "Label": LABEL,
    "ProgramArguments": [sys.executable, str(preview / "start-cloud.py")],
    "WorkingDirectory": str(preview),
    "RunAtLoad": True,
    "KeepAlive": True,
    "ThrottleInterval": 10,
    "ProcessType": "Background",
    "StandardOutPath": str(log_dir / "preview.log"),
    "StandardErrorPath": str(log_dir / "preview-error.log"),
}
domain = f"gui/{os.getuid()}"
subprocess.run(["launchctl", "bootout", f"{domain}/{LABEL}"], capture_output=True)
agent.write_bytes(plistlib.dumps(job))
agent.chmod(0o600)
subprocess.run(["launchctl", "bootstrap", domain, str(agent)], check=True)
print(f"Installed {LABEL}. Opens on login and restarts if it exits.")
print("Preview: http://127.0.0.1:8767/")
print(f"To stop/remove: launchctl bootout {domain}/{LABEL}; then remove {agent}")
