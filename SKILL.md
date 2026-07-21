---
name: screenshot-to-html-pixel-perfect
description: Use when reconstructing web UI from screenshots, GIFs, or recordings where pixels, reusable DOM, transparency, scrolling, interactions, responsive behavior, or animation frames must be proven.
---

# Screenshot to HTML Pixel Perfect

## Core rule

Treat the reference pixels and recorded behavior as the acceptance standard. Build with vanilla HTML, CSS, and JavaScript. Never claim 1:1 completion from visual judgment alone.

Classify the delivery as `visible_frame` or `full_component` before implementation. A cropped screenshot cannot prove hidden content. Never invent below-fold copy, controls, assets, states, or layout and present them as verified reconstruction.

Keep this Skill local until the user explicitly approves global installation. Do not write to a global Skill directory during local development or review.

## Required reading

- Read [visual-analysis.md](references/visual-analysis.md) before implementation.
- Read [asset-extraction.md](references/asset-extraction.md) before cropping or removing a background.
- Read [motion-reconstruction.md](references/motion-reconstruction.md) for GIF or recording inputs.
- Read [verification-gates.md](references/verification-gates.md) before reporting completion.

## Workflow

1. Inventory every input. Run `scripts/analyze_reference.py`; run `scripts/extract_reference_frames.py` for GIFs and recordings.
2. Create bilingual visual teardown and implementation baseline documents from `assets/templates/`.
3. Create `REFERENCE_BASELINE.json`, `REFERENCE_COVERAGE.json`, `ASSET_LEDGER.json`, `STRUCTURE_AUDIT.json`, `AUDIT_MAP.json`, and `INTERACTION_SCENARIOS.json` before page code. Create `CONTENT_REACHABILITY.json` for scrollable or cropped continuations and `MOTION_TIMELINE.json` for motion work.
4. Run `validate_reference_coverage.py`. A `full_component` build fails while any continuation is partial/unknown, any required unknown is unresolved, or any clipped fragment is proposed as reusable. A `visible_frame` build may retain declared unknowns but must not claim hidden content.
5. Build a source-size stage. Containers, cards, live text, numbers, descriptions, progress bars, badges, buttons, states, and repeated rows must be real DOM/CSS. Repeated content must be data-driven when reuse is part of the request.
6. Raster assets may contain only isolated artwork that CSS cannot faithfully reproduce: identity-bearing imagery, icons, decorative illustrations, textures, or explicitly non-live artistic lettering. A raster slice must not combine an icon with its label, description, button, card background, progress state, or layout container. A screenshot-edge fragment is not a reusable asset.
7. Never use the full-page screenshot, a section screenshot, or a card screenshot to carry implementable UI. Never hide missing implementation behind a screenshot overlay.
8. Extract reusable foregrounds as true RGBA assets. Preserve source RGB and generate Alpha only. Never bake a checkerboard or grid into an image to imitate transparency.
9. Implement states and interactions in vanilla JavaScript. Make dynamic values deterministic during audit. Register real scroll owners; do not use a decorative bar to imitate scrolling.
10. For motion, expose `window.__setAuditTime(milliseconds)` and capture every registered source frame at the matching relative time.
11. Run coverage and structure audits before pixel audits. Then run content reachability, browser, interaction, full-image, region, element, Alpha, responsive, and frame audits. Test wheel and touch paths separately. Iterate until all hard gates pass.
12. Run `scripts/validate_delivery.py` with every required report. When any check fails, set `passed: false` and report the evidence; do not call the work complete.

## Hard gates

- Full-image mean absolute channel difference: `< 2`.
- Every registered region: `< 2`.
- Every key element: `< 2`.
- Every audited motion frame: `< 2`.
- P0 issues: `0`; P1 issues: `0`.
- Every interaction assertion passes; no unhandled browser console or page error remains.
- `full_component` evidence is complete; no continuation or required field remains partial, unknown, inferred, or unsupported.
- Every static registered label is fully visible and unclipped. Every scrollable row and required control becomes fully visible through its registered wheel and touch path.
- The first and last required list items are reachable; real input changes the registered scroll owner; fixed content does not move with the list.
- No raster overlaps a registered live-text box unless the structure spec explicitly allows and justifies that selector.
- No raster asset combines reusable UI structure with live text or state.
- No wrong identity, wrong asset, missing module, full-page/section/card screenshot background, or fake transparency exists.
- No clipped screenshot-edge fragment is presented as a complete reusable asset.

