# Test automation audit and quality gates

This document records the test-automation architecture, coverage and verification
evidence for GridFlex. It describes repository-level work and does not establish
validation of third-party software or production reliability. The audited
starting revision was `83d98f5`; the final architecture review also incorporated
upstream changes through `0dc7414`.

## Capabilities already present

| Area | Existing evidence | Scope and limits |
| --- | --- | --- |
| Python testing | `tests/test_battery.py`, `test_flexibility.py`, `test_optimizer.py`, `test_forecasting.py`, `test_validation.py`, `test_scenarios.py`, `test_integration.py`, `test_data.py` | Numerical invariants, seeded regressions, real infeasible LP, chronological forecasting, malformed/missing inputs and data provenance. Retained rather than rewritten as BDD. |
| API testing | `tests/test_api.py` | Real FastAPI handlers through TestClient; reproducibility, finite JSON, cached-input immutability, 413/422/503 responses, saturation and recovery. In-process tests do not establish network behavior. |
| Playwright | `frontend/tests/workspace.spec.ts` | Five existing Chromium journeys cover settings/snapshots, comparisons/replay, labs, exports and mobile navigation. No Firefox/WebKit coverage. |
| CI/CD | `.github/workflows/test.yml`, `render.yaml` | Python 3.11/3.12 matrix, lint, frontend format/build/browser checks, Docker smoke test. Render is configured to deploy after checks pass. Configuration alone does not prove branch protection, an actual deployment or remote CI success. |
| Docker | `Dockerfile`, `.dockerignore`, `requirements-api.lock` | Multi-stage build, non-root runtime, liveness health check and hashed runtime dependencies; existing CI exercises health/frontend/simulation. Base image tags and development tools are not fully pinned. |
| Reporting | `frontend/playwright.config.ts`, `benchmarks/recorded.json`, `docs/experiments.csv` | Existing failure traces and CI artifact upload; recorded research/benchmark evidence is separate from test reporting and was not remeasured here. |
| Failure handling | `api/main.py`, `src/optimizer.py`, `frontend/src/api.ts` | Bounded bodies/compute slots, release in `finally`, bounded solver time, actionable errors and explicit UI retry. Existing tests covered many invalid-input paths but not solver-failure recovery across the API or browser transport failures. |

## Focused additions

- `scripts/run_tests.py` wraps the existing pytest runner with the active Python
  interpreter and repository working directory. Each invocation gets a separate
  report directory containing `pytest.log`, `junit.xml` and `summary.json` (command,
  working directory and exit status). JUnit may be absent if pytest cannot start
  or is interrupted. Console output is printed when the child finishes; the log
  can be inspected while it runs. Existing direct pytest commands still work.
- `tests/features/optimizer_recovery.feature` and `tests/test_failure_bdd.py`
  execute three Gherkin examples with pytest-bdd: peak-solve time limit,
  peak-solve infeasibility and throughput-solve time limit. Only the solver
  outcome is injected. API handlers, exception mapping, capacity management and
  the successful retry use real application code. The throughput case performs
  the real first solve before injecting the second failure. Each case checks
  actionable 422, no internal-detail leak/partial result, both slots available,
  and a finite 168-hour result on retry. Each scenario uses a fresh two-slot
  semaphore so a release regression cannot contaminate later tests. Caches and
  patches are cleaned up.
- `frontend/tests/recovery.spec.ts` injects 503 JSON, 502 HTML and an aborted
  request. Each case checks the error, removes interception and retries against
  the real API, asserting identical request settings and no main-frame
  navigation after the error. Playwright steps make the behavior readable
  in the HTML report; no second browser/BDD framework is introduced.
- CI retains Python logs/JUnit and browser JUnit/HTML/traces on success or
  failure for seven days. Focused browser tests and flaky passes fail CI. The
  Docker smoke script now explicitly requires a successful final health check
  after its readiness loop.
- Renamed a forecast test that previously claimed infeasible-optimization
  coverage although its assertions only exercised short forecast history.

No application code, scientific assumptions, runtime dependency lockfile or
existing browser journeys were changed.

## Reproduction

Use Python 3.11 or 3.12 and Node 24 to match CI. Verify `python --version`;
an older local virtual environment is not upgraded by installing the project.
From the repository root, with a supported `.venv` activated:

```bash
python -m pip install --require-hashes -r requirements-api.lock
python -m pip install -e ".[api,dev]"
npm ci --prefix frontend

python scripts/run_tests.py -- --strict-markers
python scripts/run_tests.py --suite bdd -- --strict-markers -vv
python scripts/run_tests.py -- --strict-markers -k compute_saturation
python -m ruff check .
npm run format:check --prefix frontend
npm run build --prefix frontend
cd frontend
npx playwright install chromium
CI=1 npm test
```

