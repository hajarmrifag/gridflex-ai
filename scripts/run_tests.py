"""Run the existing pytest suite with isolated, CI-friendly evidence per invocation."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("python", "bdd"), default="python")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER, help="pytest arguments after --")
    args = parser.parse_args(argv)
    extra = args.pytest_args
    if extra[:1] == ["--"]:
        extra = extra[1:]
    try:
        args.report_dir.mkdir(parents=True, exist_ok=True)
        report = Path(tempfile.mkdtemp(prefix=f"{args.suite}-", dir=args.report_dir.resolve()))
    except OSError as exc:
        parser.exit(2, f"Cannot create report directory: {exc}\n")

    command = [sys.executable, "-m", "pytest"]
    if args.suite == "bdd":
        command += ["tests/test_failure_bdd.py"]
    command += [*extra, f"--junitxml={report / 'junit.xml'}"]
    env = os.environ.copy()
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    print(f"Reports: {report}", flush=True)
    # The child owns pytest state; preserve all nonzero statuses, including no tests.
    with (report / "pytest.log").open("w") as log:
        try:
            result = subprocess.run(
                command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False
            )
            code = result.returncode if result.returncode >= 0 else 128 - result.returncode
        except OSError as exc:
            log.write(f"Could not start pytest: {exc}\n")
            code = 127
        except KeyboardInterrupt:
            log.write("Test run interrupted.\n")
            code = 130
    (report / "summary.json").write_text(
        json.dumps({"command": command, "cwd": str(ROOT), "exit_code": code}, indent=2) + "\n"
    )
    print((report / "pytest.log").read_text(), end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
