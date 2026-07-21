# Verification and delivery gates

## Evidence order

Verify in this order: source facts, reference coverage, DOM/raster boundary, asset integrity, content reachability, browser runtime, full image, regions, elements, interactions, responsive cases, frames, final delivery. A later pass never cancels an earlier failure. In particular, a pixel pass never cancels a coverage, structure, or reachability failure.

## Reference coverage

Run `validate_reference_coverage.py` against `REFERENCE_COVERAGE.json`. `full_component` fails for any partial/unknown continuation, unresolved required unknown, or clipped asset proposed as reusable. `visible_frame` may retain declared partial evidence but must report `full_component_evidence_complete: false` and may not claim a complete component.

## DOM/raster boundary

Run `validate_implementation_structure.cjs` against `STRUCTURE_AUDIT.json`. Every registered live label must be visibly painted in a non-image DOM element with non-zero element opacity and color Alpha. Use `visibility: fully-visible` for static visible content and `visibility: dom` for items whose reachability is audited separately. Every repeated collection must have the expected item count and real title/description/control children. Reject ancestor-clipped static content, raster overlap with registered live text unless explicitly allowlisted, unapproved large rasters, and any page, section, card, label, description, progress, or state carried by a screenshot slice.

## Content reachability

Run `validate_content_reachability.cjs` against `CONTENT_REACHABILITY.json`. For every registered wheel and touch viewport, require an explicit scroll style, positive scroll range, real input movement, a fully visible first item before scrolling, a fully visible last item after scrolling, required children on every row, stable fixed layers, and zero browser errors. Treat any unreachable required row or control as P0.

## Pixel formula

For equally sized RGB images, calculate the mean of `abs(reference - candidate)` across every pixel and channel. Pass only when the mean is strictly less than `2`. Also record maximum channel difference and changed-pixel count.

## Audit map

Register every major section and every identity-bearing, actionable, or high-contrast element. Boxes use source coordinates `[left, top, right, bottom]` and must remain within source bounds.

## Interaction proof

Record scenario name, viewport, starting URL/state, steps, assertions, screenshots, console errors, and page errors. Test the actual hit target, not a manual state edit. Use `wheel`, `swipe`, `scrollSelector`, `scrollTop`, and `fullyVisible` to prove scroll paths and last-action reachability; programmatic scrolling may position deterministic audit frames but cannot replace wheel/touch proof.

## Final report

Run `validate_delivery.py` over every required report, including reference coverage and content reachability when applicable. Set `passed: false` for a missing report, failed report, P0/P1 issue, unsupported full-component claim, unreachable content, dropped frame, fake transparency, or unhandled browser error.

Report exact metrics and unrun checks. Never substitute “visually similar,” “close enough,” or an unmeasured screenshot montage for evidence.
