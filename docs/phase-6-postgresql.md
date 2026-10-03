# Phase 6 — PostgreSQL persistence

Historical milestone snapshot. Current status: local Compose verification PASSED per user execution report; hosted CI/deployment pending. See [release readiness](release-readiness.md) for superseding gate status.

**TESTED local integration; no public service or production durability claim.**

## Delivered
PostgreSQL 16 with SQLAlchemy/psycopg. Explicit schema revision 1 installer; no table creation on API startup. Transactions store labelled demonstration features; predictions store the real score, selected threshold, model version/hash and UTC timestamp; HIGH predictions also store one OPEN alert. UUIDs link all records. A uniqueness constraint allows only one alert per prediction.

`POST /predict` now succeeds only after one transaction commits all required rows. PostgreSQL exceptions produce a safe 503, with no successful prediction response. `/score` remains a non-persisted preview. `/predictions` returns bounded pagination (limit 1–100, nonnegative offset), newest first. `/ready` checks the model, schema revision and required tables/columns. `/health` remains liveness; use `/ready` for dependency readiness.

## Verification
54 tests passed with the real artifact and real PostgreSQL present; lint passed. Five additional database tests cover atomic low/high submissions and history, alert failure rollback, API restart, unavailable database and schema-version rejection. No SQLite substitute.

Controlled failure injection: during the alert insert, a test issues SELECT 1/0 to PostgreSQL. The server rejects the statement and the transaction rolls back. Observed counts after failure: transactions=0, predictions=0, alerts=0. Removing the fault restores successful writes. This is a labelled test scenario, not a production incident.

Actual HTTP smoke: 99 ordinary SYNTHETIC inputs plus one deliberately extreme SYNTHETIC vector through the trained model. The extreme vector creates a HIGH decision; it is not realistic fraud evidence. All 100 predictions persisted. PostgreSQL was stopped and restarted; a new API process read the same 100 prediction IDs afterwards. SQL counts verified 100 transactions, 100 predictions and one alert. See postgresql-smoke.json. No source dataset rows were submitted or packaged.

## Reproduce with an existing local PostgreSQL installation
Provision separate databases `fraud_demo` and `fraud_test` and a local role with appropriate privileges. Set DATABASE_URL using the template in .env.example; do not commit actual credentials. The API does not automatically load .env.

```bash
python -m pip install -r requirements.txt
python -m database.migrate
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```
In another terminal with repository root as current directory:
```bash
curl -s http://127.0.0.1:8000/ready
curl -s http://127.0.0.1:8000/predict \
  -H 'Content-Type: application/json' \
  --data-binary @examples/synthetic-transaction.json
curl -s 'http://127.0.0.1:8000/predictions?limit=20&offset=0'
```
Set FRAUD_TEST_DATABASE_URL to the disposable `fraud_test` database and run `python -m pytest -q`. Tests deliberately truncate that database's demonstration tables and require a database name ending in `_test`. Five PostgreSQL tests skip if the variable is absent; ten artifact tests skip if the model is absent. Such a run is not the full 54-test gate.

For restart smoke: run `PYTHONPATH=. python scripts/smoke_persistence.py seed`, restart only your project PostgreSQL instance, then run `PYTHONPATH=. python scripts/smoke_persistence.py verify`. The seed stage writes 100 new synthetic records, not an idempotent update. Use a dedicated demo database and do not run concurrent writes during this test.

The validation environment used a private Unix socket, no TCP listener, local trust authentication and an isolated administrator role. This is development-only configuration. A deployed service needs a restricted application role, protected credentials, network controls and transport security. Installation/provisioning remains platform-specific until the Compose milestone; Docker has not been tested.

## Decisions and limitations
ADR16: synchronous model→database transaction is enough for this POC. No queue or outbox is needed for database-only alerts; external alert delivery remains out of scope.
ADR17: store immutable model identity with every prediction so later model changes do not erase provenance. Threshold/risk/decision consistency is checked in PostgreSQL.
ADR18: use an explicit initial schema installer rather than a general migration framework. Future schema changes require a numbered migration; create_all is not a migration strategy. A revision check is not a complete schema-drift audit.

Retries create new submissions: no idempotency-key guarantee yet. If a connection drops after commit but before acknowledgement, the caller can be uncertain whether storage succeeded; do not claim exactly-once semantics. Pagination totals can change under concurrent writes; no snapshot-consistent paging claim. High-risk alert existence is enforced by the application transaction, not a cross-table database constraint. Out-of-band DB writers are not supported.

Restart survival is not backup/disaster recovery. The original temporary cluster disappeared during the conversation pause; it was recreated and all tests rerun. The test above demonstrates an ordinary restart with storage intact, not survival after workspace deletion. No enduring hosted database exists. Future Compose volumes and deployment backup plans must address their own lifecycle.

## Delivery status
WS2/WS3 handoff now works: HTTP input→real model→atomic PostgreSQL writes→history API. The outstanding Product/Analytics workstream can consume these records next. Stored alerts are genuine database records; no email or webhook is sent. Dashboard, container execution, hosted CI, release deployment and learner responses remain open.

## TPM knowledge check
1. Why must the transaction, prediction and alert commit together?
2. How does the rollback test demonstrate more than receiving an HTTP 503?
3. Why is surviving a database restart different from having a backup?
4. What risk remains if a client retries after losing the response to a committed request?
