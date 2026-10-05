# Phases 8–9 checkpoint — test regression and container preparation
**Container runtime gate PASSED on the user’s local machine, as reported on 3 October 2026.**

The local Compose runtime was subsequently verified successfully, and runtime evidence is now retained under docs/evidence. Earlier managed-runtime failures below are preserved as historical troubleshooting evidence. See [release readiness](release-readiness.md) for the authoritative current status.

## What is implemented
Dockerfile: Python 3.12 slim Debian base; pinned Python dependencies; trusted model and manifest included; non-root application user. One shared image serves API, dashboard and an explicit one-shot schema installer. This avoids separate image maintenance for a small Python POC, at the cost of a larger shared image containing both UI and backend dependencies.

Compose: PostgreSQL with named volume → successful schema installer → API readiness → dashboard. Dependencies use health and completion conditions, not just process-start order. API/dashboard ports bind to host loopback; PostgreSQL publishes no host port. Dashboard receives only API_BASE_URL and no database secret. Application containers request read-only filesystems, temporary /tmp and no-new-privileges.

A generated local password is mounted through Compose secrets, never embedded in the image or tracked source. The host `.secrets` directory is owner-private; its password file is readable inside the non-root container via the mount. This is a local file-based secret, not an encrypted external secret manager. The database role remains a local demo owner; a restricted runtime role and separate migration role are future deployment controls.

## Historical assistant-environment verification (superseded by the user’s local pass)
- Docker CLI installed: 29.1.3; Compose 2.40.3.
- `docker compose config --quiet`: PASS.
- Resolved topology checks: four services, no published DB port, loopback app ports, migration completion dependency, no DB secret on dashboard: PASS.
- Secret file excluded by Git: PASS. Build context uses an explicit allowlist that omits credentials, datasets, Git history and source documents; image-content verification still needs a successful build.
- 61 Python tests PASS against the actual local model/PostgreSQL stack; lint PASS. Three added tests cover secret-file credentials, safe URL handling and configuration precedence. The regression suite includes API, data, model, persistence and dashboard functionality.
- Docker daemon: FAILED to start. Exact failure class: cannot create bridge networking/NAT rules; iptables permission denied in the managed runtime.
- `docker ... compose build`: BLOCKED because no daemon is running. No image was built.
- Compose startup, container health, volume restart and non-root runtime compatibility: NOT EXECUTED.

This is an execution-environment restriction, not a passing build or evidence that the application is defective. No security boundary was disabled to force a pass. No remote host was provisioned, account changed or money spent.

## Reproduction commands for a new environment (already passed on the user’s machine)
The milestone ZIP contains the trusted model. With Docker Desktop/Engine running and Python 3 available, change into the extracted `fraud-detection-analytics-platform` directory and run:

```bash
python scripts/prepare_compose.py
docker compose up --build -d --wait
python scripts/verify_compose.py
```
On systems where Python 3 is named python3, use that command. Preparation and verification use only the Python standard library, so no host pip install is required for these commands. Preparation refuses a mismatched model and does not print the generated password. Ports 8000 and 8501 must be free. Docker requires internet access for base images and pinned Python dependencies.

After successful startup: http://127.0.0.1:8501 is the dashboard; http://127.0.0.1:8000/docs is OpenAPI. The verifier submits one SYNTHETIC transaction, checks aggregates and dashboard health, restarts only the Compose database, and checks the prediction remains available. It writes `docs/evidence/compose-runtime.json` only after every assertion passes. Run it without concurrent demo traffic.

The verifier itself is prepared, not executed in this environment. A passing configuration check does not prove that dependency installation, image tags, read-only container permissions or health checks work. The user subsequently supplied the actual pass output and final health states; the local gate is now PASSED on that basis. Receiving the original JSON is an evidence-import task, not a demand to repeat verification.

Stop with `docker compose down` (keeps the named database volume). Do not add `--volumes` unless intentionally deleting demonstration history. Preserve the generated password when reusing the volume; regenerating it does not change the existing PostgreSQL role password. Base tags are not yet digest-locked; capture successful image digests at the first verified build.

## Release controls and delivery decision
I02 — RESOLVED for the local project checkpoint. The user ran the packaged verification successfully after fixing a port conflict and an unattached API container. Preserve the original runtime JSON on the user machine. The assistant environment's historical permissions restriction does not invalidate that pass.

No-Go remains for a failed future clean build, failed health checks, lost records or exposed secrets. Hosted CI, public publication and deployment retain their separate pending gates; none is inferred from the local pass.

## References
Docker startup-order documentation: https://docs.docker.com/compose/how-tos/startup-order/
Docker Compose secrets: https://docs.docker.com/compose/how-tos/use-secrets/
Checked 3 October 2026. These support configuration decisions, not a claim of runtime success.

## TPM knowledge check
1. Why does valid Compose configuration not prove the containers will run?
2. Why must the API wait for both database health and migration success?
3. What is lost if a database volume is deleted, versus a container restarted?
4. How would you report this blocker without marking the release complete?
