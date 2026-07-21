# Screenshot to HTML Pixel Perfect

[简体中文](README.zh-CN.md) | English

A Codex Skill for reconstructing screenshots, GIFs, and recordings with reusable vanilla HTML, CSS, and JavaScript. It treats source pixels and recorded behavior as evidence, then gates delivery with structure, transparency, scrolling, interaction, responsive, and frame-by-frame audits.

## What this Skill enforces

- Real DOM/CSS for containers, cards, live text, numbers, descriptions, progress, buttons, states, and repeated rows.
- Raster images only for isolated artwork that CSS cannot faithfully reproduce.
- True RGBA cutouts with source RGB preserved; checkerboards and baked backgrounds are forbidden.
- Explicit `visible_frame` versus `full_component` scope so cropped screenshots do not become invented hidden content.
- Real wheel and touch scrolling with first-item, last-item, and required-control reachability checks.
- Deterministic interaction and motion capture, including registered frame-by-frame comparison.
- Evidence-based completion: full image, regions, key elements, Alpha, interactions, console errors, P0/P1 issues, and final delivery reports.

Read [SKILL.md](SKILL.md) for the complete workflow and hard gates.

## Audited case study

### Sign-in reward popup

This runnable vanilla HTML/CSS/JS example demonstrates the full feedback loop behind the layer-topology and compositing gates: a translucent rim around a combined silhouette, a protruding calendar, preserved concave openings, and distinct rare/grand-prize badges.

| Original screenshot | Implemented with this Skill |
|---|---|
| <img src="examples/sign-in-popup/demo/reference-full.png" alt="Original sign-in popup screenshot" width="390"> | <img src="examples/sign-in-popup/demo/mobile-preview.png" alt="Sign-in popup implemented with this Skill" width="390"> |

The left column keeps the complete source screenshot as evidence. The right column implements only the popup on a neutral gray stage.

- [Open the case and local demo instructions](examples/sign-in-popup/README.md)
- Scope: `visible_frame`; the page background is excluded.
- Verified: DOM/raster boundary passed, Alpha assets 5/5, interactions 3/3, responsive viewports 3/3.
- Strict pixel status: **failed**. Scoped popup MAE is `5.458677` against the required `<2`; original fonts, vector header layers, and recoverable translucent source layers were unavailable.

The case is intentionally published with its failed strict status and comparison evidence. It shows why a screenshot reconstruction needs explicit layer topology, evidence limits, before-state captures, and target/guard region audits.

## Repository layout

- `SKILL.md` / `SKILL.zh-CN.md`: English and Chinese Skill instructions.
- `references/`: bilingual implementation and verification guidance.
- `assets/templates/`: bilingual evidence templates and machine-readable audit specifications.
- `scripts/`: reference analysis, true-alpha extraction, browser capture, structure/reachability checks, visual/frame comparison, and final delivery validation.
- `tests/`: regression tests and browser fixtures.
- `examples/`: runnable, evidence-backed reconstruction cases.
- `agents/openai.yaml`: Codex Skill interface metadata.

## Local validation

Requirements: Python 3.10+, Node.js 18+, Chromium, and Playwright.

```powershell
python -m pip install -r requirements.txt
npm install
npx playwright install chromium
python -m unittest discover -s tests -v
```

Run each script with `--help` for its exact command contract. Generated audit evidence belongs in an `evidence/` directory and is intentionally excluded from version control.

## Install as a Codex Skill

Copy this repository into the Codex global Skill directory as `screenshot-to-html-pixel-perfect`, or install the repository with the Codex Skill installer. Restart Codex after installation so the Skill catalog is refreshed.