The browser suite starts `../.venv/bin/uvicorn` on port 8000 and serves the
production build. Stop another server on that port before a CI-style run;
ordinary local runs may reuse an existing server. The Python CLI can be invoked
by absolute path from another directory; `--report-dir` is relative to the
caller's working directory if specified. Arguments after `--` are pytest
arguments. A filtered run is useful for diagnosis, not a replacement for the
full gate. `--suite bdd` selects the scenario file; the full Python suite already
includes it.

To reproduce only browser failure/recovery cases:

```bash
cd frontend
CI=1 npm test -- tests/recovery.spec.ts --retries=0
```

These tests pass when the injected failure is correctly handled. They do not
leave the application broken. CLI contract tests additionally launch isolated
temporary pytest files that intentionally fail, fail collection, or collect
nothing, and assert the corresponding nonzero status and XML evidence.

## Required quality gates

| Gate | Pass criterion | Evidence |
| --- | --- | --- |
| Python, both CI versions | Full suite exits 0; strict marker validation. An empty suite (pytest exit 5), collection error or assertion failure fails the job. | `python-test-results-3.11` / `python-test-results-3.12`: per-run XML, log, summary. |
| Static checks | Ruff and Prettier exit 0; TypeScript and production Vite build succeed. | CI step logs. |
| Browser | All Chromium tests pass. `test.only` and any test passing only on retry fail CI; one retry is retained for diagnostics. | `browser-test-results`: JUnit, HTML and retained failure traces. |
| Container | Image builds; health, frontend and simulation POST all return successful HTTP responses. | Container job logs; Docker logs on failure. This is a smoke test, not response-schema/load validation. |

Do not remove failing checks or add skips/xfails to obtain a green run. Investigate
the failing assertion and attach its evidence. This change adds no skipped or
expected-failure tests. No coverage-percentage, latency or throughput threshold
is asserted without a measured basis. Required-check branch protection must be
configured separately in GitHub; it is not established by this workflow file.

## Verification record and limitations

See the dated local results below. GitHub Actions and deployment status must be
checked on the eventual commit before merging/deploying. Fault injection proves
the handling of a selected solver outcome or transport failure; it does not
prove a real 20-second timeout, production load tolerance or network reliability.
The suite remains single-worker for browser tests; no concurrent stress or
cross-browser certification is claimed. Python development dependencies use
bounded ranges rather than a separate hash lock, so future tool resolution can
differ even when runtime dependencies are locked.

### Local verification — 2026-10-21

| Check | Observed result |
| --- | --- |
| Original Python tests, excluding the two new test modules | 91 passed. |
| Full Python CLI with `--strict-markers` | 100 passed, zero failures/errors/skips. Includes 3 BDD cases and 6 CLI cases. |
| Standalone `--suite bdd -- --strict-markers -vv` | 3 passed. These are a subset of the 100, not additional coverage. |
| Full Chromium suite with `CI=1` and `--retries=0` | 8 passed, zero failures/errors/skips; 5 existing journeys and 3 recovery cases. |
| Ruff, Prettier, TypeScript/Vite build, whitespace diff check | Passed. |
| Browser gate probes | A deliberate fail-then-pass test and a focused `test.only` each produced exit 1 with CI flags enabled. Probe files and output remain ignored local artifacts. |
| BDD isolation probe | With release deliberately disabled, all three scenarios detected the leak; the following API saturation/recovery test passed and the original semaphore was restored. The injected regression was confined to an ignored test plugin. |
| Container smoke script control flow | Healthy mock commands exited 0; repeated failed health checks exited 22 before simulation. This validates shell control flow only. |

The environment used macOS ARM64, Python 3.11.16, pytest 9.1.1, pytest-bdd 9.0.0
and Node 26.0.0. The existing Python 3.9 `.venv` was preserved; verification used
a separate Python 3.11 virtual environment with the repository's hashed runtime
dependencies. A local ignored Playwright config changed only the server
command/port and test/output paths: a fresh server used port 18080 because 8000 was already
occupied. CI flags remained enabled and retries were explicitly disabled.
Playwright managed and stopped that test server. Reports are local, ignored
artifacts; future CI runs publish the artifact names listed above.

One pre-existing Starlette TestClient/httpx deprecation warning remains in the
Python runs; it was not suppressed. The runtime dependency set was deliberately
left unchanged. Docker's daemon was unavailable, so image build/runtime checks
were **not** verified locally. Python 3.12, Node 24, remote GitHub Actions,
branch protection and Render deployment were **not** verified in this session.
No coverage percentage, performance gain or production reliability claim is
inferred from these passing tests.
