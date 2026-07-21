# Sign-in reward popup audit case

English | [简体中文](README.zh-CN.md)

This example reconstructs only the sign-in popup; the page behind it is excluded. It uses vanilla HTML, CSS, and JavaScript. Cards, labels, badges, buttons, checks, and the close control are real DOM. Raster files contain only isolated calendar and reward artwork.

> Audit result: structure, Alpha assets, interactions, and responsive checks passed. The strict pixel gate did not pass: scoped popup MAE is `5.458677`, above the required `<2`. This is an audited implementation and postmortem, not a strict 1:1 completion claim.

| Original screenshot | Implemented with this Skill |
|---|---|
| <img src="demo/reference-full.png" alt="Original sign-in popup screenshot" width="390"> | <img src="demo/mobile-preview.png" alt="Sign-in popup implemented with this Skill" width="390"> |

The left column keeps the complete source screenshot as evidence. The right column implements only the popup on a neutral gray stage.

## Run locally

From this directory:

```powershell
python -m http.server 4198 --bind 127.0.0.1
```

Open:

- Responsive demo: `http://127.0.0.1:4198/`
- 1179×2556 audit view: `http://127.0.0.1:4198/?audit=1`

## Implemented behavior

- Data-driven rendering for all seven reward cards.
- Signed day 1, selected day 2 with a rare badge, and a two-column grand-prize card on day 7.
- Claim button, reminder toggle, and close button.
- Close by click or Escape, plus reminder-state toggling.
- Complete layout at 360×780, 390×846, and 430×932.

## Reference, candidate, and diff

The image below shows the source crop, current implementation, and pixel diff. The diff intentionally exposes the remaining font, rim, and badge-edge errors.

![Reference, candidate, and diff](demo/comparison.png)

## What the postmortem changed

1. The rim belongs to the union of the yellow header, green surface, protruding calendar, and white dialog body—not to one rectangular box.
2. Protruding artwork must participate in the outer contour, or its rim disappears.
3. Concave openings and internal seams must be modeled separately; hard triangles create visible cuts.
4. The rare badge and grand-prize flag require different geometry.
5. User-marked regions must be registered before editing, with unmarked areas acting as regression guards.
6. A single flattened screenshot cannot uniquely recover translucent foreground RGB and Alpha over an excluded background.

## Audit results

| Check | Result | Evidence |
|---|---:|---|
| DOM/raster boundary | Pass | Seven cards and all labels are live DOM |
| Alpha assets | 5/5 pass | Zero source-RGB mismatches |
| Interactions | 3/3 pass | Click close, Escape, reminder toggle; zero browser errors |
| Responsive | 3/3 pass | 360, 390, and 430 px widths |
| Strict pixels | Fail | Scoped popup MAE `5.458677`; required `<2` |

See [`audit/AUDIT_STATUS.json`](audit/AUDIT_STATUS.json) for the machine-readable result and [`audit/VISUAL_MODEL.json`](audit/VISUAL_MODEL.json) for layer and contour ownership.

Run the core checks from the repository root:

```powershell
python scripts/validate_reference_coverage.py --spec examples/sign-in-popup/audit/REFERENCE_COVERAGE.json --output examples/sign-in-popup/evidence/reference-coverage.json
python scripts/validate_visual_model.py --model examples/sign-in-popup/audit/VISUAL_MODEL.json --audit-map examples/sign-in-popup/audit/AUDIT_MAP.json --iteration-ledger examples/sign-in-popup/audit/ITERATION_LEDGER.json --output examples/sign-in-popup/evidence/visual-model.json
node scripts/validate_implementation_structure.cjs --spec examples/sign-in-popup/audit/STRUCTURE_AUDIT.json --output-dir examples/sign-in-popup/evidence/structure
node scripts/run_interaction_scenarios.cjs --spec examples/sign-in-popup/audit/INTERACTION_SCENARIOS.json --output-dir examples/sign-in-popup/evidence/interactions
node examples/sign-in-popup/tools/responsive_audit.cjs
node scripts/capture_transparency_matrix.cjs --url http://127.0.0.1:4198 --output-dir examples/sign-in-popup/evidence/transparency --background-selector .stage --component-selector .popup-shell
```

## Evidence boundary

- Delivery scope is `visible_frame`; only the visible open state is source-proven.
- Closed, claimed, and reminder-off visuals are unknown.
- Original fonts, vector header layers, and transparent dialog exports are unavailable.
- Translucent rim regions are `non_identifiable`, so strict delivery remains failed.

## Layout

- `index.html`, `styles.css`, `app.js`: runnable implementation.
- `assets/`: isolated artwork and Noto Sans SC fonts.
- `demo/`: reference, mobile demo, before-state baseline, and comparison.
- `audit/`: scope, regions, layer topology, interactions, and status.
- `tools/`: case-specific responsive audit script.
