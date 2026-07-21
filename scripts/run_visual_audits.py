from __future__ import annotations

import argparse
from pathlib import Path

from _image_common import (
    compare_images,
    load_rgb,
    read_json,
    safe_id,
    save_diff,
    sha256_file,
    validate_box,
    write_json,
)


EVIDENCE_LIMITED_CLASSES = {"source_composited", "non_identifiable"}


def add_iteration_result(
    result: dict[str, object],
    reference_crop,
    baseline_crop,
    threshold: float,
    role: str,
    regression_budget: float,
) -> None:
    baseline_metrics = compare_images(reference_crop, baseline_crop, threshold)
    current_mean = float(result["mean_absolute_channel_difference"])
    baseline_mean = float(baseline_metrics["mean_absolute_channel_difference"])
    delta = round(current_mean - baseline_mean, 6)
    if role == "target":
        iteration_passed = delta < 0 or bool(result["pixel_measurement_passed"])
    else:
        iteration_passed = delta <= regression_budget
    result["iteration"] = {
        "role": role,
        "baseline_mean_absolute_channel_difference": baseline_mean,
        "current_mean_absolute_channel_difference": current_mean,
        "delta_mean_absolute_channel_difference": delta,
        "improved": delta < 0,
        "regressed": delta > 0,
        "regression_budget": regression_budget,
        "passed": iteration_passed,
    }


def audit_item(
    kind: str,
    item: dict[str, object],
    reference,
    candidate,
    baseline,
    threshold: float,
    regression_budget: float,
    output_dir: Path,
) -> dict[str, object]:
    item_id = str(item["id"])
    box = validate_box(item["box"], reference.size, f"{kind}:{item_id}")
    reference_crop = reference.crop(box)
    candidate_crop = candidate.crop(box)
    baseline_crop = baseline.crop(box) if baseline is not None else None
    prefix = safe_id(item_id)
    reference_name = f"{kind}-{prefix}-reference.png"
    candidate_name = f"{kind}-{prefix}-candidate.png"
    baseline_name = f"{kind}-{prefix}-baseline-candidate.png"
    diff_name = f"{kind}-{prefix}-diff.png"
    reference_crop.save(output_dir / reference_name)
    candidate_crop.save(output_dir / candidate_name)
    if baseline_crop is not None:
        baseline_crop.save(output_dir / baseline_name)
    save_diff(reference_crop, candidate_crop, output_dir / diff_name)
    metrics = compare_images(reference_crop, candidate_crop, threshold)
    evidence_class = str(item.get("evidence_class", "exact"))
    strict_pixel_gate = bool(item.get("strict_pixel_gate", evidence_class == "exact"))
    evidence_limited = evidence_class in EVIDENCE_LIMITED_CLASSES or not strict_pixel_gate
    pixel_measurement_passed = bool(metrics.pop("passed"))
    result = {
        "id": item_id,
        "box": list(box),
        **metrics,
        "evidence_class": evidence_class,
        "strict_pixel_gate": strict_pixel_gate,
        "evidence_limited": evidence_limited,
        "pixel_measurement_passed": pixel_measurement_passed,
        "passed": pixel_measurement_passed if not evidence_limited else False,
        "reference_crop": reference_name,
        "candidate_crop": candidate_name,
        "diff_crop": diff_name,
    }
    if baseline_crop is not None:
        result["baseline_candidate_crop"] = baseline_name
        add_iteration_result(
            result,
            reference_crop,
            baseline_crop,
            threshold,
            str(item.get("iteration_role", "guard")),
            float(item.get("regression_budget", regression_budget)),
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare source-size pixels and optionally measure current-vs-baseline iteration deltas.")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--baseline-candidate", type=Path)
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    reference = load_rgb(args.reference)
    candidate = load_rgb(args.candidate)
    baseline = load_rgb(args.baseline_candidate) if args.baseline_candidate else None
    if reference.size != candidate.size:
        raise SystemExit(f"FAIL dimensions differ: reference={reference.size}, candidate={candidate.size}")
    if baseline is not None and reference.size != baseline.size:
        raise SystemExit(f"FAIL baseline dimensions differ: reference={reference.size}, baseline={baseline.size}")
    audit_map = read_json(args.map)
    threshold = float(audit_map.get("threshold", 2))
    regression_budget = float(audit_map.get("regression_budget", 0))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save_diff(reference, candidate, args.output_dir / "full-diff.png")
    full = compare_images(reference, candidate, threshold)
    full["pixel_measurement_passed"] = bool(full["passed"])
    full["diff"] = "full-diff.png"
    if baseline is not None:
        add_iteration_result(full, reference, baseline, threshold, "guard", regression_budget)
    regions = [
        audit_item("region", item, reference, candidate, baseline, threshold, regression_budget, args.output_dir)
        for item in audit_map.get("regions", [])
    ]
    elements = [
        audit_item("element", item, reference, candidate, baseline, threshold, regression_budget, args.output_dir)
        for item in audit_map.get("elements", [])
    ]
    audited_items = regions + elements
    evidence_limited_count = sum(bool(item["evidence_limited"]) for item in audited_items)
    iteration_results = [item["iteration"] for item in audited_items if "iteration" in item]
    iteration_passed = bool(
        baseline is None
        or (full["iteration"]["passed"] and all(item["passed"] for item in iteration_results))
    )
    strict_full_image_eligible = evidence_limited_count == 0
    passed = bool(
        strict_full_image_eligible
        and full["passed"]
        and all(item["passed"] for item in audited_items)
        and iteration_passed
    )
    input_hashes = {
        "reference_sha256": sha256_file(args.reference),
        "candidate_sha256": sha256_file(args.candidate),
        "audit_map_sha256": sha256_file(args.map),
    }
    if args.baseline_candidate:
        input_hashes["baseline_candidate_sha256"] = sha256_file(args.baseline_candidate)
    report = {
        "passed": passed,
        "threshold": threshold,
        "comparison_rule": "mean_absolute_channel_difference < threshold",
        "scope": {
            "version": audit_map.get("version"),
            "id": audit_map.get("scope_id"),
            "input_hashes": input_hashes,
        },
        "reference": str(args.reference.resolve()),
        "candidate": str(args.candidate.resolve()),
        "baseline_candidate": str(args.baseline_candidate.resolve()) if args.baseline_candidate else None,
        "size": list(reference.size),
        "strict_full_image_eligible": strict_full_image_eligible,
        "evidence_limited_count": evidence_limited_count,
        "iteration_passed": iteration_passed,
        "full_image": full,
        "regions": regions,
        "elements": elements,
    }
    write_json(args.output_dir / "visual-audit.json", report)
    print(
        f"{'PASS' if passed else 'FAIL'} full={full['mean_absolute_channel_difference']} "
        f"regions={len(regions)} elements={len(elements)} evidence_limited={evidence_limited_count} "
        f"iteration_passed={iteration_passed}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
