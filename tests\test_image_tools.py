from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def run_script(name: str, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
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


class ImageToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_reference(self, name: str = "reference.png") -> Path:
        array = np.zeros((8, 10, 3), dtype=np.uint8)
        array[:, :] = (16, 48, 96)
        array[2:7, 3:8] = (220, 52, 64)
        path = self.root / name
        Image.fromarray(array, "RGB").save(path)
        return path

    def test_analyze_reference_records_source_facts(self) -> None:
        source = self.make_reference()
        output = self.root / "REFERENCE_BASELINE.json"
        run_script("analyze_reference.py", "--input", source, "--output", output)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["source"]["width"], 10)
        self.assertEqual(report["source"]["height"], 8)
        self.assertEqual(report["source"]["kind"], "static_image")
        self.assertEqual(len(report["source"]["sha256"]), 64)
        self.assertGreaterEqual(len(report["palette"]), 2)

    def test_extract_and_validate_true_alpha_preserves_source_rgb(self) -> None:
        source = self.make_reference()
        mask = Image.new("L", (5, 5), 0)
        pixels = np.array(mask)
        pixels[1:4, 1:4] = 255
        mask_path = self.root / "mask.png"
        Image.fromarray(pixels, "L").save(mask_path)
        spec = self.root / "asset-spec.json"
        spec.write_text(
            json.dumps(
                {
                    "assets": [
                        {
                            "name": "subject.png",
                            "box": [3, 2, 8, 7],
                            "alpha": {"method": "mask", "path": str(mask_path)},
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        assets = self.root / "assets"
        qa = self.root / "qa"
        manifest = self.root / "ASSET_LEDGER.json"
        run_script(
            "extract_alpha_assets.py",
            "--reference",
            source,
            "--spec",
            spec,
            "--output-dir",
            assets,
            "--qa-dir",
            qa,
            "--manifest",
            manifest,
        )
        output = Image.open(assets / "subject.png")
        self.assertEqual(output.mode, "RGBA")
        self.assertEqual(output.getchannel("A").getextrema(), (0, 255))
        report_path = self.root / "alpha-audit.json"
        run_script(
            "validate_alpha_assets.py",
            "--reference",
            source,
            "--manifest",
            manifest,
            "--asset-dir",
            assets,
            "--qa-dir",
            qa,
            "--output",
            report_path,
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        self.assertEqual(report["assets"][0]["rgb_mismatch_count"], 0)
        self.assertEqual(report["assets"][0]["corners"], [0, 0, 0, 0])
        self.assertTrue((qa / "assets-on-white.png").is_file())
        self.assertTrue((qa / "assets-on-navy.png").is_file())

    def test_alpha_extraction_removes_tiny_disconnected_artifacts(self) -> None:
        array = np.zeros((20, 20, 3), dtype=np.uint8)
        array[:, :] = (0, 255, 0)
        array[7:13, 7:13] = (240, 40, 30)
        array[3, 16] = (20, 40, 230)
        source = self.root / "artifact-source.png"
        Image.fromarray(array, "RGB").save(source)
        spec = self.root / "artifact-spec.json"
        spec.write_text(
            json.dumps(
                {
                    "assets": [
                        {
                            "name": "clean.png",
                            "box": [0, 0, 20, 20],
                            "alpha": {
                                "method": "chroma",
                                "color": [0, 255, 0],
                                "tolerance": 8,
                                "softness": 1,
                                "remove_components_below": 4,
                                "clear_border": True,
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        assets = self.root / "clean-assets"
        run_script(
            "extract_alpha_assets.py",
            "--reference",
            source,
            "--spec",
            spec,
            "--output-dir",
            assets,
            "--qa-dir",
            self.root / "clean-qa",
            "--manifest",
            self.root / "clean-manifest.json",
        )
        alpha = np.asarray(Image.open(assets / "clean.png").getchannel("A"))
        self.assertEqual(int(alpha[3, 16]), 0)
        self.assertEqual(int(alpha[9, 9]), 255)

    def test_extract_reference_frames_keeps_every_gif_frame(self) -> None:
        frames = [
            Image.new("RGB", (6, 4), (255, 0, 0)),
            Image.new("RGB", (6, 4), (0, 0, 255)),
        ]
        source = self.root / "motion.gif"
        frames[0].save(source, save_all=True, append_images=frames[1:], duration=[80, 120], loop=0)
        output_dir = self.root / "frames"
        run_script("extract_reference_frames.py", "--input", source, "--output-dir", output_dir)
        manifest = json.loads((output_dir / "frames.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["declared_frame_count"], 2)
        self.assertEqual(manifest["decoded_frame_count"], 2)
        self.assertEqual([frame["duration_ms"] for frame in manifest["frames"]], [80, 120])

    def test_visual_and_frame_audits_compare_every_registered_item(self) -> None:
        reference = self.make_reference("reference.png")
        candidate = self.root / "candidate.png"
        Image.open(reference).save(candidate)
        audit_map = self.root / "AUDIT_MAP.json"
        audit_map.write_text(
            json.dumps(
                {
                    "threshold": 2,
                    "regions": [{"id": "hero", "box": [0, 0, 10, 5]}],
                    "elements": [{"id": "subject", "box": [3, 2, 8, 7]}],
                }
            ),
            encoding="utf-8",
        )
        audit_dir = self.root / "visual-audit"
        run_script(
            "run_visual_audits.py",
            "--reference",
            reference,
            "--candidate",
            candidate,
            "--map",
            audit_map,
            "--output-dir",
            audit_dir,
        )
        report = json.loads((audit_dir / "visual-audit.json").read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        self.assertEqual(report["full_image"]["mean_absolute_channel_difference"], 0.0)
        self.assertEqual(len(report["regions"]), 1)
        self.assertEqual(len(report["elements"]), 1)

        reference_frames = self.root / "reference-frames"
        candidate_frames = self.root / "candidate-frames"
        for directory in (reference_frames, candidate_frames):
            directory.mkdir()
            for index, color in enumerate(((255, 0, 0), (0, 0, 255))):
                Image.new("RGB", (6, 4), color).save(directory / f"frame-{index:06d}.png")
            (directory / "frames.json").write_text(
                json.dumps(
                    {
                        "declared_frame_count": 2,
                        "decoded_frame_count": 2,
                        "frames": [
                            {"index": 0, "time_ms": 0, "file": "frame-000000.png"},
                            {"index": 1, "time_ms": 80, "file": "frame-000001.png"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
        frame_audit = self.root / "frame-audit"
        run_script(
            "compare_frame_sequence.py",
            "--reference-manifest",
            reference_frames / "frames.json",
            "--candidate-manifest",
            candidate_frames / "frames.json",
            "--output-dir",
            frame_audit,
        )
        frame_report = json.loads((frame_audit / "frame-audit.json").read_text(encoding="utf-8"))
        self.assertTrue(frame_report["passed"])
        self.assertEqual(frame_report["compared_frame_count"], 2)
        self.assertEqual(len(frame_report["frames"]), 2)

    def test_delivery_gate_rejects_any_failed_report(self) -> None:
        reports = self.root / "reports"
        reports.mkdir()
        for name, passed in (
            ("visual-audit.json", True),
            ("alpha-audit.json", True),
            ("interaction-audit.json", False),
        ):
            (reports / name).write_text(json.dumps({"passed": passed}), encoding="utf-8")
        output = self.root / "DELIVERY_REPORT.json"
        run_script(
            "validate_delivery.py",
            "--report",
            reports / "visual-audit.json",
            "--report",
            reports / "alpha-audit.json",
            "--report",
            reports / "interaction-audit.json",
            "--output",
            output,
            expected=1,
        )
        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertFalse(result["passed"])
        self.assertIn("interaction-audit.json", result["failed_reports"])

    def test_delivery_gate_aggregates_p0_and_p1_from_child_reports(self) -> None:
        reachability = self.root / "content-reachability.json"
        reachability.write_text(
            json.dumps({"passed": False, "p0_count": 1, "p1_count": 2}),
            encoding="utf-8",
        )
        output = self.root / "DELIVERY_REPORT.json"
        run_script(
            "validate_delivery.py",
            "--report",
            reachability,
            "--output",
            output,
            expected=1,
        )
        result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["p0_count"], 1)
        self.assertEqual(result["p1_count"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
