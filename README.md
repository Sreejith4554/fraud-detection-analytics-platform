# Fraud Detection & Analytics Delivery Platform
A portfolio proof-of-concept connecting fraud-model inference with API delivery, persistence, analytics and release evidence.

**Status: trained/evaluated baseline and tested real-model HTTP scoring. PostgreSQL persistence and alerts are now tested; the Streamlit dashboard reads real persisted data. Docker Compose runtime verification PASSED on the user’s machine (reported execution evidence; original JSON pending import). Hosted CI and deployment remain pending.**

This is a new AI-assisted portfolio implementation inspired by Sreejith Sivakumar’s research-based MBA dissertation. It was not part of the dissertation and is not employment experience or a banking-grade system. Predictions, once implemented, must not be used for real financial decisions.

## Start here
- [Phase 0–1 blueprint: requirements, five workstreams, risks and milestones](docs/phase-0-1-blueprint.md)
- [Proposed architecture diagrams](docs/architecture/design.md)
- [Verification evidence](docs/verification.md)
- [Accepted dataset and reproduction commands](data/README.md)
- [Phase 2 delivery evidence and learning](docs/phase-2-data-delivery.md)

## Run the foundation (Python 3.12)
```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python -m ruff check .
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```
Open http://127.0.0.1:8000/docs. With the trusted model loaded, `/score` returns genuine model output with `persisted=false`; `/model-info` exposes its verified metadata. `/health` reports liveness and scoring availability. With DATABASE_URL and schema revision 1 configured, `/ready` returns 200, `/predict` persists real scores and conditional alerts, and `/predictions` returns history. Database failures return 503. Invalid input returns 422. [API runbook and synthetic request example](docs/phase-5-api.md).

Source-only checkouts must restore the model first using [these instructions](docs/phase-3-4-model.md); the private milestone ZIP includes it. Real-artifact tests skip if it is absent, so a release must not treat such a run as full verification.

## Delivery approach
One owner, five workstreams: Data & ML, Backend/API, Data & Integration, Platform/DevOps and Product/Analytics. Short local feature branches and commits capture increments; future GitHub issues/PRs/CI require account-action approval. Self-review will be labelled honestly.

## Next gate
Run the prepared GitHub Actions workflow after repository authorization; hosted CI remains unverified. The completed local Docker check need not be repeated. Future metrics, screenshots, Docker/CI/deployment status and portfolio claims will be added only after verification. No live demo exists.

Author: Sreejith Sivakumar. Implementation assistance: OpenAI Codex. Code licence: MIT; dataset rights are separate.

## Data milestone results
284,807 source rows; 492 fraud labels; validated schema and finite values. After documented duplicate exclusions: 170,235 training, 56,184 validation and 55,026 test rows. Full-data repeatability and overlap checks are recorded under docs/evidence. 61 tests pass with the model and dedicated PostgreSQL test database present. Offline model results are recorded below.

## Offline model milestone
Weighted logistic regression selected using validation AP; held-out test precision 72.4%, recall 74.3%, F1 0.733 and average precision 0.748. It detected 55 of 74 fraud labels, missed 19 and flagged 21 non-fraud records. Scores are uncalibrated and must not be interpreted as real-world fraud probabilities. [Decision, limitations and artifact restoration](docs/phase-3-4-model.md).

## HTTP scoring verification
Actual Uvicorn server completed 100 sequential synthetic score requests; local p95 2.57 ms after warm-up. No database writes and no production latency claim. [Evidence](docs/evidence/api-smoke.json).

## Durable prediction verification
100 synthetic predictions and one alert survived an actual PostgreSQL restart. A controlled alert-insert failure rolled back all related writes. [Database setup, evidence and limitations](docs/phase-6-postgresql.md). Local deployment only.

## Dashboard
Streamlit provides aggregate analytics, a read-only alert queue, a synthetic transaction form and model/operations details. All data comes through the API. [Run instructions and UI verification](docs/phase-7-dashboard.md). Functional tests and server smoke passed; browser screenshots and responsive visual QA remain pending.

## Container checkpoint — local runtime passed
The user reported a successful verify_compose.py run, successful migration, healthy API/dashboard/PostgreSQL containers and recovery after the verifier restarted PostgreSQL. The earlier managed-runtime limitation is historical; the local Compose gate is closed. [Concrete launch and verification steps](docs/phase-8-9-containers.md).

## CI and release readiness
GitHub Actions now defines full integration and dependent container jobs, with pinned action commits and zero-skips enforcement. Five new gate tests passed locally. No hosted CI run is claimed. [Pipeline](docs/phase-10-ci.md) · [Current release gates](docs/release-readiness.md) · [Local Compose incident](docs/incident-compose-network.md).
