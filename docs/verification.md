# Current verification status — 6 October 2026

The end-to-end portfolio proof-of-concept is currently working and verified. The sections below preserve historical milestone results and should be read as point-in-time development records rather than the present release state.

Current verified state:

- canonical model artifact integrity verified
- FastAPI inference operational
- PostgreSQL persistence and transactional alert creation operational
- Streamlit analytics dashboard operational, including OPEN/RESOLVED alert views and API-backed alert resolution
- local Docker Compose runtime verified
- PostgreSQL restart/persistence behavior verified
- latest complete local PostgreSQL-backed regression suite: **81 passed, 0 failed, 0 skipped**
- hosted GitHub integration pipeline verified successfully
- hosted Docker Compose build/runtime verification completed successfully
- dependency vulnerability audit included in the passing CI gate
- CodeQL Python security analysis passing
- Dependabot monitoring configured for Python, Docker, and GitHub Actions
- browser dashboard views visually verified and captured under `docs/images`
- deterministic validation-partition demo replay implemented without using ground-truth labels for row selection
- synthetic out-of-distribution alert-path demonstration verified through the real inference, persistence, alert, and dashboard path

The current development commit verified by the hosted portfolio build is:

`61fd9bdcaa94da7f08bb752ace06f25bf1d7cff0`

CodeQL remains passing for the released v1.0.0 baseline. The current feature branch will receive commit-specific CodeQL verification when proposed to `main`.

The project remains a **portfolio proof-of-concept, not a production banking system**. Authentication/authorization, full analyst case management, production-scale load validation, real bank integration, public application deployment, formal accessibility testing, external penetration testing, production disaster recovery, and real financial use are not claimed.

See [release readiness](release-readiness.md) for the authoritative current release-gate assessment.

---

# Historical milestone verification — 2 October 2026

Scope: phase 0–1 design baseline plus initial FastAPI foundation. Full project Definition of Done is NOT satisfied.

| Gate | Observed result | Limitation |
|---|---|---|
| Python execution | Python 3.12.14; dependencies installed and frozen | Network-restricted install failed first; permitted escalation succeeded |
| Automated tests | 17 passed in 0.30 seconds after import corrections | Contract/scaffold tests only; no model or DB integration |
| Lint | Ruff: all checks passed | Four import-order violations fixed before pass |
| Live HTTP | Temporary Uvicorn server: /health 200; /openapi.json 200 | Server stopped after smoke test; not a hosted deployment |
| Honest readiness | /ready and valid /predict return 503 | No scoring until dependencies implemented |
| Invalid input | Missing/extra/wrong-length/negative/nonfinite and unsupported inputs rejected | Provisional dataset contract |
| Git diff | git diff --check passed | Local Git only |
| Source review | CV and dissertation read; unsupported transfers excluded | Not independent verification of source claims |
| Docker/PostgreSQL | Executables not available in current environment | No build, Compose or persistence pass claimed |
| CI / cloud | Not run | No external account changes authorized |
| Learner understanding | Questions supplied | Responses pending |

The initial in-process pytest invocation stalled in the restricted sandbox. The same tests completed promptly outside it; sandbox interference is the working diagnosis, not a proven root cause. One dependency warning remains: Starlette deprecates its httpx-based TestClient path. Current pinned tests pass; revisit the supported test client before dependency upgrades. No warnings suppressed.

Design review: all 18 requested planning outputs are covered in the blueprint, with four proposed architecture diagrams. No queue, cluster, feature store, microservice fleet or paid integration is necessary for the MVP. Model/schema/hosting details remain explicitly gated.

Reproducibility scope: commands exercised in the development environment. A fresh-environment install, Docker reproduction, ML reproducibility, PostgreSQL integration, secret scanner and hosted CI remain later gates. Do not describe this milestone as portfolio-ready.

## Phase 2 verification update
33 tests passed (16 data-pipeline checks added). Actual CSV validation and two complete ingestion runs succeeded; partition and report hashes matched. Cross-partition non-time signature overlap was zero. Training-only EDA generated. See docs/evidence and docs/phase-2-data-delivery.md. Docker, PostgreSQL, model inference and deployment remain unverified.

## Phases 3–4 update
39 tests pass; lint passes. Four candidates trained, validation decision frozen in commit 72f8398 before held-out evaluation. Real model reloaded and independently retrained with zero validation probability difference; scaler training-only statistics checked. See model-selection.json, test-evaluation.json and model-reproducibility.json. API integration is still pending.

## Phase 5 update
49 tests pass with the real artifact present, including 10 new serving integration cases; lint passes. Real HTTP scoring tested over 100 sequential synthetic requests. Structured logging enabled; invalid data and model failures handled safely. /predict and /ready still return 503 until PostgreSQL persistence. Full prediction Definition of Done remains open.

## Phase 6 update
54 tests passed against actual PostgreSQL and the saved model. Controlled database failure rolled back all related rows. 100 synthetic HTTP predictions and one alert survived an ordinary database restart with storage intact. This does not demonstrate backups or workspace-loss recovery. See phase-6-postgresql.md.

## Phase 7 update
58 tests pass, including full-database aggregates and Streamlit interactions against real HTTP/PostgreSQL. Server health and root HTTP checks passed. The demo displayed 100 stored predictions and one alert. Browser-pixel/screenshot review remains pending; no human UAT sign-off claimed.

## Phases 8–9 checkpoint
61 tests pass; lint and Compose configuration/topology checks pass. Docker daemon cannot initialize networking (iptables permission denied). Image build and Compose runtime/volume checks remain BLOCKED, not passed. See container-gate.json and phase-8-9-containers.md.

## User local Docker verification and CI preparation
Local Compose gate PASSED per user-provided verifier output and final healthy service states. Earlier BLOCKED entries are superseded, not repeated. Five new test-report gate tests pass; workflow structure and lint pass. No hosted run or combined 66-test full-suite pass is claimed.
