# Platform architecture
## System context
```mermaid
flowchart TD
 Owner[Sole portfolio owner] --> Train[Offline model training]
 Reviewer[Portfolio reviewer] --> Platform[Fraud demonstration platform]
 Data[Public dataset] --> Train
 Train --> Platform
 Platform --> Evidence[Prediction and delivery evidence]
```
## Containers and components
```mermaid
flowchart TD
 UI[Streamlit dashboard] --> API[FastAPI validation and routes]
 API --> Model[Trusted scikit-learn pipeline]
 Model --> Decision[Threshold decision]
 Decision --> Repo[Transactional persistence service]
 Repo --> DB[(PostgreSQL)]
 API --> Logs[JSON logs and metrics]
 UI --> Read[API history, alerts, investigations and aggregates]
 Read --> DB
 UI --> Review[Human investigation workflow]
 Review --> API
```
## Request data flow
```mermaid
flowchart TD
 Input[Labelled demo features] --> Validate{Valid contract?}
 Validate -->|No| Reject[422 response]
 Validate -->|Yes| Score[Pipeline probability]
 Score --> Threshold[Apply frozen threshold]
 Threshold --> Commit{Commit transaction and alert?}
 Commit -->|No| Fail[Safe failure response]
 Commit -->|Yes| Success[Prediction ID and result]
 Success --> History[Dashboard refresh]
```
## Deployment proposal
```mermaid
flowchart TD
 Git[Approved source commit] --> CI[Tests and image build]
 CI --> Gate{Release gate}
 Gate -->|Pass| Images[Versioned API and dashboard images]
 Gate -->|Fail| Stop[Stop release]
 Images --> Local[Local Docker Compose]
 Local --> PG[(PostgreSQL volume)]
 Images --> Hosted[Approved hosting environment]
 Hosted --> Managed[(Managed PostgreSQL)]
```
Current implementation: health/readiness and validation, offline model training, API-to-model scoring, transactional PostgreSQL persistence, conditional alert creation, and the human investigation workflow are implemented and tested. The Streamlit dashboard consumes API-backed analytics, prediction history, alerts, and persisted investigations. The training pipeline runs offline and never executes inside a prediction request.

The implemented PostgreSQL schema is revision 3. It contains transactions, predictions, alerts, investigations, and investigation_notes. Each alert can have at most one investigation. Investigation notes are append-only. Closing an investigation records a controlled disposition (CONFIRMED_FRAUD, FALSE_POSITIVE, or INCONCLUSIVE) and resolves the associated alert atomically. Direct alert resolution is rejected while an investigation is active.

Investigation dispositions are human review outcomes in this portfolio proof-of-concept. They are not model labels and are not treated as independently established ground truth. Authentication, analyst identity, and assignment are not implemented in Phase 12 and are deferred to the authentication and RBAC phase.

Schema migrations are versioned and transactional, and application readiness requires the expected schema revision. Model metadata remains a versioned JSON manifest; a separate model registry service is unnecessary for this proof-of-concept.

Local Docker Compose deployment is implemented. Hosted deployment remains proposed and requires separate approval.
