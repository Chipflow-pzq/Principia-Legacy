"""Retired first-release helper; canonical record versions must remain immutable."""

raise SystemExit(
    "This legacy helper is retired because it rewrote canonical versions. "
    "Use python3 scripts/check_connections.py --env-file /path/to/secret.env --batch new-batch instead, "
    "and apply corrections through the explicit patch workflow. "
    "No network or file changes were performed."
)
