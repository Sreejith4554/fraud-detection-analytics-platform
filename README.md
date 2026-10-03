# Fraud Detection & Analytics Delivery Platform

[![Verified portfolio build](https://github.com/Sreejith4554/fraud-detection-analytics-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Sreejith4554/fraud-detection-analytics-platform/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Sreejith4554/fraud-detection-analytics-platform/actions/workflows/codeql.yml/badge.svg)](https://github.com/Sreejith4554/fraud-detection-analytics-platform/actions/workflows/codeql.yml)

An end-to-end portfolio proof-of-concept demonstrating how a fraud-detection model can be delivered as a tested, containerized analytics platform with API inference, PostgreSQL persistence, operational monitoring, automated quality gates, and reproducible release evidence.

> **Portfolio proof-of-concept — not a production banking system.**
> Synthetic/demo requests are used for runtime verification. Model outputs must not be used for real financial decisions.

## What this project demonstrates

This project goes beyond training a machine-learning model. It treats the model as one component in a broader delivery system:

- reproducible data validation and model evaluation
- frozen, integrity-verified model artifact
- FastAPI inference and operational endpoints
- PostgreSQL persistence and schema migration
- transactional alert creation
- Streamlit analytics dashboard
- Docker Compose deployment
- health/readiness checks and restart verification
- automated integration and container testing
- dependency vulnerability auditing
- CodeQL static security analysis
- Dependabot dependency monitoring
- evidence-backed release and operational documentation

The implementation is a new AI-assisted portfolio project inspired by research from Sreejith Sivakumar's MBA dissertation. It was not part of the dissertation and is not presented as employment experience.

## Architecture

```text
Accepted transaction data
        |
        v
Data validation / feature preparation
        |
        v
Frozen fraud model
        |
        v
FastAPI inference service
        |
        +--------------------+
        |                    |
        v                    v
PostgreSQL              Model metadata
Predictions             Health / readiness
Alerts                   Operational endpoints
        |
        v
Streamlit analytics dashboard
```

The local container runtime consists of:

```text
Dashboard  --->  API  --->  PostgreSQL
                  |
                  v
            Verified model

Migration job ---> PostgreSQL schema
```

See [architecture documentation](docs/architecture/design.md) for the detailed design.

## Verified delivery pipeline

Every qualifying push or pull request runs an automated verification pipeline.

### Integration gate

The integration job:

1. launches an isolated PostgreSQL service
2. installs the pinned Python dependency set
3. audits dependencies for known vulnerabilities
4. checks repository structure and linting
5. acquires and validates the accepted dataset
6. verifies/restores the frozen model
7. executes the complete test gate with skips treated as failures
8. uploads the verified model artifact for the container stage

### Container gate

Only after integration succeeds, the Compose job:

1. downloads the verified model artifact
2. verifies artifact integrity
3. creates the disposable CI secret
4. builds the application image
5. launches the complete Docker Compose stack
6. waits for service health checks
7. verifies persistence and PostgreSQL restart behavior
8. collects runtime evidence
9. removes disposable containers and volumes

The hosted integration and Compose pipeline has been successfully executed on GitHub Actions.

## Security and supply-chain controls

The repository includes several automated controls:

- GitHub Actions pinned to immutable commit SHAs
- Python and PostgreSQL runtime images pinned to exact versions and immutable digests
- read-only application containers
- non-root application user
- `no-new-privileges` container security option
- database credentials supplied through Docker secrets
- PostgreSQL not published to the host
- `pip-audit` dependency vulnerability gate
- CodeQL Python analysis with `security-extended` queries
- Dependabot monitoring for Python, Docker, and GitHub Actions dependencies

Security automation complements, rather than replaces, application review and production security engineering.

## Model integrity and reproducibility

Runtime inference uses a canonical frozen model artifact.

The production/runtime path requires the exact expected SHA-256 digest. Reconstruction is treated separately as a reproducibility check and is verified against a recorded numerical fingerprint.

This prevents a newly serialized but behaviorally similar model from silently replacing the canonical runtime artifact.

See [model decision and reproducibility documentation](docs/phase-3-4-model.md).

## Offline model results

Weighted logistic regression was selected using validation average precision.

Held-out test results:

| Metric | Result |
| --- | ---: |
| Precision | 72.4% |
| Recall | 74.3% |
| F1 | 0.733 |
| Average precision | 0.748 |
| Fraud labels detected | 55 / 74 |
| Fraud labels missed | 19 |
| Non-fraud records flagged | 21 |

Scores are uncalibrated and must not be interpreted as real-world fraud probabilities.

Supporting evidence is stored under [`docs/evidence`](docs/evidence).

## Data milestone

The accepted source dataset contains:

- 284,807 source rows
- 492 fraud labels
- validated schema and finite values
- 170,235 training rows after documented duplicate exclusions
- 56,184 validation rows
- 55,026 held-out test rows

Dataset rights are separate from the repository's MIT-licensed source code.

See [data documentation and reproduction instructions](data/README.md).

## API

The FastAPI service exposes operational and scoring functionality including:

- health and readiness checks
- model metadata
- prediction/scoring
- persisted prediction history

With PostgreSQL configured, predictions are persisted and qualifying events can create alerts transactionally.

Database failures are surfaced as service-unavailable responses rather than silently accepting writes.

See the [API runbook](docs/phase-5-api.md).

## PostgreSQL persistence

The persistence layer includes:

- explicit schema migration
- prediction storage
- model metadata
- alerts
- transactional write behavior
- rollback verification
- restart/persistence verification

Runtime verification confirms that persisted data survives an ordinary PostgreSQL container restart.

See [PostgreSQL delivery evidence](docs/phase-6-postgresql.md).

## Dashboard

The Streamlit dashboard provides:

- aggregate prediction analytics
- risk distribution views
- recent prediction activity
- read-only alert queue
- synthetic transaction submission
- model and operational information

Dashboard data is retrieved through the API rather than directly querying PostgreSQL.

See [dashboard documentation](docs/phase-7-dashboard.md).

## HTTP scoring verification

An actual Uvicorn server completed 100 sequential synthetic scoring requests.

Recorded local p95 after warm-up: **2.57 ms**.

This is local synthetic verification only and is **not** presented as a production latency benchmark.

Evidence: [`docs/evidence/api-smoke.json`](docs/evidence/api-smoke.json).

## Run locally with Docker

Prerequisites:

- Docker with Compose support
- Git

Create the local secret expected by Compose:

```bash
mkdir -p .secrets
printf 'replace-with-a-strong-local-secret' > .secrets/db_password
```

Then:

```bash
docker compose up --build -d --wait
python scripts/verify_compose.py
```

Local endpoints:

- API documentation: `http://127.0.0.1:8000/docs`
- Dashboard: `http://127.0.0.1:8501`

Stop the disposable environment with:

```bash
docker compose down --volumes --remove-orphans
```

## Run the Python development environment

Python 3.12 is the verified runtime family.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-ci.txt
python -m ruff check .
python scripts/ci_verify.py
```

Windows PowerShell activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Evidence and delivery documentation

Key project records include:

- [verification overview](docs/verification.md)
- [data delivery](docs/phase-2-data-delivery.md)
- [model development and reproducibility](docs/phase-3-4-model.md)
- [API delivery](docs/phase-5-api.md)
- [PostgreSQL persistence](docs/phase-6-postgresql.md)
- [dashboard delivery](docs/phase-7-dashboard.md)
- [container delivery](docs/phase-8-9-containers.md)
- [CI pipeline](docs/phase-10-ci.md)
- [release readiness](docs/release-readiness.md)
- [Compose incident record](docs/incident-compose-network.md)
- [machine-readable evidence](docs/evidence)

## Delivery approach

The project is organized across five workstreams:

1. **Data & ML** — dataset acceptance, validation, model selection, and reproducibility
2. **Backend/API** — inference contract, validation, and operational endpoints
3. **Data & Integration** — PostgreSQL schema, persistence, and alerts
4. **Platform/DevOps** — containers, CI/CD gates, security, and runtime verification
5. **Product/Analytics** — dashboard, operational visibility, and portfolio communication

The repository intentionally preserves decision records, verification evidence, and incident documentation alongside the implementation to demonstrate not only *what* was built, but *how delivery risk was managed*.

## Current scope

**Verified**

- data validation and reproducibility
- held-out model evaluation
- canonical model integrity
- real HTTP inference
- PostgreSQL persistence and transactional behavior
- Streamlit application functionality
- containerized local runtime
- database restart/persistence behavior
- hosted GitHub integration testing
- hosted Docker Compose verification
- dependency vulnerability auditing
- CodeQL static security analysis
- automated dependency monitoring

**Not claimed**

- production deployment
- banking-grade fraud performance
- production-scale load testing
- calibrated fraud probabilities
- production disaster recovery
- external penetration testing
- real financial decision use

## Author

**Sreejith Sivakumar**

Project focus: technical project delivery, system integration, API/data workflows, release governance, and analytics.


Code license: MIT. Dataset rights are separate.
