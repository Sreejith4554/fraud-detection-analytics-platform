import pytest

from scripts.ci_verify import verify_report


def test_gate_accepts_completed_tests(tmp_path):
    report = tmp_path / "report.xml"
    report.write_text(
        '<testsuites><testsuite><testcase name="a"/><testcase name="b"/></testsuite></testsuites>'
    )
    assert verify_report(report) == 2


@pytest.mark.parametrize("child", ["skipped", "failure", "error"])
def test_gate_rejects_skips_and_failures(tmp_path, child):
    report = tmp_path / "report.xml"
    report.write_text(
        f'<testsuites><testsuite><testcase name="blocked"><{child}/></testcase></testsuite></testsuites>'
    )
    with pytest.raises(ValueError, match="Skipped or failing"):
        verify_report(report)


def test_gate_rejects_empty_run(tmp_path):
    report = tmp_path / "report.xml"
    report.write_text("<testsuites/>")
    with pytest.raises(ValueError, match="No test cases"):
        verify_report(report)
