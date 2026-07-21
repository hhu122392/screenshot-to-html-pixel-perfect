# Visual analysis contract

## Required dimensions

Record evidence for every item before implementation:

1. Subject content: people, objects, copy, hierarchy, and state.
2. Art style: illustration, photography, 3D, brush lettering, UI language, and edge treatment.
3. Color system: dominant colors, accent colors, gradients, transparency, and contrast roles.
4. Lighting: source direction, bloom, rim light, cast shadow, reflection, and atmospheric haze.
5. Composition: source dimensions, sections, alignment axes, margins, overlap, and fixed overlays.
6. Material: glass, plastic, metal, paper, fabric, cloud, grain, and blur behavior.
7. Typography: exact copy, font evidence, size, weight, line height, tracking, and rasterized art text.
8. Detail: icons, particles, texture, antialiasing, border radii, strokes, and one-pixel edges.
9. Behavior: hit targets, scroll ownership, state transitions, countdowns, and navigation.

## Evidence files

Create the bilingual `REFERENCE_VISUAL_TEARDOWN` pair and populate `REFERENCE_BASELINE.json`, `REFERENCE_COVERAGE.json`, and `VISUAL_MODEL.json`. Define source-space bounding boxes in `AUDIT_MAP.json`; do not estimate CSS dimensions from a scaled screenshot.

Before code, model layer owners, z-order, clip owners, protrusions, outer-contour members, openings, and internal seams. A visible line is not enough evidence to choose `fill`, `stroke`, `outer_ring`, or `shadow`; record the source-proven primitive and the contour members it applies to.

## Coverage and unknowns

Choose exactly one delivery scope before implementation:

- `visible_frame`: reproduce only source-proven pixels and behavior. Keep cropped continuations, hidden content, and missing states declared as unknown; do not present them as implemented truth.
- `full_component`: require source evidence for the complete component, including every scroll position, repeated row, control, state, and asset. Any partial/unknown continuation blocks implementation and delivery.

Register each list, card, panel, or asset cut by a screenshot edge in `REFERENCE_COVERAGE.json`. A clipped fragment may be used only as a `visible-fragment` in a `visible_frame` delivery; it is never a complete reusable asset.

## Layer choice

Use DOM/CSS for containers, cards, repeated rows, live text, numbers, descriptions, progress, badges, controls, states, and behavior. A source-derived raster asset may contain only isolated artwork, identity, texture, or explicitly non-live custom lettering that cannot be reproduced without pixel drift. It must not include its card background, label, description, control, or surrounding layout. Never choose a full-page, section, or card image as the implementation.

Before implementation, write a `STRUCTURE_AUDIT.json` that registers every live text selector, every repeated collection and its required child selectors, and the raster area policy. A pixel pass does not excuse a failed DOM/raster boundary.

For scrollable content, also write `CONTENT_REACHABILITY.json`. Record the scroll owner, axis, expected item count, required children, fixed layers, minimum scroll range, and separate wheel/touch viewports. A decorative indicator is not evidence of scrolling.

## Baseline freeze

Freeze dynamic values, fonts, locale, device scale factor, scroll position, animation time, reference hash, audit-map hash, scope-mask hash, and relevant asset hashes. Record every freeze control in the implementation baseline and `ITERATION_LEDGER.json`.

Whenever the user marks a discrepancy, register its source-space box and capture the before-state candidate before editing. Preserve the old core scope when adding a new audit region.
