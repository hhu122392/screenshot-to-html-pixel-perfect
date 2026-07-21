from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from _image_common import make_contact_sheet, read_json, validate_box, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Reject fake transparency, opaque edges, and visible RGB changes in extracted assets.")
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--asset-dir", required=True, type=Path)
    parser.add_argument("--qa-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    reference = Image.open(args.reference).convert("RGB")
    reference_array = np.asarray(reference, dtype=np.uint8)
    manifest = read_json(args.manifest)
    items = manifest.get("assets", manifest.get("transparent_assets", []))
    if not items:
        raise SystemExit("FAIL manifest contains no transparent assets")
    checkerboard_used = manifest.get("checkerboard_used") is True
    results = []
    qa_items = []
    for item in items:
        name = str(item["file"])
        path = args.asset_dir / name
        errors = []
        if not path.is_file():
            results.append({"file": name, "passed": False, "errors": ["file missing"]})
            continue
        image = Image.open(path)
        if image.mode != "RGBA":
            errors.append(f"expected RGBA, got {image.mode}")
        rgba = image.convert("RGBA")
        qa_items.append((name, rgba))
        data = np.asarray(rgba, dtype=np.uint8)
        alpha = data[:, :, 3]
        alpha_range = [int(alpha.min()), int(alpha.max())]
        if alpha_range != [0, 255]:
            errors.append(f"expected Alpha range [0, 255], got {alpha_range}")
        corners = [int(alpha[0, 0]), int(alpha[0, -1]), int(alpha[-1, 0]), int(alpha[-1, -1])]
        if corners != [0, 0, 0, 0]:
            errors.append(f"opaque corner found: {corners}")
        edge = np.concatenate((alpha[0, :], alpha[-1, :], alpha[:, 0], alpha[:, -1]))
        opaque_edge_pixels = int(np.count_nonzero(edge))
        if opaque_edge_pixels:
            errors.append(f"non-transparent edge pixels: {opaque_edge_pixels}")
        box = validate_box(item["source_box"], reference.size, name)
        left, top, right, bottom = box
        source_crop = reference_array[top:bottom, left:right]
        if source_crop.shape[:2] != data.shape[:2]:
            errors.append(f"source crop size {source_crop.shape[1]}x{source_crop.shape[0]} differs from asset {rgba.size}")
            mismatch = -1
        else:
            visible = alpha > 0
            mismatch = int(np.any(data[:, :, :3] != source_crop, axis=2)[visible].sum())
            if mismatch:
                errors.append(f"visible source RGB changed at {mismatch} pixels")
        if checkerboard_used:
            errors.append("manifest declares checkerboard_used=true")
        results.append(
            {
                "file": name,
                "passed": not errors,
                "mode": image.mode,
                "alpha_range": alpha_range,
                "corners": corners,
                "opaque_edge_pixel_count": opaque_edge_pixels,
                "rgb_mismatch_count": mismatch,
                "errors": errors,
            }
        )
    make_contact_sheet(qa_items, (255, 255, 255), args.qa_dir / "assets-on-white.png")
    make_contact_sheet(qa_items, (10, 34, 75), args.qa_dir / "assets-on-navy.png")
    passed = bool(results) and all(item["passed"] for item in results) and not checkerboard_used
    report = {
        "passed": passed,
        "checkerboard_used": checkerboard_used,
        "asset_count": len(results),
        "failed_asset_count": sum(not item["passed"] for item in results),
        "assets": results,
        "qa": {
            "white": str((args.qa_dir / "assets-on-white.png").resolve()),
            "navy": str((args.qa_dir / "assets-on-navy.png").resolve()),
        },
    }
    write_json(args.output, report)
    print(f"{'PASS' if passed else 'FAIL'} assets={len(results)} failed={report['failed_asset_count']} checkerboard_used={checkerboard_used}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