These are strict less-than gates. A value equal to `2` fails.

## Quick reference

| Need | Tool or artifact |
|---|---|
| Source facts and palette | `analyze_reference.py` |
| Visible-frame vs full-component evidence | `validate_reference_coverage.py` |
| All GIF/video frames | `extract_reference_frames.py` |
| Source-RGB Alpha assets | `extract_alpha_assets.py` |
| Transparent edge and RGB audit | `validate_alpha_assets.py` |
| DOM/raster implementation boundary | `validate_implementation_structure.cjs` |
| Wheel/touch and last-item reachability | `validate_content_reachability.cjs` |
| Full/region/element diff | `run_visual_audits.py` |
| Every-frame diff | `compare_frame_sequence.py` |
| Browser screenshot | `capture_preview.cjs` |
| Interaction simulation | `run_interaction_scenarios.cjs` |
| Deterministic motion capture | `capture_interaction_frames.cjs` |
| Final hard gate | `validate_delivery.py` |

Run each script with `--help` for its exact command contract.

## Common failures

| Failure | Required correction |
|---|---|
| “Looks close” but no diff report | Capture at source size and generate pixel evidence. |
| Layout flow is right but artwork is wrong | Rebuild the asset ledger and use isolated source-derived artwork assets. |
| Cutout has a white, green, or grid halo | Repair the Alpha mask; keep source RGB; rerun white/navy QA. |
| Candidate skips motion frames | Fix capture timing or the audit clock; never reduce the source frame list. |
| Screenshot carries a page, section, card, label, or description | Rebuild containers and content in DOM/CSS; keep only isolated artwork as raster assets. |
| Pixel audit passes but task rows are images | Mark the result failed, add live-text/collection selectors to `STRUCTURE_AUDIT.json`, and rebuild the rows as DOM. |
| Screenshot ends inside a list/card/asset | Mark the continuation partial in `REFERENCE_COVERAGE.json`; do not invent hidden content or call it `full_component`. |
| Last row exists in DOM but touch cannot reach it | Register the real scroll owner in `CONTENT_REACHABILITY.json`, fix overflow/touch behavior, and rerun wheel and touch cases. |
| A gray bar looks like a scrollbar but is not linked to scroll state | Treat it as decoration until real scroll ownership and input evidence pass. |
| Lossy recording cannot pass `< 2` with recreated DOM | Report the failed frame evidence. Do not silently relax the threshold. |

## Minimal command sequence

```powershell
python scripts/analyze_reference.py --input reference.png --output REFERENCE_BASELINE.json
python scripts/validate_reference_coverage.py --spec REFERENCE_COVERAGE.json --output evidence/reference-coverage.json
node scripts/validate_implementation_structure.cjs --spec STRUCTURE_AUDIT.json --output-dir evidence/structure-audit
node scripts/validate_content_reachability.cjs --spec CONTENT_REACHABILITY.json --output-dir evidence/content-reachability
python scripts/run_visual_audits.py --reference reference.png --candidate evidence/page.png --map AUDIT_MAP.json --output-dir evidence/visual-audit
python scripts/validate_delivery.py --report evidence/reference-coverage.json --report evidence/structure-audit/structure-audit.json --report evidence/content-reachability/content-reachability.json --report evidence/visual-audit/visual-audit.json --report evidence/interaction-audit.json --output DELIVERY_REPORT.json
```

## Completion statement

Report the delivery scope, unresolved evidence count, scroll contracts and methods, reachable item/control totals, source dimensions, compared frame count, full/region/element maxima, interaction totals, Alpha failures, P0/P1 totals, exact commands, and exit codes. State unrun checks plainly. Global installation still requires explicit user approval after local review.
