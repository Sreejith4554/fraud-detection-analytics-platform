# Current release readiness - 13 October 2026

**Working, tested portfolio proof-of-concept. Not a production banking system.**

This document records the current release state. Historical phase documents preserve the evidence and limitations that applied at earlier milestones.

The current development candidate is **v1.2.0**. The latest published release remains **v1.1.0** until the v1.2.0 branch completes hosted CI, release-specific CodeQL, review, merge, and release publication.

## Current release gates

| Gate | Status | Evidence / limitation |
| --- | --- | --- |
| Data and offline model | PASS | Validated dataset pipeline, frozen model decision, held-out evaluation, checksums, and reproducibility evidence |
| Model artifact integrity | PASS | Canonical runtime artifact verified by exact SHA-256; reconstruction separately verified against numerical fingerprint |
| API and PostgreSQL | PASS | Real inference, persistence, transactional alerts, analytics/history, revision-3 investigation persistence, and lifecycle behavior verified |
| Schema revision 3 migration | PASS | Live demonstration database migrated from revision 2 to 3 with 106 transactions, 106 predictions, and 1 OPEN alert preserved; no historical investigations or notes were invented |
| Pre-migration backup and local recovery | PASS | PostgreSQL custom-format backup was archive-validated, copied outside the database container, and restored into an isolated disposable database with the exact revision-2 106/106/1 OPEN state |
| Investigation workflow | PASS FOR V1.2 SCOPE | Persisted start, lookup, append-only notes, controlled disposition, close, atomic alert resolution, conflict handling, and refresh recovery are covered by PostgreSQL/API/Streamlit tests. Authentication, analyst identity/assignment, authenticated attribution, and production-grade case management are not implemented |
| Dashboard functionality | PASS LOCALLY | Rebuilt v1.2.0 Streamlit service is healthy; automated Streamlit tests verify the investigation workflow and persisted recovery. Fresh browser visual verification remains pending |
| Automated application regression | PASS | Latest complete local PostgreSQL-backed run: 95 passed, 0 failed, 0 skipped; one known Starlette/httpx TestClient deprecation warning remains |
| Lint | PASS | Repository-wide Ruff check completed successfully |
| Local Docker Compose | PASS | v1.2.0 image rebuilt from current source; migration exited 0; API, dashboard, and PostgreSQL healthy; /health reports release 1.2.0 and /ready reports schema revision 3; application restart preserved the OPEN demonstration alert |
| Hosted GitHub integration CI | PENDING FOR V1.2 | The v1.2.0 candidate has not yet completed its branch/PR-specific hosted integration gate |
| Hosted Docker Compose CI | PENDING FOR V1.2 | Fresh hosted container verification must run for the v1.2.0 candidate |
| Dependency vulnerability gate | PENDING FOR V1.2 | pip-audit remains part of hosted integration CI and requires a fresh v1.2.0 candidate run |
| CodeQL static analysis | PENDING FOR V1.2 | Earlier released baselines passed CodeQL; v1.2.0 requires commit-specific verification |
| Dependabot monitoring | ENABLED | Python, Docker, and GitHub Actions ecosystems configured |
| Repository publication | PASS | Repository is published on GitHub; latest published release is v1.1.0 while v1.2.0 remains a development candidate |
| Release evidence | PASS LOCALLY | Revision-3 migration/recovery and v1.2.0 local runtime evidence are recorded under docs/evidence |
| Browser visual verification | PENDING FOR V1.2 | Earlier dashboard views were visually inspected; the v1.2 investigation interface requires fresh browser verification |
| Accessibility review | NOT COMPLETED | No formal accessibility audit or cross-browser accessibility certification is claimed |
| Authentication/authorization | DEFERRED TO PHASE 13 | Not implemented in v1.2.0 |
| Analyst identity and assignment | DEFERRED TO PHASE 13 | Investigation records do not claim authenticated analyst identity, ownership, or assignment |
| Production load/scaling validation | OUT OF CURRENT SCOPE | No production-scale concurrency or capacity claim is made |
| Cloud/public application deployment | OUT OF CURRENT SCOPE | The repository is public; the running application is not deployed as a public production service |
| Real bank integration | OUT OF CURRENT SCOPE | No bank, payment processor, or live transaction stream is connected |
| Production financial use | NOT APPROPRIATE | Model outputs and human-review dispositions must not be used for real financial decisions |
| External penetration test | NOT COMPLETED | Automated security controls do not constitute an independent penetration test |
| Production disaster recovery | NOT COMPLETED | Local backup/restore and restart persistence are verified, but this is not production disaster-recovery validation |
| v1.0.0 release | RELEASED | Published from commit 213f0828aade73553bac953cd05b93445073e5b2 |
| v1.1.0 release | RELEASED | Product-foundation release published from merge commit 2be0125bd65c4a7974872262a7104f40078cf1d4 |
| v1.2.0 release | PENDING | Local implementation and verification gates are passing; hosted CI, CodeQL, browser verification, review/merge, and release publication remain |

## Current demonstration state

The portfolio demonstration exercises the actual application path:

```text
Input
  |
  v
FastAPI validation
  |
  v
Frozen model inference
  |
  v
Decision threshold
  |
  v
PostgreSQL persistence
  |
  +----> persisted alert when review criteria are met
  |          |
  |          v
  |      Human investigation
  |          |
  |          +----> append-only notes
  |          |
  |          +----> controlled human-review disposition
  |          |
  |          +----> close investigation + resolve alert atomically
  |
  v
Streamlit analytics and investigation workflow
```

Investigation dispositions are **human review outcomes**, not model labels or independently established fraud ground truth. The preserved local demonstration state contains one OPEN synthetic alert with no investigation so the v1.2 investigation workflow remains available for browser demonstration.
