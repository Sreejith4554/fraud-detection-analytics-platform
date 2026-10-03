"""Load only the locally trusted, checksum-verified model at startup."""

import hashlib
import json
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

FEATURES = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]


class InferenceService:
    def __init__(self, artifact: Path, manifest_path: Path):
        manifest = json.loads(manifest_path.read_text())
        if manifest["features"] != FEATURES or manifest["schema_version"] != "1":
            raise ValueError("Unsupported feature contract")
        if manifest["sklearn"] != sklearn.__version__:
            raise ValueError("Model runtime version mismatch")
        threshold = manifest["threshold"]
        if (
            not isinstance(threshold, (int, float))
            or not math.isfinite(threshold)
            or not 0 <= threshold <= 1
        ):
            raise ValueError("Invalid operating threshold")
        with artifact.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != manifest["model_sha256"]:
                raise ValueError("Model artifact checksum mismatch")
        # Hash protects accidental corruption, not malicious replacement of BOTH files.
        # Never allow requests to supply this path or upload pickle/joblib artifacts.
        model = joblib.load(artifact)
        if list(model.feature_names_in_) != FEATURES or list(model.classes_) != [0, 1]:
            raise ValueError("Artifact schema or class mapping mismatch")
        self.model, self.manifest = model, manifest

    def score(self, transaction):
        frame = pd.DataFrame(
            [[transaction.time, *transaction.v, transaction.amount]], columns=FEATURES
        )
        result = np.asarray(self.model.predict_proba(frame))
        if result.shape != (1, 2) or not np.isfinite(result).all():
            raise ValueError("Invalid model output")
        score = float(result[0, 1])
        if not 0 <= score <= 1:
            raise ValueError("Model output outside probability range")
        return score

    def info(self):
        return {
            k: self.manifest[k]
            for k in [
                "model_version",
                "selected_model",
                "schema_version",
                "features",
                "threshold",
                "model_sha256",
                "sklearn",
            ]
        }
