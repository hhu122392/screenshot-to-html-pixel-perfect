from __future__ import annotations

import argparse
from pathlib import Path

from _image_common import read_json, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate required audit reports without relaxing any failed gate.")
    parser.add_argument("--report", action="append", type=Path, default=[])
    parser.add_argument("--require-file", action="append", type=Path, default=[])
    parser.add_argument("--p0", type=int, default=0)
    parser.add_argument("--p1", type=int, default=0)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    reports = []
    failed_reports = []
    missing_files = []
    report_p0 = 0
    report_p1 = 0
    for path in args.report:
        if not path.is_file():
            failed_reports.append(path.name)
            reports.append({"path": str(path), "passed": False, "error": "missing"})
            continue
        data = read_json(path)
        passed = data.get("passed") is True
        child_p0 = int(data.get("p0_count", 0) or 0)
        child_p1 = int(data.get("p1_count", 0) or 0)
        report_p0 += child_p0
        report_p1 += child_p1
        reports.append(
            {
                "path": str(path.resolve()),
                "passed": passed,
                "p0_count": child_p0,
                "p1_count": child_p1,
            }
        )
        if not passed:
            failed_reports.append(path.name)
    for path in args.require_file:
        if not path.is_file():
            missing_files.append(str(path))
    p0_count = args.p0 + report_p0
    p1_count = args.p1 + report_p1
    passed = not failed_reports and not missing_files and p0_count == 0 and p1_count == 0 and bool(args.report)
    result = {
        "passed": passed,
        "reports": reports,
        "failed_reports": failed_reports,
        "missing_files": missing_files,
        "p0_count": p0_count,
        "p1_count": p1_count,
        "global_install_approved": False,
    }
    write_json(args.output, result)
    print(f"{'PASS' if passed else 'FAIL'} reports={len(reports)} failed={len(failed_reports)} missing={len(missing_files)} p0={p0_count} p1={p1_count}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
