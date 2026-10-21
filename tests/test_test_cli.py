"""Exercise real child pytest processes, including failure and empty selection."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from scripts import run_tests


@pytest.mark.parametrize(
    ("source", "expected_code", "failures", "errors"),
    [
        ("def test_probe(): assert True", 0, 0, 0),
        ("def test_probe(): assert False, 'deliberate probe failure'", 1, 1, 0),
        ("raise RuntimeError('deliberate collection error')", 2, 0, 1),
        ("# no tests", 5, 0, 0),
    ],
)
def test_cli_preserves_pytest_status_and_reports_from_another_directory(
    tmp_path, source, expected_code, failures, errors
):
    probe = tmp_path / "test_probe.py"
    probe.write_text(source + "\n")
    reports = tmp_path / "reports with spaces"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(run_tests.__file__).resolve()),
            "--report-dir",
            str(reports),
            "--",
            str(probe),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    (report,) = reports.iterdir()
    assert json.loads((report / "summary.json").read_text())["exit_code"] == expected_code
    suite = ET.parse(report / "junit.xml").getroot().find("testsuite")
    assert int(suite.attrib["failures"]) == failures
    assert int(suite.attrib["errors"]) == errors
    assert (report / "pytest.log").read_text() in result.stdout


def test_cli_keeps_separate_reports_and_fails_if_pytest_cannot_start(tmp_path, monkeypatch):
    def missing_runner(*args, **kwargs):
        raise FileNotFoundError("runner unavailable")

    monkeypatch.setattr(run_tests.subprocess, "run", missing_runner)
    for _ in range(2):
        assert run_tests.main(["--report-dir", str(tmp_path)]) == 127
    reports = list(tmp_path.iterdir())
    assert len(reports) == 2
    for report in reports:
        assert "runner unavailable" in (report / "pytest.log").read_text()
        assert json.loads((report / "summary.json").read_text())["exit_code"] == 127
        assert not (report / "junit.xml").exists()


def test_cli_rejects_unwritable_report_destination(tmp_path):
    destination = tmp_path / "file"
    destination.touch()
    with pytest.raises(SystemExit) as error:
        run_tests.main(["--report-dir", str(destination / "reports")])
    assert error.value.code == 2
