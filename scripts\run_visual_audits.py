from __future__ import annotations

import argparse
from pathlib import Path

from _image_common import compare_images, load_rgb, read_json, safe_id, save_diff, validate_box, write_json


def audit_item(
    kind: str,
    item: dict[str, object],
    reference,
    candidate,
    threshold: float,
    output_dir: Path,
) -> dict[str, object]:
    item_id = str(item["id"])
    box = validate_box(item["box"], reference.size, f"{kind}:{item_id}")
    reference_crop = reference.crop(box)
    candidate_crop = candidate.crop(box)
    prefix = safe_id(item_id)
    reference_name = f"{kind}-{prefix}-reference.png"
    candidate_name = f"{kind}-{prefix}-candidate.png"
    diff_name = f"{kind}-{prefix}-diff.png"
    reference_crop.save(output_dir / reference_name)
    candidate_crop.save(output_dir / candidate_name)
    save_diff(reference_crop, candidate_crop, output_dir / diff_name)
    metrics = compare_images(reference_crop, candidate_crop, threshold)
    return {
        "id": item_id,
        "box": list(box),
        **metrics,
        "reference_crop": reference_name,
        "candidate_crop": candidate_name,
        "diff_crop": diff_name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare full-image, region, and key-element pixels against a source-size reference.")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    reference = load_rgb(args.reference)
    candidate = load_rgb(args.candidate)
    if reference.size != candidate.size:
        raise SystemExit(f"FAIL dimensions differ: reference={reference.size}, candidate={candidate.size}")
    audit_map = read_json(args.map)
    threshold = float(audit_map.get("threshold", 2))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_diff(reference, candidate, args.output_dir / "full-diff.png")
    full = compare_images(reference, candidate, threshold)
    full["diff"] = "full-diff.png"
    regions = [
        audit_item("region", item, reference, candidate, threshold, args.output_dir)
        for item in audit_map.get("regions", [])
    ]
    elements = [
        audit_item("element", item, reference, candidate, threshold, args.output_dir)
        for item in audit_map.get("elements", [])
    ]
    passed = bool(full["passed"] and all(item["passed"] for item in regions + elements))
    report = {
        "passed": passed,
        "threshold": threshold,
        "comparison_rule": "mean_absolute_channel_difference < threshold",
        "reference": str(args.reference.resolve()),
        "candidate": str(args.candidate.resolve()),
        "size": list(reference.size),
        "full_image": full,
        "regions": regions,
        "elements": elements,
    }
    write_json(args.output_dir / "visual-audit.json", report)
    print(f"{'PASS' if passed else 'FAIL'} full={full['mean_absolute_channel_difference']} regions={len(regions)} elements={len(elements)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

