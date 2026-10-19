#!/usr/bin/env python3
"""Conservative hosted update readiness gate; never downloads or publishes."""
import argparse
import json
from pathlib import Path
import sys

REQUIRED = ("source_access_reviewed", "reuse_rights_reviewed", "public_scope_verified",
            "collector_verified", "publication_rollback_tested", "live_mcp_verified",
            "quota_measured", "owner_approved")


def check(config_path: Path) -> None:
    if not config_path.is_file():
        raise ValueError("No approved release configuration exists")
    config = json.loads(config_path.read_text())
    if not isinstance(config, dict):
        raise ValueError("Invalid release configuration")
    if config.get("status") != "approved":
        raise ValueError("Release not approved")
    missing = [key for key in REQUIRED if config.get(key) is not True]
    if missing:
        raise ValueError("Release gates incomplete: " + ", ".join(missing))
    # No collector/publisher is implemented: passing labels alone must
    # never activate a job that could imply data publication is authorized.
    raise ValueError("Public collector and publisher not implemented or verified")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        check(args.config)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"BLOCKED: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
