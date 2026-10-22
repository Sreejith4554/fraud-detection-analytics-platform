
"""Seed the isolated public demo with generated synthetic transactions only."""

import os
import random
from pathlib import Path

from sqlalchemy import text

from api.schemas import TransactionInput
from api.services.inference import InferenceService
from database.config import database_url
from database.store import Store


EXPECTED_DATABASE = "fraud_public_demo"
SEED_COUNT = 60

MODEL_PATH = Path("artifacts/model.joblib")
MANIFEST_PATH = Path("docs/evidence/model-selection.json")

# Deliberately extreme, artificial feature values to exercise the alert workflow.
# These are not realistic transactions or examples of actual fraud.
STRESS_COMPONENTS = [
    1000, 1000, 1000, 1000, 1000, -1000, -1000,
    -1000, -1000, -1000, 1000, -1000, -1000, -1000,
    -1000, -1000, -1000, -1000, 1000, -1000, 1000,
    1000, 1000, -1000, 1000, -1000, -1000, 1000,
]


def synthetic_transactions():
    """Generate reproducible artificial feature vectors without source data."""
    rng = random.Random(20261022)

    for index in range(SEED_COUNT):
        if index % 10 == 0:
            components = [float(value) for value in STRESS_COMPONENTS]
        else:
            components = [
                round(rng.gauss(0.0, 1.0), 6)
                for _ in range(28)
            ]

        yield TransactionInput(
            schema_version="1",
            source="SYNTHETIC",
            amount=round(rng.uniform(2.0, 900.0), 2),
            time=float(index * 120),
            v=components,
        )


def main():
    if os.getenv("PUBLIC_DEMO_DATABASE") != "1":
        raise RuntimeError(
            "Refusing to seed: PUBLIC_DEMO_DATABASE=1 is required"
        )

    url = database_url()
    if url is None:
        raise RuntimeError("Refusing to seed: database configuration missing")

    store = Store(url)

    try:
        # Verify the actual PostgreSQL connection, not just DB_NAME.
        with store.engine.connect() as conn:
            actual_database = conn.execute(
                text("SELECT current_database()")
            ).scalar_one()

            if actual_database != EXPECTED_DATABASE:
                raise RuntimeError(
                    "Refusing to seed: unexpected PostgreSQL database"
                )

            existing_transactions = conn.execute(
                text("SELECT COUNT(*) FROM transactions")
            ).scalar_one()

            if existing_transactions != 0:
                raise RuntimeError(
                    "Refusing to seed: transaction records already exist"
                )

        store.ready()

        inference = InferenceService(MODEL_PATH, MANIFEST_PATH)
        threshold = inference.manifest["threshold"]
        model_version = inference.manifest["model_version"]
        model_hash = inference.manifest["model_sha256"]

        high_count = 0

        for transaction in synthetic_transactions():
            score = inference.score(transaction)
            high = score >= threshold

            result = {
                "model_score": score,
                "threshold": threshold,
                "risk_category": "HIGH" if high else "LOW",
                "decision": (
                    "FLAG_FOR_REVIEW"
                    if high
                    else "NO_REVIEW_TRIGGERED"
                ),
                "model_version": model_version,
            }

            store.persist(transaction, result, model_hash)
            high_count += int(high)

        print(
            f"Seeded {SEED_COUNT} synthetic transactions "
            f"into {EXPECTED_DATABASE}; "
            f"{high_count} high-risk alerts."
        )
        print(
            "Synthetic demonstration only: "
            "scores are not evidence of actual fraud."
        )

    finally:
        store.engine.dispose()


if __name__ == "__main__":
    main()
