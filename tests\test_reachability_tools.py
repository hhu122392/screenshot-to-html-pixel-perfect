from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
FIXTURES = SKILL / "tests" / "fixtures"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run_python(name: str, *args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != expected:
        raise AssertionError(
            f"{name} exit={completed.returncode}, expected={expected}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def run_node(name: str, *args: object, expected: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["node", str(SCRIPTS / name), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=os.environ.copy(),
    )
    if completed.returncode != expected:
        raise AssertionError(
            f"{name} exit={completed.returncode}, expected={expected}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


class ReachabilityToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = free_port()
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(cls.port), "--bind", "127.0.0.1"],
            cwd=FIXTURES,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.terminate()
        cls.server.wait(timeout=5)

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_json(self, name: str, payload: dict) -> Path:
        path = self.root / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def test_full_component_coverage_rejects_partial_continuation_and_clipped_asset(self) -> None:
        spec = self.write_json(
            "REFERENCE_COVERAGE.json",
            {
                "delivery_scope": "full_component",
                "source_files": [{"path": "reference.png"}],
                "continuations": [{"id": "tasks", "status": "partial", "evidence": ["reference.png"]}],
                "unknowns": [{"id": "below-fold", "resolved": False}],
                "clipped_assets": [{"id": "task-6-icon", "intended_use": "reusable"}],
            },
        )
        output = self.root / "coverage-audit.json"
        run_python("validate_reference_coverage.py", "--spec", spec, "--output", output, expected=1)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertFalse(report["passed"])
        self.assertIn("continuation:tasks", report["failures"])
        self.assertIn("unknown:below-fold", report["failures"])
        self.assertIn("clipped_asset:task-6-icon", report["failures"])

    def test_visible_frame_coverage_allows_declared_partial_evidence_without_claiming_full_component(self) -> None:
        spec = self.write_json(
            "REFERENCE_COVERAGE.json",
            {
                "delivery_scope": "visible_frame",
                "source_files": [{"path": "reference.png"}],
                "continuations": [{"id": "tasks", "status": "partial", "evidence": ["reference.png"]}],
                "unknowns": [{"id": "below-fold", "resolved": False}],
                "clipped_assets": [{"id": "task-6-icon", "intended_use": "visible-fragment"}],
            },
        )
        output = self.root / "coverage-audit.json"
        run_python("validate_reference_coverage.py", "--spec", spec, "--output", output)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        self.assertFalse(report["full_component_evidence_complete"])

    def test_coverage_requires_source_inventory(self) -> None:
        spec = self.write_json(
            "REFERENCE_COVERAGE.json",
            {"delivery_scope": "visible_frame", "source_files": [], "continuations": [], "unknowns": [], "clipped_assets": []},
        )
        output = self.root / "coverage-audit.json"
        run_python("validate_reference_coverage.py", "--spec", spec, "--output", output, expected=1)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("source_files", report["failures"])

    def test_full_component_requires_evidence_for_complete_continuation(self) -> None:
        spec = self.write_json(
            "REFERENCE_COVERAGE.json",
            {
                "delivery_scope": "full_component",
                "source_files": [{"path": "reference.png"}],
                "continuations": [{"id": "tasks", "status": "complete", "evidence": []}],
                "unknowns": [],
                "clipped_assets": [],
            },
        )
        output = self.root / "coverage-audit.json"
        run_python("validate_reference_coverage.py", "--spec", spec, "--output", output, expected=1)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("continuation-evidence:tasks", report["failures"])

    def test_full_component_rejects_even_declared_visible_fragment(self) -> None:
        spec = self.write_json(
            "REFERENCE_COVERAGE.json",
            {
                "delivery_scope": "full_component",
                "source_files": [{"path": "reference.png"}],
                "continuations": [],
                "unknowns": [],
                "clipped_assets": [{"id": "cut-icon", "intended_use": "visible-fragment"}],
            },
        )
        output = self.root / "coverage-audit.json"
        run_python("validate_reference_coverage.py", "--spec", spec, "--output", output, expected=1)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertIn("clipped_asset:cut-icon", report["failures"])

    def reachability_spec(self, fixture: str) -> Path:
        return self.write_json(
            "CONTENT_REACHABILITY.json",
            {
                "url": f"http://127.0.0.1:{self.port}/{fixture}",
                "viewports": [
                    {"id": "desktop-wheel", "width": 390, "height": 640, "method": "wheel"},
                    {"id": "mobile-touch", "width": 390, "height": 640, "method": "touch", "is_mobile": True, "has_touch": True},
                ],
                "contracts": [
                    {
                        "id": "tasks",
                        "scroll_selector": ".task-scroll",
                        "item_selector": ".task-row",
                        "expected_count": 6,
                        "required_children": [".task-title", ".task-action"],
                        "fixed_selectors": [".sheet-header"],
                        "min_scroll_range": 1,
                    }
                ],
            },
        )

    def test_reachability_audit_passes_real_wheel_and_touch_scroll(self) -> None:
        spec = self.reachability_spec("scroll-pass.html")
        output_dir = self.root / "reachability-pass"
        run_node("validate_content_reachability.cjs", "--spec", spec, "--output-dir", output_dir)
        report = json.loads((output_dir / "content-reachability.json").read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["cases"]), 2)
        for case in report["cases"]:
            self.assertTrue(case["last_item_fully_visible"])
            self.assertGreater(case["scroll_after"], case["scroll_before"])

    def test_reachability_audit_rejects_hidden_overflow_and_unreachable_last_item(self) -> None:
        spec = self.reachability_spec("scroll-fail.html")
        output_dir = self.root / "reachability-fail"
        run_node("validate_content_reachability.cjs", "--spec", spec, "--output-dir", output_dir, expected=1)
        report = json.loads((output_dir / "content-reachability.json").read_text(encoding="utf-8"))
        self.assertFalse(report["passed"])
        self.assertTrue(any("last-item-unreachable" in item for item in report["failures"]))

    def test_reachability_audit_rejects_clipped_required_control_in_last_item(self) -> None:
        spec = self.reachability_spec("scroll-clipped-action.html")
        output_dir = self.root / "reachability-clipped-action"
        run_node("validate_content_reachability.cjs", "--spec", spec, "--output-dir", output_dir, expected=1)
        report = json.loads((output_dir / "content-reachability.json").read_text(encoding="utf-8"))
        self.assertFalse(report["passed"])
        self.assertTrue(any("last-required-child-unreachable" in item for item in report["failures"]))

    def test_interaction_runner_scrolls_named_container_and_clicks_last_action(self) -> None:
        spec = self.write_json(
            "INTERACTION_SCENARIOS.json",
            {
                "url": f"http://127.0.0.1:{self.port}/scroll-pass.html",
                "viewport": {"width": 390, "height": 640, "is_mobile": True, "has_touch": True},
                "scenarios": [
                    {
                        "id": "reach-and-click-last-task",
                        "steps": [
                            {"action": "swipe", "selector": ".task-scroll", "direction": "up", "distance": 420},
                            {"action": "scrollSelector", "selector": ".task-scroll", "position": "end"},
                            {"action": "click", "selector": ".task-row:last-child .task-action"},
                        ],
                        "assertions": [
                            {"type": "scrollTop", "selector": ".task-scroll", "min": 1},
                            {"type": "fullyVisible", "selector": ".task-row:last-child"},
                            {"type": "text", "selector": "#result", "value": "last-clicked"},
                        ],
                    }
                ],
            },
        )
        output_dir = self.root / "interaction"
        run_node("run_interaction_scenarios.cjs", "--spec", spec, "--output-dir", output_dir)
        report = json.loads((output_dir / "interaction-audit.json").read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])

    def test_structure_audit_rejects_text_partly_clipped_by_ancestor(self) -> None:
        spec = self.write_json(
            "STRUCTURE_AUDIT.json",
            {
                "url": f"http://127.0.0.1:{self.port}/ancestor-clipped.html",
                "viewport": {"width": 390, "height": 640},
                "live_text": [
                    {
                        "id": "partly-clipped",
                        "selector": ".partly-clipped",
                        "text": "被祖先裁剪的文字",
                        "visibility": "fully-visible",
                    }
                ],
                "collections": [],
                "raster_policy": {},
            },
        )
        output_dir = self.root / "structure"
        run_node("validate_implementation_structure.cjs", "--spec", spec, "--output-dir", output_dir, expected=1)
        report = json.loads((output_dir / "structure-audit.json").read_text(encoding="utf-8"))
        result = report["live_text"][0]
        self.assertFalse(result["passed"])
        self.assertFalse(result["presentation"]["fully_unclipped"])
        self.assertIn(".clip-owner", result["presentation"]["clipped_by"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
