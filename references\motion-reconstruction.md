# Motion reconstruction and frame audit

## Source timeline

Decode every GIF frame. For a recording, define each relevant clip with explicit start and end milliseconds, then decode every frame inside that clip. Record both declared and decoded counts; fail on unexplained loss.

## Motion ledger

For every actor, record start/end bounds, transform origin, position, scale, rotation, opacity, layer, trigger, delay, duration, easing evidence, loop rule, and terminal state in the bilingual motion timeline and `MOTION_TIMELINE.json`.

## Deterministic audit clock

Expose:

```javascript
window.__setAuditTime = (milliseconds) => {
  // Render every animated actor at this exact relative time.
};
```

The hook must update the same state used by live playback. Do not create a separate fake audit-only image.

## Frame capture and comparison

1. Extract the complete source sequence.
2. Capture candidate frames at every source timestamp with `capture_interaction_frames.cjs`.
3. Run `compare_frame_sequence.py`.
4. Require matching counts and dimensions.
5. Fix the implementation when any frame has mean absolute channel difference `>= 2`.

Record interaction anchors so the same click, touch, or scroll event starts both timelines.

