# Verification and delivery gates

## Evidence order

Verify in this order: source facts, evidence sufficiency, reference coverage, layer topology, DOM/raster boundary, asset integrity, content reachability, browser runtime, full image, regions, elements, iteration deltas, transparency matrix, interactions, responsive cases, frames, final delivery. A later pass never cancels an earlier failure. In particular, a pixel pass never cancels a coverage, topology, structure, or reachability failure.

## Evidence sufficiency and topology

Run `validate_visual_model.py` before implementation. Every protruding layer, clip owner, outer-contour member, opening, and excluded internal seam must be explicit. A `source_composited` or `non_identifiable` region must set `strict_pixel_gate: false` in the audit map and must block a strict 1:1 delivery. Multi-background captures prove candidate transparency behavior but do not recover unknown source Alpha.

## Reference coverage

Run `validate_reference_coverage.py` against `REFERENCE_COVERAGE.json`. `full_component` fails for any partial/unknown continuation, unresolved required unknown, or clipped asset proposed as reusable. `visible_frame` may retain declared partial evidence but must report `full_component_evidence_complete: false` and may not claim a complete component.

## DOM/raster boundary

Run `validate_implementation_structure.cjs` against `STRUCTURE_AUDIT.json`. Every registered live label must be visibly painted in a non-image DOM element with non-zero element opacity and color Alpha. Use `visibility: fully-visible` for static visible content and `visibility: dom` for items whose reachability is audited separately. Every repeated collection must have the expected item count and real title/description/control children. Reject ancestor-clipped static content, raster overlap with registered live text unless explicitly allowlisted, unapproved large rasters, and any page, section, card, label, description, progress, or state carried by a screenshot slice.

## Content reachability

Run `validate_content_reachability.cjs` against `CONTENT_REACHABILITY.json`. For every registered wheel and touch viewport, require an explicit scroll style, positive scroll range, real input movement, a fully visible first item before scrolling, a fully visible last item after scrolling, required children on every row, stable fixed layers, and zero browser errors. Treat any unreachable required row or control as P0.

## Pixel formula

For equally sized RGB images, calculate the mean of `abs(reference - candidate)` across every pixel and channel. Pass only when the mean is strictly less than `2`. Also record maximum channel difference and changed-pixel count.

## Audit map

Register every major section and every identity-bearing, actionable, high-contrast, user-marked, protruding, or contour-connection region. Boxes use source coordinates `[left, top, right, bottom]` and must remain within source bounds. Freeze `version`, `scope_id`, and the audit-map hash. When scope expands, preserve a comparable core-scope report.

## Iteration proof

For a correction pass, capture the current implementation before editing and run `run_visual_audits.py --baseline-candidate`. Target regions must improve or already pass. Guard regions must stay within their declared regression budget. Reference, candidate dimensions, audit map, scope mask, fonts, assets, and viewport must stay frozen; otherwise report a new scope instead of a trend.

## Interaction proof

Record scenario name, viewport, starting URL/state, steps, assertions, screenshots, console errors, and page errors. Test the actual hit target, not a manual state edit. Use `wheel`, `swipe`, `scrollSelector`, `scrollTop`, and `fullyVisible` to prove scroll paths and last-action reachability; programmatic scrolling may position deterministic audit frames but cannot replace wheel/touch proof.

## Final report

Run `validate_delivery.py` over every required report, including reference coverage and content reachability when applicable. Set `passed: false` for a missing report, failed report, P0/P1 issue, unsupported full-component claim, unreachable content, dropped frame, fake transparency, or unhandled browser error.

Report exact metrics, signed iteration deltas, scope hashes, evidence-limited regions, and unrun checks. Never substitute “visually similar,” “close enough,” or an unmeasured screenshot montage for evidence. Stop tuning and report the limitation when the available evidence cannot distinguish a unique correct result.
