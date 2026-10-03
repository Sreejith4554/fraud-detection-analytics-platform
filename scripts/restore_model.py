"""Restore the selected model from verified training data.

An existing canonical artifact must match its frozen SHA-256 exactly.
A rebuilt artifact is accepted only when its learned numerical state matches
the independently captured fingerprint of the canonical frozen artifact.
"""

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from model.train import digest, load_partition

MANIFEST_PATH = Path("docs/evidence/model-selection.json")
RECONSTRUCTION_PATH = Path("docs/evidence/model-reconstruction.json")
DESTINATION = Path("artifacts/model.joblib")


def build_model():
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=42,
        ),
    )


def verify_reconstruction(model, manifest, reference):
    if reference["source_model_sha256"] != manifest["model_sha256"]:
        raise ValueError("Reconstruction reference does not match frozen model")
    if reference["selected_model"] != manifest["selected_model"]:
        raise ValueError("Reconstruction reference model mismatch")

    verification = reference["verification"]
    rtol = verification["rtol"]
    atol = verification["atol"]

    scaler, logistic = model[0], model[1]

    checks = (
        ("scaler mean", scaler.mean_, reference["mean"]),
        ("scaler scale", scaler.scale_, reference["scale"]),
        ("coefficients", logistic.coef_, reference["coef"]),
        ("intercept", logistic.intercept_, reference["intercept"]),
    )

    for name, actual, expected in checks:
        if not np.allclose(
            np.asarray(actual),
            np.asarray(expected),
            rtol=rtol,
            atol=atol,
        ):
            raise ValueError(f"Rebuilt model differs: {name}")

    if not np.array_equal(logistic.classes_, np.asarray(reference["classes"])):
        raise ValueError("Rebuilt model differs: classes")
    if not np.array_equal(logistic.n_iter_, np.asarray(reference["n_iter"])):
        raise ValueError("Rebuilt model differs: iteration count")


def main():
    manifest = json.loads(MANIFEST_PATH.read_text())

    if DESTINATION.exists():
        if digest(DESTINATION) != manifest["model_sha256"]:
            raise ValueError("Existing model hash mismatch; investigate before replacing")
        print("Verified existing canonical artifact")
        return

    if manifest["selected_model"] != "logistic_balanced":
        raise ValueError("This restoration script supports only the frozen v1 model")

    reference = json.loads(RECONSTRUCTION_PATH.read_text())

    x, y = load_partition("train")
    model = build_model()
    model.fit(x, y)

    verify_reconstruction(model, manifest, reference)

    DESTINATION.parent.mkdir(exist_ok=True)
    temporary = DESTINATION.with_suffix(".part")
    try:
        joblib.dump(model, temporary)
        temporary.replace(DESTINATION)
    finally:
        temporary.unlink(missing_ok=True)

    print(
        "Restored model; canonical numerical fingerprint matched; "
        "test set not read"
    )


if __name__ == "__main__":
    main()
