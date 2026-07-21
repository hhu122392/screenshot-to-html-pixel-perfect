# Layer topology and compositing

Read this reference before implementation when the target contains overlapping layers, protruding artwork, translucent rims, shadows, blur, cutouts, concave outlines, or an excluded background that still affects the component pixels.

## Evidence sufficiency

Classify every translucent or background-dependent region:

- `recoverable`: the source provides the foreground, Alpha, background, or enough independent observations to reconstruct them.
- `source_composited`: the screenshot already contains foreground blended with a known or visible background.
- `non_identifiable`: foreground color, Alpha, or the covered background is unknown, so one screenshot cannot determine the original layer uniquely.

For compositing `C = alpha * F + (1 - alpha) * B`, one observed `C` cannot determine unknown `F`, `alpha`, and `B`. Record this limitation before code. Do not promise a strict pixel pass for `non_identifiable` regions. Keep the delivery failed for a strict 1:1 claim until transparent source layers, design exports, or sufficient additional backgrounds are available.

Use the same limitation ID as the corresponding `AUDIT_MAP.json` region:

```json
{
  "id": "translucent-outer-rim",
  "evidence_class": "non_identifiable",
  "reason": "Foreground Alpha and the covered background are not independently known.",
  "strict_pixel_claim_allowed": false
}
```

## Required visual model

Create `VISUAL_MODEL.json` from the template before page code. Record:

- every DOM, SVG, raster, and effect layer;
- owner and z-order;
- clip owner and overflow behavior;
- whether the layer protrudes beyond its owner;
- whether it participates in the outer contour;
- compositing class;
- combined contours, openings, and internal seams that must remain unpainted.

Treat the outer contour as the union of its members. A protruding calendar, badge, tab, cloud, character, or illustration changes the component silhouette even if it visually belongs to a header.

## Primitive selection

- Use `fill` for a continuous material interior.
- Use `stroke` for a source-proven visible line.
- Use `outer_ring` for a rim around the union of several overlapping silhouette members. Build the union first, expand it, then subtract the original union.
- Use `shadow` only for a soft source-proven shadow, not as a substitute for an exact complex outline.

Never dilate overlapping members separately when their internal edges must disappear. Never fill a concave opening merely to connect two outer edges. Never use a hard rectangular clip to end a curved or translucent outline unless the source proves that cut.

## Clip and protrusion checks

For every protruding layer:

1. Compare its source-space box with the owner box.
2. Record the actual clip owner.
3. Confirm that `overflow: hidden` does not remove required pixels.
4. Place the outline outside the clipping context or include the protruding layer in the outline union.
5. Register the protrusion and its connection points in `AUDIT_MAP.json`.

## Transparency proof

Use the original composite for ordinary pixel comparison only when its background is part of the target or otherwise known. Also render the candidate on white, navy, and neutral gray backgrounds to prove that translucent DOM/SVG effects are real and do not contain a baked background. Use a tight component selector, disable animations, and pass the same audit time for every capture. These captures prove implementation integrity; they do not recover unknown source Alpha.
