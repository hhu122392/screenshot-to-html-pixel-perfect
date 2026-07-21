# Feedback-driven visual iteration

Read this reference whenever the user supplies a correction, annotated screenshot, red box, comparison crop, or asks for another visual pass.

## Register before editing

Before changing code:

1. Save the feedback image and its source dimensions.
2. Convert every marked area into a source-space region in `AUDIT_MAP.json`.
3. Record the requirement, expected direction, and evidence class in `ITERATION_LEDGER.json`.
4. Capture the current implementation at the same viewport as the baseline candidate.
5. Hash the reference, baseline candidate, audit map, scope mask, font files, and relevant assets.

Do not edit first and create the audit region afterward. A verbal note or red rectangle is not an audit until it has a registered box and before-state evidence.

## Comparable iteration

Compare before and after only when reference, dimensions, viewport, font state, audit map, and scope-mask hashes match. If the scope changes, keep the old `core_scope` report and create a separate `expanded_scope` report. Never present metrics from different scopes as one improvement trend.

Change one visual cause per iteration when possible. Record the implementation decision such as `fill`, `stroke`, `outer_ring`, Alpha asset, clip change, or typography change.

Run `run_visual_audits.py --baseline-candidate ...` to report current-vs-reference metrics together with before-vs-reference deltas. Require every target region to improve and every guard region to stay within its regression budget. A full-image improvement does not cancel a target-region regression, and a target improvement does not excuse an unrelated regression.

## Review output

For each iteration preserve:

- reference crop;
- baseline candidate crop;
- current candidate crop;
- current diff;
- baseline and current MAE;
- signed delta, where negative is improvement;
- scope and input hashes;
- target and guard regression failures.

Reject any iteration that fixes the annotated region by adding a new hard seam, filling an opening, clipping a protrusion, or changing unrelated geometry without evidence.
