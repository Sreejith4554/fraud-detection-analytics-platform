# Phase 5 — model-serving preview

Historical milestone snapshot. Current status: local Compose verification PASSED per user execution report; hosted CI/deployment pending. See [release readiness](release-readiness.md) for superseding gate status.

**TESTED local inference integration. Durable predictions are still blocked on PostgreSQL.**

## Objective and acceptance
Connect the frozen model to the HTTP boundary, preserve exact feature mapping, reject invalid requests, and make dependency failures visible without fake successful predictions.

| Criterion | Evidence |
|---|---|
| Score comes from trained artifact | Integration test compares HTTP score with direct predict_proba, exact agreement |
| Feature order preserved | Time,V1..V28,Amount; ordered mapping test |
| Startup checks | Manifest schema, sklearn version, threshold, SHA256, feature names and binary class order verified |
| Invalid requests safe | 422; response omits rejected values; request logs exclude bodies |
| Failure behaviour | Missing/corrupt/incompatible artifact gives scoring 503; unexpected inference errors return safe 500 |
| Real HTTP execution | Uvicorn smoke: valid score 200, invalid input 422, durable predict/readiness 503 |
| Observability | JSON event logs, generated request IDs, process-scoped request/error/scoring counters |
| Full tests | 49 pass with trusted artifact present; lint passes |

## ADR15: temporary non-persisted scoring boundary
The final POST /predict contract requires atomic PostgreSQL persistence. Returning success there before persistence exists would misrepresent the system. Added POST /score as an explicitly non-persisted preview; it includes persisted=false, source label, model version, threshold and limitations. It creates no transaction ID, history or stored alert. It will remain a useful diagnostic route, but it does not satisfy the final durable prediction requirement.

## Routes at this milestone
| Route | Behaviour |
|---|---|
| GET /health | 200 liveness; scoring_ready reflects loaded artifact; prediction_ready=false |
| GET /ready | 503 until durable prediction dependencies are integrated |
| GET /model-info | 200 with verified manifest fields; 503 if model unavailable |
| POST /score | Valid input → real score/decision; persisted=false |
| POST /predict | 503; PostgreSQL integration pending |
| GET /predictions | 503; no history store yet |
| GET /metrics | Process-lifetime counts and mean scoring duration; resets on restart |
| GET /docs | Interactive OpenAPI documentation |

Response score is named model_score to avoid presenting poor calibration as financial certainty. HIGH if score >= threshold; otherwise LOW. FLAG_FOR_REVIEW is a demonstration decision, not a recorded alert, payment block or human action. No rule says the score is calibrated.

## Local run
Use Python 3.12 and the pinned requirements. The private milestone package includes the trusted artifact. From a source-only checkout, follow the data-card download/ingestion instructions and scripts/restore_model.py first.

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```
In another terminal, from repository root:
```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/score \
  -H 'Content-Type: application/json' \
  --data-binary @examples/synthetic-transaction.json
```
The included input is SYNTHETIC, not a bank transaction or an evaluation case. Its observed real score was 0.009240607812024676 (LOW); it was not stored. See docs/evidence/api-smoke.json. Do not interpret arbitrary synthetic vectors as realistic transaction scenarios.

## Test and performance reproduction
```bash
python -m pytest -q
python -m ruff check .
PYTHONPATH=. OPENBLAS_NUM_THREADS=2 python scripts/smoke_api.py
```
The smoke script starts a temporary localhost service on port 8765 and stops it afterwards. Choose an unused port before adapting it. It uses one warm-up and 100 sequential requests on the same synthetic input: p50 2.07 ms, p95 2.57 ms, max 5.39 ms in this environment. Hardware/runtime context is in the report. This is not a load test, hosted latency, database latency or SLA.

Ten real-artifact integration cases skip if the artifact is absent. A release gate must restore/provide the trusted model and require those tests to run; a smaller green test count is not equivalent evidence. Test doubles appear only in boundary/error unit checks and are labelled; the real HTTP smoke and direct-model comparison use the trained artifact. The existing Starlette test-client deprecation warning remains; no warning is suppressed.

## Security and limitations
Local-only server, no authentication, no public deployment. Do not expose it publicly until access, request limits and abuse protection are designed. No raw request bodies or feature vectors are logged; route templates avoid user-supplied URLs in application request events. Uvicorn raw access logging is disabled by the documented command. Unexpected errors return generic responses. Validation returns field locations and types, not input values.

Model checksums detect accidental changes but do not make pickle/joblib safe against a malicious actor replacing both artifact and manifest. Only trusted build artifacts are permitted. No upload route exists. Out-of-distribution detection and calibrated probabilities are not implemented. Model computation is synchronous inside a single local process; concurrency/scaling and multi-worker metrics aggregation are not tested.

## TPM handoff
WS1 → WS2 contract is now exercised with actual inference. WS3 owns the next unresolved dependency: atomic transaction/prediction/alert persistence. Schema and commit semantics must be agreed before /predict returns success. A database failure must not be hidden behind a successful model score.

Knowledge check:
1. Why can /score return 200 while /ready and /predict return 503?
2. Why is checking feature order as important as checking that the file loads?
3. What is the difference between FLAG_FOR_REVIEW here and a persisted alert?
4. Why is this local p95 measurement not an SLA?

Credible interview answer: “I coordinated the boundary between the offline model and API in an AI-assisted portfolio build. We checked model identity, feature order and failure behaviour, and kept the durable endpoint blocked until persistence was available. I distinguish a working model preview from an integrated transactional service.”
