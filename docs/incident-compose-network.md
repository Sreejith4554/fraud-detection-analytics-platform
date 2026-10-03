# Local Compose startup incident — user-reported actual event
Reported 3 October 2026. Not a controlled simulation and not a production outage.

Impact: local API readiness remained 503 and dashboard startup was delayed. First a host port 8000 conflict prevented API creation. After retry, the API container was running but was not attached to fraud-platform_default; the db hostname could not resolve.

Recovery reported by Sreejith: remove/recreate the broken API container, confirm network membership alongside PostgreSQL, confirm API health, start dashboard, execute verify_compose.py, and check final compose ps. Migration reported schema revision 1 installed/verified. API, dashboard and database ended healthy. The verifier's database restart check also passed.

Evidence: exact successful command output and final service states supplied in the conversation; captured in docs/evidence/user-compose-verification.json. The original docs/evidence/compose-runtime.json remains on the user's machine and has not been received in this workspace. No prediction identifiers, durations or image digests are invented.

Diagnosis boundary: missing network membership explains failed db-name resolution. Why the container was left detached after the initial conflict was not established; do not claim a Docker defect or application root cause without daemon/network inspection evidence.

Corrective controls: check host port availability; distinguish running from ready; inspect Compose network membership when DNS fails; recreate only the affected demo container; verify health and persistence afterwards. Do not delete the database volume to solve a network issue. Clean-run CI now tests the deployment path independently when authorized.

I02 container-execution blocker: RESOLVED for the user's local Compose gate. The managed assistant environment restriction remains historical context, not an unresolved project runtime gate. Hosted CI and cloud deployment are separate pending gates.
