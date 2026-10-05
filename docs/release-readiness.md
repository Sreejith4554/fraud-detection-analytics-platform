# Current release readiness — 5 October 2026

**Working, tested portfolio proof-of-concept. Not a production banking system.**

This document records the current release state. Historical phase documents preserve the evidence and limitations that applied at earlier milestones.

## Current release gates

| Gate | Status | Evidence / limitation |
| --- | --- | --- |
| Data and offline model | PASS | Validated dataset pipeline, frozen model decision, held-out evaluation, checksums, and reproducibility evidence |
| Model artifact integrity | PASS | Canonical runtime artifact verified by exact SHA-256; reconstruction separately verified against numerical fingerprint |
| API and PostgreSQL | PASS | Real inference, persistence, transactional alerts, rollback behavior, analytics, and history verified |
| Dashboard functionality | PASS | API-backed Streamlit application verified with persisted analytics, synthetic submission, and read-only review queue |
| Automated application regression | PASS | Latest complete local PostgreSQL-backed run: 70 passed, 0 failed, 0 skipped |
| Local Docker Compose | PASS | API, dashboard, PostgreSQL, migration, health checks, persistence, and restart verification completed |
| Hosted GitHub integration CI | PASS | Verified portfolio build completed successfully for current application commit `11cb733ca0162c6f6ae5557c530b04f39b3f56e7` |
| Hosted Docker Compose CI | PASS | Container stage built and launched the stack, verified persistence/restart behavior, and collected runtime evidence |
| Dependency vulnerability gate | PASS | `pip-audit` is part of the verified hosted integration gate |
| CodeQL static analysis | PASS | Python CodeQL security analysis completed successfully for the current application commit, including the scheduled 5 October 2026 run |
| Dependabot monitoring | ENABLED | Python, Docker, and GitHub Actions ecosystems configured |
| Repository publication | PASS | Repository is published on GitHub and current `main` contains the verified application implementation |
| Compose evidence | PASS | Runtime evidence is present under `docs/evidence`, including Compose verification records |
| Browser visual verification | PASS | Operational overview and persisted review-alert views visually inspected and captured under `docs/images` |
| Accessibility review | NOT COMPLETED | No formal accessibility audit or cross-browser accessibility certification is claimed |
| Authentication/authorization | OUT OF V1 SCOPE | Not implemented |
| Human investigation/case management | OUT OF V1 SCOPE | Review queue is read-only; acknowledgement, assignment, disposition, and analyst audit history are not implemented |
| Production load/scaling validation | OUT OF V1 SCOPE | Local synthetic HTTP timing exists, but no production-scale concurrency or capacity claim is made |
| Cloud/public application deployment | OUT OF V1 SCOPE | GitHub repository is public; the running application itself is not deployed as a public production service |
| Real bank integration | OUT OF V1 SCOPE | No bank, payment processor, or live transaction stream is connected |
| Production financial use | NOT APPROPRIATE | Model outputs must not be used for real financial decisions |
| External penetration test | NOT COMPLETED | Automated security controls do not constitute an independent penetration test |
| Production disaster recovery | NOT COMPLETED | Database restart persistence is verified; production backup/restore and disaster recovery are not |
| v1.0.0 release | PENDING | Final documentation synchronization, recruiter-facing repository review, final green verification, and release/tag creation remain |

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
  |
  v
Streamlit analytics and review views
