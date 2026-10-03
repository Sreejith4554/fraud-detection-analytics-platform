# Proposed architecture — not yet integrated
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
 Decision --> Repo[Atomic persistence service]
 Repo --> DB[(PostgreSQL)]
 API --> Logs[JSON logs and metrics]
 UI --> Read[API history and aggregates]
 Read --> DB
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
Current implementation: health/readiness and validation scaffold, data pipeline and offline trained model. API-to-model scoring is tested via /score; PostgreSQL persistence via /predict and conditional alert recording are tested. Dashboard consumes real API analytics/history/alerts; hosted deployment remains proposed. Hosted path requires separate approval. The training pipeline runs offline, never in a prediction request. Proposed database tables: transactions(id UUID, source, schema_version, time, amount, components, created_at); predictions(id UUID, transaction_id FK, probability CHECK 0..1, threshold, risk, decision, model_version, created_at); alerts(id UUID, prediction_id UNIQUE FK, status, created_at). Model metadata is a versioned JSON manifest initially; a separate model registry service is unnecessary.
