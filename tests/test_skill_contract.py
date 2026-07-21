from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_bilingual_skill_requires_coverage_and_reachability_gates(self) -> None:
        english = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        chinese = (SKILL / "SKILL.zh-CN.md").read_text(encoding="utf-8")
        for text in (english, chinese):
            self.assertIn("REFERENCE_COVERAGE.json", text)
            self.assertIn("CONTENT_REACHABILITY.json", text)
            self.assertIn("validate_reference_coverage.py", text)
            self.assertIn("validate_content_reachability.cjs", text)
            self.assertIn("full_component", text)
            self.assertIn("visible_frame", text)

    def test_required_bilingual_references_cover_unknowns_clipping_and_scroll_ownership(self) -> None:
        files = [
            SKILL / "references" / "visual-analysis.md",
            SKILL / "references" / "visual-analysis.zh-CN.md",
            SKILL / "references" / "verification-gates.md",
            SKILL / "references" / "verification-gates.zh-CN.md",
        ]
        terms = ["REFERENCE_COVERAGE.json", "CONTENT_REACHABILITY.json", "full_component", "visible_frame"]
        for path in files:
            text = path.read_text(encoding="utf-8")
            for term in terms:
                self.assertIn(term, text, f"{path.name} missing {term}")

    def test_new_templates_expose_auditable_contracts(self) -> None:
        coverage = json.loads((SKILL / "assets" / "templates" / "REFERENCE_COVERAGE.json").read_text(encoding="utf-8"))
        reachability = json.loads((SKILL / "assets" / "templates" / "CONTENT_REACHABILITY.json").read_text(encoding="utf-8"))
        interactions = json.loads((SKILL / "assets" / "templates" / "INTERACTION_SCENARIOS.json").read_text(encoding="utf-8"))
        structure = json.loads((SKILL / "assets" / "templates" / "STRUCTURE_AUDIT.json").read_text(encoding="utf-8"))
        self.assertIn(coverage["delivery_scope"], {"visible_frame", "full_component"})
        self.assertTrue(coverage["continuations"])
        self.assertGreaterEqual(len(reachability["viewports"]), 2)
        self.assertEqual({item["method"] for item in reachability["viewports"]}, {"wheel", "touch"})
        self.assertTrue(reachability["contracts"][0]["required_children"])
        actions = {step["action"] for scenario in interactions["scenarios"] for step in scenario["steps"]}
        assertions = {item["type"] for scenario in interactions["scenarios"] for item in scenario["assertions"]}
        self.assertIn("swipe", actions)
        self.assertIn("scrollSelector", actions)
        self.assertIn("fullyVisible", assertions)
        self.assertEqual(structure["live_text"][0]["visibility"], "fully-visible")
        self.assertEqual(structure["collections"][0]["visibility"], "dom")


if __name__ == "__main__":
    unittest.main(verbosity=2)
