# True-Alpha asset extraction

## Non-negotiable rule

Preserve source RGB. Create or repair only the Alpha mask. A model-generated replacement, approximate recolor, opaque white background, chroma background, checkerboard, or grid is not a reusable cutout.

## Procedure

1. Register a padded source-space box in `ASSET_LEDGER.json`.
2. Choose a mask source: hand mask for critical edges; model mask for a first pass; GrabCut/chroma/ellipse only when the geometry supports it.
3. Run `extract_alpha_assets.py` with an explicit spec.
4. Run `validate_alpha_assets.py` against the source and manifest.
5. Inspect white and navy composites at 100% and enlarged scale.
6. Repair hair, translucent material, holes, edge halos, and detached components; rerun validation.

## Required proof

- Mode is RGBA.
- Alpha includes both 0 and 255 for a true foreground cutout.
- Transparent corners and padded edges are actually Alpha 0.
- Every visible RGB pixel equals its source crop pixel.
- The manifest states `checkerboard_used: false`.
- White and navy QA sheets exist.

`source_composited: true` may document that the source screenshot already contains background color in translucent pixels. It does not permit replacing Alpha with an opaque background.

