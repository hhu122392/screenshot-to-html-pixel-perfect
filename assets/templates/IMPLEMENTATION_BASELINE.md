# Implementation Baseline

## Source-size stage

- Width / height:
- Scaling rule:
- Device scale factor:
- Delivery scope: `visible_frame` or `full_component`

## Layer map

List each DOM/CSS layer, isolated artwork asset, z-index, source bounding box, and interaction owner. For every repeated row, state the data source and renderer.

## DOM/raster boundary

- Live text selectors:
- Repeated collection selectors and required children:
- Maximum unapproved raster area ratio:
- Explicitly allowed large artwork selectors and reasons:

## Deterministic audit state

Record fixed time, data, locale, fonts, query parameters, scroll position, and animation clock.

## Scroll contract

- Scroll owner selector and axis:
- Fixed selectors:
- Wheel and touch paths:
- First and last required item/control:
- Expected item count and minimum scroll range:

## Asset decisions

For each asset, record source crop, Alpha method, source-RGB rule, QA evidence, and confirmation that it contains no live text or layout container.

## Prohibited shortcuts check

- Full-page screenshot background: false
- Section/card screenshot carrying UI: false
- Raster containing live text, progress, control, or state: false
- Screenshot overlay hiding missing DOM: false
- Fake checkerboard/grid transparency: false
