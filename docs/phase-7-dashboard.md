# Phase 7 — product analytics and alert views

Historical milestone snapshot. The statements below preserve the project state at this phase and are not the current release status. The completed proof-of-concept now has verified local Docker Compose execution, passing hosted GitHub integration and container gates, CodeQL analysis, and browser demonstration evidence. See [release readiness](release-readiness.md) for the authoritative current status.

**TESTED functional dashboard, backed by the real API and PostgreSQL. Local-only.**

## Delivered
A dark Streamlit interface with four areas: Overview, Review queue, Submit demo, and Model & operations. A persistent warning states this is a portfolio proof-of-concept and must not support real financial decisions. Sidebar explains score calibration and the absence of bank connections/external notifications.

- Overview: total predictions, HIGH count, flagged share, stored alerts, model-score histogram, UTC processing timeline, mean score and latest 20 predictions.
- Review queue: read-only paginated OPEN alerts with score, threshold, model and source provenance. No acknowledgement or case-management workflow is implied.
- Submit demo: amount, elapsed seconds and a JSON array of 28 anonymised components; all UI submissions are SYNTHETIC. Successful /predict calls save real model outputs; UI reruns to refresh totals. Invalid submissions show an error, clear any previous success message and do not assume persistence.
- Model & operations: verified model metadata and process-scoped operational counters.

The UI imports neither a database client nor a model loader. API_BASE_URL is configuration, not an editable visitor-supplied URL. Database credentials remain with the API.

## Backend changes and accuracy controls
GET /analytics aggregates the entire database in a repeatable-read snapshot. Total, HIGH/LOW counts, mean, histogram, source counts and timeline derive from persisted records. Exact score 1.0 belongs in the last histogram bin. UTC processing dates are not the original dataset's elapsed transaction time. These records have no ground-truth review labels, so flagged share is never labelled “fraud rate”.

GET /alerts provides bounded pagination (limit 1–100, nonnegative offset), with deterministic newest-first ordering. History pagination remains separate from global totals. Timeline is all stored processing dates; no hidden date filter. Empty databases display zero counts and an absent mean rather than invented scores.

## Verification
58 tests pass with real model and dedicated PostgreSQL test database; lint passes. Four additional tests cover:
1. Empty database analytics and alerts.
2. 22 persisted predictions versus a 20-row history page: totals, histogram and timeline still sum to 22; alert links and pagination validation checked.
3. Streamlit AppTest against a real HTTP API and PostgreSQL: valid form submission writes one prediction and refreshes KPI count; invalid array adds no row and shows no stale success.
4. Unavailable API renders an error state without fabricated metrics or an application exception.

Live server smoke: API /ready, Streamlit health and Streamlit root returned 200. AppTest displayed the existing demo database totals of 100 predictions, one flag, 1.00% flagged share and one alert. These are SYNTHETIC demonstration inputs from phase 6, not bank traffic. See docs/evidence/dashboard-smoke.json.

AppTest simulates UI interactions; the backend calls and PostgreSQL writes are real. This is functional UI verification, not browser-pixel verification. No screenshot or human stakeholder UAT approval is claimed. Browser screenshots, responsive layout and accessibility review remain presentation/release gates.

## Actual development correction
The initial UI test run failed twice because the test harness resolved a relative dashboard path under tests/. The path was corrected to an absolute repository-derived path and rerun successfully. This was a local automated-test failure, not a GitHub CI incident. The stale-success behaviour was also corrected and covered by an assertion. A deprecated Streamlit width argument was replaced with the supported width='stretch' form. The pre-existing Starlette test-client warning remains documented.

## Run locally
Use the phase-6 PostgreSQL setup and trusted artifact. Set DATABASE_URL for the API. From repository root, start two terminals:

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

```bash
API_BASE_URL=http://127.0.0.1:8000 python -m streamlit run dashboard/app.py
```

Open http://127.0.0.1:8501. The app reads API_BASE_URL and defaults to the same local address; .env is not loaded automatically. .streamlit/config.toml sets the dark theme, loopback binding and disables usage telemetry.

Verification:
```bash
python -m pytest -q
python -m ruff check .
PYTHONPATH=. python scripts/smoke_dashboard.py
```
Set FRAUD_TEST_DATABASE_URL to the disposable *_test database for the complete suite; set DATABASE_URL for the smoke's demo database. The smoke starts temporary servers on ports 8009/8510 and stops them afterwards. It does not add records. Missing model or test DB means integration checks skip; a skipped run does not satisfy the 58-test gate.

## Decisions and remaining risk
ADR19: Streamlit consumes API aggregates rather than calculating totals from paginated history. This prevents quietly undercounting transactions.
ADR20: manual refresh and rerun after submission, no caching or background polling in v1. Separate API calls may observe different moments if other users write concurrently; only the aggregate endpoint itself uses one database snapshot.
ADR21: keep queue read-only. A workflow for review outcomes, audit trails of analyst actions and permissions needs separate requirements.

Synchronous calls and modest data volumes remain intentional POC limits. No authentication, public deployment, cross-browser proof, load test, confirmed fraud rate or external notification is claimed. Dashboard availability currently requires full /ready, so a missing model blocks viewing even historical records; degraded read-only operation is deferred.

## Workstream handoff and next gate
WS1 model → WS2 API → WS3 PostgreSQL → WS5 analytics now communicates end to end. WS4 must package that working path in containers and verify startup, volumes and reproducibility. Docker/Compose, hosted CI and public deployment are still unverified.

## TPM knowledge check
1. Why must KPI totals come from an aggregate query rather than the latest history page?
2. Why is “flagged share” more accurate than “fraud rate” here?
3. Which dependency should you investigate first if the dashboard reports the service unavailable?
4. What does AppTest prove, and what still needs browser or human review?
