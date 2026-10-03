"""A green process exit is insufficient if integration tests were skipped."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def verify_report(path):
    root = ET.parse(path).getroot()
    cases = root.findall(".//testcase")
    if not cases:
        raise ValueError("No test cases recorded")
    for case in cases:
        if any(case.find(tag) is not None for tag in ["skipped", "failure", "error"]):
            raise ValueError("Skipped or failing test: " + case.attrib.get("name", "unknown"))
    return len(cases)


def main():
    directory = Path("reports")
    directory.mkdir(exist_ok=True)
    report = directory / "pytest.xml"
    subprocess.run([sys.executable, "-m", "pytest", "-q", f"--junitxml={report}"], check=True)
    count = verify_report(report)
    result = {"status": "PASSED", "tests": count, "skips": 0, "failures": 0}
    (directory / "test-gate.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"All {count} tests passed without skips")


if __name__ == "__main__":
    main()
