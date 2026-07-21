from __future__ import annotations

import argparse
from pathlib import Path

from _image_common import compare_images, load_rgb, read_json, save_diff, write_json


def frame_path(manifest_path: Path, entry: dict[str, object]) -> Path:
    path = Path(str(entry["file"]))
    return path if path.is_absolute() else manifest_path.parent / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare every decoded reference frame with a candidate frame at the same sequence index.")
    parser.add_argument("--reference-manifest", required=True, type=Path)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=2)
    parser.add_argument("--save-all-diffs", action="store_true")
    args = parser.parse_args()
    reference_manifest = read_json(args.reference_manifest)
    candidate_manifest = read_json(args.candidate_manifest)
    reference_frames = reference_manifest.get("frames", [])
    candidate_frames = candidate_manifest.get("frames", [])
    errors = []
    for label, manifest, frames in (
        ("reference", reference_manifest, reference_frames),
        ("candidate", candidate_manifest, candidate_frames),
    ):
        declared = int(manifest.get("declared_frame_count", len(frames)))
        decoded = int(manifest.get("decoded_frame_count", len(frames)))
        if declared != decoded or decoded != len(frames):
            errors.append(f"{label} frame count mismatch: declared={declared}, decoded={decoded}, listed={len(frames)}")
    if len(reference_frames) != len(candidate_frames):
        errors.append(f"sequence count mismatch: reference={len(reference_frames)}, candidate={len(candidate_frames)}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    if not errors:
        for index, (reference_entry, candidate_entry) in enumerate(zip(reference_frames, candidate_frames)):
            reference = load_rgb(frame_path(args.reference_manifest, reference_entry))
            candidate = load_rgb(frame_path(args.candidate_manifest, candidate_entry))
            try:
                metrics = compare_images(reference, candidate, args.threshold)
            except ValueError as error:
                errors.append(f"frame {index}: {error}")
                break
            diff_file = None
            if args.save_all_diffs or not metrics["passed"]:
                diff_file = f"frame-{index:06d}-diff.png"
                save_diff(reference, candidate, args.output_dir / diff_file)
            results.append(
                {
                    "index": index,
                    "reference_time_ms": reference_entry.get("time_ms"),
                    "candidate_time_ms": candidate_entry.get("time_ms"),
                    **metrics,
                    "diff": diff_file,
                }
            )
    passed = not errors and len(results) == len(reference_frames) and all(item["passed"] for item in results)
    report = {
        "passed": passed,
        "threshold": args.threshold,
        "comparison_rule": "every frame mean_absolute_channel_difference < threshold",
        "reference_frame_count": len(reference_frames),
        "candidate_frame_count": len(candidate_frames),
        "compared_frame_count": len(results),
        "errors": errors,
        "frames": results,
    }
    write_json(args.output_dir / "frame-audit.json", report)
    print(f"{'PASS' if passed else 'FAIL'} compared={len(results)} reference={len(reference_frames)} candidate={len(candidate_frames)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

