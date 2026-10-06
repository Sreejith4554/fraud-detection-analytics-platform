# Current release readiness — 6 October 2026

**Working, tested portfolio proof-of-concept. Not a production banking system.**

This document records the current release state. Historical phase documents preserve the evidence and limitations that applied at earlier milestones.

## Current release gates

| Gate | Status | Evidence / limitation |
| --- | --- | --- |
| Data and offline model | PASS | Validated dataset pipeline, frozen model decision, held-out evaluation, checksums, and reproducibility evidence |
| Model artifact integrity | PASS | Canonical runtime artifact verified by exact SHA-256; reconstruction separately verified against numerical fingerprint |
| API and PostgreSQL | PASS | Real inference, persistence, transactional alerts, rollback behavior, analytics, and history verified |
| Dashboard functionality | PASS | API-backed Streamlit application verified with persisted analytics, synthetic submission, OPEN/RESOLVED alert filtering, and API-backed alert resolution |
| Automated application regression | PASS | Latest complete local PostgreSQL-backed run: 81 passed, 0 failed, 0 skipped |
| Local Docker Compose | PASS | API, dashboard, PostgreSQL, migration, health checks, persistence, and restart verification completed |
| Hosted GitHub integration CI | PASS | Verified portfolio build #22 completed successfully for development commit `61fd9bdcaa94da7f08bb752ace06f25bf1d7cff0` |
| Hosted Docker Compose CI | PASS | Container stage built and launched the stack, verified persistence/restart behavior, and collected runtime evidence |
| Dependency vulnerability gate | PASS | `pip-audit` is part of the verified hosted integration gate |
| CodeQL static analysis | PASS ON RELEASED BASELINE | Python CodeQL security analysis passed for the released v1.0.0 baseline; the current feature branch will receive its commit-specific CodeQL gate when proposed to `main` |
| Dependabot monitoring | ENABLED | Python, Docker, and GitHub Actions ecosystems configured |
| Repository publication | PASS | Repository is published on GitHub and current `main` contains the verified application implementation |
| Compose evidence | PASS | Runtime evidence is present under `docs/evidence`, including Compose verification records |
| Browser visual verification | PASS | Operational overview and persisted review-alert views visually inspected and captured under `docs/images` |
| Accessibility review | NOT COMPLETED | No formal accessibility audit or cross-browser accessibility certification is claimed |
| Authentication/authorization | OUT OF V1 SCOPE | Not implemented |
| Human investigation/case management | PARTIAL FOUNDATION | Basic OPEN → RESOLVED alert lifecycle is implemented; analyst assignment, investigation notes, richer disposition, authentication, and analyst audit history are not implemented |
| Production load/scaling validation | OUT OF V1 SCOPE | Local synthetic HTTP timing exists, but no production-scale concurrency or capacity claim is made |
| Cloud/public application deployment | OUT OF V1 SCOPE | GitHub repository is public; the running application itself is not deployed as a public production service |
| Real bank integration | OUT OF V1 SCOPE | No bank, payment processor, or live transaction stream is connected |
| Production financial use | NOT APPROPRIATE | Model outputs must not be used for real financial decisions |
| External penetration test | NOT COMPLETED | Automated security controls do not constitute an independent penetration test |
| Production disaster recovery | NOT COMPLETED | Database restart persistence is verified; production backup/restore and disaster recovery are not |
| v1.0.0 release | RELEASED | Verified portfolio baseline published from commit `213f0828aade73553bac953cd05b93445073e5b2`; later product-foundation work remains unreleased development |

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
```
