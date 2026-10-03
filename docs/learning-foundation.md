# TPM learning: discovery, architecture and first executable boundary
## API contract
What: agreed request/response shape. Why: components need the same feature names, ordering and types. Here: a provisional versioned numerical request with 28 components. Failure: a changed feature order can produce plausible but wrong scores. TPM concern: assign contract ownership and coordinate downstream impact before changing it.
Interview question: “How would you manage a model input change?”
Credible answer: “In this AI-assisted portfolio project I documented a versioned input contract. I would identify affected validation, training, inference and dashboard components, update acceptance tests, and block release until those components agree.”

## Liveness versus readiness
What: process running versus able to fulfil its purpose. Why: a web server can run while its model/database are missing. Here: health returns 200 while readiness returns 503. Failure: routing traffic based only on liveness produces failed predictions. TPM concern: release criteria must test dependencies, not just a green landing page.
Interview question: “Can a healthy service still be unusable?”
Credible answer: “Yes. Our foundation starts and exposes OpenAPI, but deliberately reports not ready because model and persistence are not integrated.”

## Validation versus test evaluation
What: validation supports model/threshold choices; test data estimates performance after those choices. Why: repeatedly choosing on the test set contaminates evaluation. Here: a chronological split and validation-only threshold decision are planned. Failure: inflated results due to leakage or test-driven tuning. TPM concern: ask for split evidence, assumptions and a frozen decision before final evaluation. This is designed, not yet implemented.

## Git branch and release evidence
What: a branch isolates changes; a commit identifies an actual source snapshot. Why: milestones and failures need traceability. Here: a design commit followed by a service-foundation branch. No GitHub PR or hosted CI run has occurred. Failure: presenting local checks as remote CI or inventing peer approval. TPM concern: distinguish implemented, tested, simulated and planned.

## Knowledge checks
Phase 0:
1. Why is this project an extension of the dissertation rather than evidence that the dissertation built an ML service?
2. Why should five workstreams not be described as five developers managed?
3. What would you need before turning a source-document performance claim into a claim about this project?

Phase 1:
1. Why must the API agree with the trained model’s feature order?
2. Why should successful inference followed by a failed database write not return success?
3. Why select the threshold on validation data rather than the final test set?
4. What does /health=200 with /ready=503 tell you?
5. Why is the share flagged for review not a measured fraud rate?

Answers pending. These questions check understanding; they are not a request for permission to develop.
