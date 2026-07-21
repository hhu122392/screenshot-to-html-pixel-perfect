from __future__ import annotations

import argparse
from pathlib import Path

from _image_common import read_json, write_json


LAYER_KINDS = {"dom", "svg", "raster", "effect"}
CONTOUR_ROLES = {"none", "member", "backing"}
COMPOSITING_CLASSES = {"opaque", "true_alpha", "recoverable", "source_composited", "non_identifiable"}
CONTOUR_PRIMITIVES = {"fill", "stroke", "outer_ring", "shadow"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate layer topology, compositing evidence, audit regions, and feedback coverage before implementation.")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--audit-map", required=True, type=Path)
    parser.add_argument("--iteration-ledger", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    model = read_json(args.model)
    audit_map = read_json(args.audit_map)
    ledger = read_json(args.iteration_ledger) if args.iteration_ledger else None
    failures: list[str] = []

    if int(model.get("version", 0) or 0) < 1:
        failures.append("model:version")
    layers = model.get("layers")
    contours = model.get("contours")
    limitations = model.get("evidence_limitations")
    if not isinstance(layers, list) or not layers:
        failures.append("model:layers")
        layers = []
    if not isinstance(contours, list) or not contours:
        failures.append("model:contours")
        contours = []
    if not isinstance(limitations, list):
        failures.append("model:evidence_limitations")
        limitations = []

    layer_ids: set[str] = set()
    for index, layer in enumerate(layers):
        label = f"layer:{index}"
        if not isinstance(layer, dict):
            failures.append(label)
            continue
        layer_id = str(layer.get("id", "")).strip()
        if not layer_id or layer_id in layer_ids:
            failures.append(f"{label}:id")
        layer_ids.add(layer_id)
        required = {"kind", "owner", "z_order", "clip_owner", "protrudes", "outer_contour_role", "compositing"}
        for key in required:
            if key not in layer:
                failures.append(f"{label}:{key}")
        if layer.get("kind") not in LAYER_KINDS:
            failures.append(f"{label}:kind")
        if layer.get("outer_contour_role") not in CONTOUR_ROLES:
            failures.append(f"{label}:outer_contour_role")
        if layer.get("compositing") not in COMPOSITING_CLASSES:
            failures.append(f"{label}:compositing")
        if not isinstance(layer.get("protrudes"), bool):
            failures.append(f"{label}:protrudes")

    contour_ids: set[str] = set()
    for index, contour in enumerate(contours):
        label = f"contour:{index}"
        if not isinstance(contour, dict):
            failures.append(label)
            continue
        contour_id = str(contour.get("id", "")).strip()
        if not contour_id or contour_id in contour_ids:
            failures.append(f"{label}:id")
        contour_ids.add(contour_id)
        members = contour.get("members")
        if not isinstance(members, list) or not members:
            failures.append(f"{label}:members")
        else:
            for member in members:
                if member not in layer_ids:
                    failures.append(f"{label}:unknown-member:{member}")
        if contour.get("primitive") not in CONTOUR_PRIMITIVES:
            failures.append(f"{label}:primitive")
        for key in ("openings", "internal_seams_excluded"):
            if not isinstance(contour.get(key), list):
                failures.append(f"{label}:{key}")

    limitation_ids: set[str] = set()
    for index, limitation in enumerate(limitations):
        label = f"limitation:{index}"
        if not isinstance(limitation, dict):
            failures.append(label)
            continue
        limitation_id = str(limitation.get("id", "")).strip()
        if not limitation_id or limitation_id in limitation_ids:
            failures.append(f"{label}:id")
        limitation_ids.add(limitation_id)
        evidence_class = limitation.get("evidence_class")
        if evidence_class not in {"source_composited", "non_identifiable"}:
            failures.append(f"{label}:evidence_class")
        if not str(limitation.get("reason", "")).strip():
            failures.append(f"{label}:reason")
        if limitation.get("strict_pixel_claim_allowed") is not False:
            failures.append(f"{label}:strict_pixel_claim_allowed")

    if int(audit_map.get("version", 0) or 0) < 1:
        failures.append("audit-map:version")
    if not str(audit_map.get("scope_id", "")).strip():
        failures.append("audit-map:scope_id")
    audit_ids: set[str] = set()
    limited_audit_ids: set[str] = set()
    for kind in ("regions", "elements"):
        entries = audit_map.get(kind, [])
        if not isinstance(entries, list):
            failures.append(f"audit-map:{kind}")
            continue
        for index, entry in enumerate(entries):
            entry_id = str(entry.get("id", "")).strip() if isinstance(entry, dict) else ""
            if not entry_id or entry_id in audit_ids:
                failures.append(f"audit-map:{kind}:{index}:id")
            audit_ids.add(entry_id)
            if not isinstance(entry, dict) or not isinstance(entry.get("box"), list) or len(entry["box"]) != 4:
                failures.append(f"audit-map:{kind}:{index}:box")
                continue
            evidence_class = entry.get("evidence_class", "exact")
            strict_pixel_gate = entry.get("strict_pixel_gate", evidence_class == "exact")
            if evidence_class in {"source_composited", "non_identifiable"} and strict_pixel_gate is not False:
                failures.append(f"audit-map:{kind}:{index}:strict_pixel_gate")
            if evidence_class in {"source_composited", "non_identifiable"}:
                limited_audit_ids.add(entry_id)

    for entry_id in sorted(limited_audit_ids - limitation_ids):
        failures.append(f"audit-map:evidence-limitation-not-modeled:{entry_id}")

    feedback_count = 0
    if ledger is not None:
        if int(ledger.get("version", 0) or 0) < 1:
            failures.append("iteration-ledger:version")
        core_scope = ledger.get("core_scope")
        if not isinstance(core_scope, dict):
            failures.append("iteration-ledger:core_scope")
        else:
            for key in ("id", "reference_sha256", "audit_map_sha256", "scope_mask_sha256"):
                if key not in core_scope:
                    failures.append(f"iteration-ledger:core_scope:{key}")
        feedback = ledger.get("feedback_regions")
        if not isinstance(feedback, list):
            failures.append("iteration-ledger:feedback_regions")
            feedback = []
        feedback_count = len(feedback)
        for index, item in enumerate(feedback):
            region_id = str(item.get("audit_region_id", "")).strip() if isinstance(item, dict) else ""
            if not region_id or region_id not in audit_ids:
                failures.append(f"iteration-ledger:feedback:{index}:audit_region_id")
            for key in ("requirement", "evidence_class", "baseline_candidate"):
                if not isinstance(item, dict) or not str(item.get(key, "")).strip():
                    failures.append(f"iteration-ledger:feedback:{index}:{key}")
        if not isinstance(ledger.get("iterations"), list):
            failures.append("iteration-ledger:iterations")

    failures = sorted(set(failures))
    passed = not failures
    result = {
        "passed": passed,
        "layer_count": len(layers),
        "contour_count": len(contours),
        "evidence_limitation_count": len(limitations),
        "audit_region_count": len(audit_ids),
        "feedback_region_count": feedback_count,
        "failures": failures,
        "p0_count": 0,
        "p1_count": len(failures),
    }
    write_json(args.output, result)
    print(
        f"{'PASS' if passed else 'FAIL'} layers={len(layers)} contours={len(contours)} "
        f"limitations={len(limitations)} feedback={feedback_count} failures={len(failures)}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
