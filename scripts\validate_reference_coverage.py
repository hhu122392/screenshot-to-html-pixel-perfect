from __future__ import annotations

import argparse
from pathlib import Path

from _image_common import read_json, write_json


VALID_SCOPES = {"visible_frame", "full_component"}
VALID_CONTINUATIONS = {"complete", "partial", "unknown"}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reject unsupported full-component claims, unresolved continuations, and reusable clipped assets."
    )
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    spec = read_json(args.spec)
    failures: list[str] = []
    scope = spec.get("delivery_scope")
    if scope not in VALID_SCOPES:
        failures.append("delivery_scope")

    source_files = spec.get("source_files", [])
    if not source_files or any(not item.get("path") for item in source_files):
        failures.append("source_files")

    continuations = spec.get("continuations", [])
    unknowns = spec.get("unknowns", [])
    clipped_assets = spec.get("clipped_assets", [])
    full_component_complete = True

    for item in continuations:
        item_id = str(item.get("id") or "unnamed")
        status = item.get("status")
        if status not in VALID_CONTINUATIONS:
            failures.append(f"continuation-status:{item_id}")
            full_component_complete = False
        elif not item.get("evidence"):
            failures.append(f"continuation-evidence:{item_id}")
            full_component_complete = False
        elif status != "complete":
            full_component_complete = False
            if scope == "full_component":
                failures.append(f"continuation:{item_id}")

    for item in unknowns:
        item_id = str(item.get("id") or "unnamed")
        if item.get("resolved") is not True:
            full_component_complete = False
            if scope == "full_component":
                failures.append(f"unknown:{item_id}")

    for item in clipped_assets:
        item_id = str(item.get("id") or "unnamed")
        intended_use = item.get("intended_use")
        if scope == "full_component" or intended_use != "visible-fragment":
            full_component_complete = False
            failures.append(f"clipped_asset:{item_id}")

    passed = not failures
    result = {
        "passed": passed,
        "delivery_scope": scope,
        "full_component_evidence_complete": full_component_complete,
        "source_files": source_files,
        "continuations": continuations,
        "unknowns": unknowns,
        "clipped_assets": clipped_assets,
        "failures": failures,
        "p0_count": 0 if passed else 1,
    }
    write_json(args.output, result)
    print(
        f"{'PASS' if passed else 'FAIL'} scope={scope} "
        f"complete={str(full_component_complete).lower()} failures={len(failures)}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
