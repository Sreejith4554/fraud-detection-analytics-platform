# Phase 10 — automated release gates
**Workflow implemented and statically checked. Hosted GitHub Actions execution PENDING.**

## Pipeline
Integration job: checkout → Python 3.12.14 → pinned dependencies → repository hygiene/YAML checks → lint → verified public dataset → chronological partitions → restore frozen model → full tests with zero skips → upload model and test report.

Compose job (requires integration success): checkout → download that exact model artifact → verify checksum/create local secret → build/start Compose → HTTP prediction and database restart verification → retain logs/evidence → destroy disposable runner volumes.

Triggers: pull requests, pushes to main/feature branches and manual dispatch. Default token permissions are read-only. Official action references are pinned to 40-character commits resolved from their upstream tags on 3 October 2026. No deployment, image-registry push or public publishing step exists. Concurrency cancels obsolete runs of the same ref; job timeouts bound runner use.

## Why skips fail
The existing test suite intentionally skips real-artifact and database tests if prerequisites are absent. A superficial green pytest run could therefore omit the most important integration evidence. scripts/ci_verify.py executes pytest, then rejects JUnit reports with any skipped, failed or errored case, or no cases at all. Successful tests produce reports/test-gate.json. Failing commands stop downstream jobs. `if: always()` applies only to evidence collection and cleanup, never to bypass a release gate.

Five new local tests verify acceptance of completed test reports and rejection of skips, failures, errors and empty runs. These fixtures are controlled tests of the gate, not fabricated hosted CI results. Workflow YAML parses and critical control assertions pass. Ruff and tracked-file hygiene pass. The prior full local application suite had 61 passing tests; this milestone adds five gate tests, but a combined 66-test/hosted run is not claimed.

## Reproducibility constraints
A clean runner downloads the publisher dataset, checks the accepted hash and reconstructs the frozen artifact. Restoration requires exact model bytes. Cross-host BLAS/Python serialization differences may cause a legitimate failure; investigate and version a reproducible artifact rather than bypassing the guard or silently selecting a new model. No test-set model selection is repeated.

Data acquisition and image/dependency downloads require network access. Raw transactions are not uploaded as CI artifacts. The CI PostgreSQL password is an explicitly disposable runner-only credential, not a production secret. Compose generates its own local secret file. Reports and the reconstructed trusted model are retained briefly in GitHub Actions artifacts; application data remains ephemeral.

This workflow has not yet run on GitHub. Python version availability, network acquisition and container execution on the chosen runner remain runtime gates. Static YAML validation does not emulate GitHub Actions. Branch protection/required checks are recommended after the first successful hosted run, but no repository settings have been changed.

## Local checks for this milestone
```bash
python -m pip install -r requirements-ci.txt
python scripts/check_workflow.py
python scripts/check_repository.py
python -m ruff check .
python -m pytest tests/test_ci_gate.py -q
```
The full CI-equivalent runner command `python scripts/ci_verify.py` requires the model and FRAUD_TEST_DATABASE_URL; skips deliberately fail. Existing Docker verification on the user's machine is accepted and is not repeated merely to update docs. A future clean CI runner tests portability of a new source commit independently.

## Next external gate
Create/push the intended repository only with the user's explicit authorization, then inspect the first hosted run and fix observed failures. No remote repository, issue, PR, hosted run or release has been created in this milestone. Before public publication, also collect original Compose evidence, complete screenshots/accessibility checks, inspect secrets and review dataset/model publication obligations.

## TPM knowledge check
1. Why should a green test run with skipped PostgreSQL tests block release?
2. Why must the container job wait for the integration job?
3. Why does the user's local Compose pass not automatically prove a clean GitHub runner passes?
4. What evidence should a failed CI run retain for diagnosis?
