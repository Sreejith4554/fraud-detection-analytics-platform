import json
from pathlib import Path

import numpy as np
import pytest

import scripts.restore_model as restore_model


def write_files(tmp_path, reference):
    manifest = {
        "model_sha256": "historical-serialized-sha",
        "selected_model": "logistic_balanced",
    }

    manifest_path = tmp_path / "model-selection.json"
    reference_path = tmp_path / "model-reconstruction.json"

    manifest_path.write_text(json.dumps(manifest))
    reference_path.write_text(json.dumps(reference))

    return manifest_path, reference_path


def reference(coef=None):
    return {
        "schema_version": "1",
        "source_model_sha256": "historical-serialized-sha",
        "selected_model": "logistic_balanced",
        "verification": {
            "rtol": 1e-8,
            "atol": 1e-9,
        },
        "mean": [10.0, 20.0],
        "scale": [2.0, 4.0],
        "coef": coef or [[1.0, -2.0]],
        "intercept": [0.5],
        "classes": [0, 1],
        "n_iter": [35],
    }


class FakeScaler:
    mean_ = np.array([10.0, 20.0])
    scale_ = np.array([2.0, 4.0])


class FakeLogistic:
    coef_ = np.array([[1.0, -2.0]])
    intercept_ = np.array([0.5])
    classes_ = np.array([0, 1])
    n_iter_ = np.array([35])


class FakePipeline:
    def fit(self, x, y):
        return self

    def __getitem__(self, item):
        return FakeScaler() if item == 0 else FakeLogistic()


def test_existing_artifact_requires_exact_frozen_hash(tmp_path, monkeypatch):
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"tampered")

    manifest_path, reference_path = write_files(tmp_path, reference())

    monkeypatch.setattr(restore_model, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(restore_model, "RECONSTRUCTION_PATH", reference_path)
    monkeypatch.setattr(restore_model, "DESTINATION", artifact)

    with pytest.raises(ValueError, match="Existing model hash mismatch"):
        restore_model.main()


def test_reconstruction_verifies_model_equivalence_not_joblib_bytes(
    tmp_path, monkeypatch
):
    artifact = tmp_path / "model.joblib"
    manifest_path, reference_path = write_files(tmp_path, reference())

    monkeypatch.setattr(restore_model, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(restore_model, "RECONSTRUCTION_PATH", reference_path)
    monkeypatch.setattr(restore_model, "DESTINATION", artifact)
    monkeypatch.setattr(
        restore_model,
        "load_partition",
        lambda _: (np.zeros((2, 2)), np.array([0, 1])),
    )
    monkeypatch.setattr(restore_model, "build_model", FakePipeline)
    monkeypatch.setattr(
        restore_model.joblib,
        "dump",
        lambda model, path: Path(path).write_bytes(b"different-serialization"),
    )

    restore_model.main()

    assert artifact.exists()
    assert artifact.read_bytes() == b"different-serialization"


def test_reconstruction_rejects_numerically_different_model(
    tmp_path, monkeypatch
):
    artifact = tmp_path / "model.joblib"

    manifest_path, reference_path = write_files(
        tmp_path,
        reference(coef=[[999.0, -2.0]]),
    )

    monkeypatch.setattr(restore_model, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(restore_model, "RECONSTRUCTION_PATH", reference_path)
    monkeypatch.setattr(restore_model, "DESTINATION", artifact)
    monkeypatch.setattr(
        restore_model,
        "load_partition",
        lambda _: (np.zeros((2, 2)), np.array([0, 1])),
    )
    monkeypatch.setattr(restore_model, "build_model", FakePipeline)

    with pytest.raises(ValueError, match="Rebuilt model differs"):
        restore_model.main()

def test_reconstruction_reads_only_train_partition(tmp_path, monkeypatch):
    artifact = tmp_path / "model.joblib"
    manifest_path, reference_path = write_files(tmp_path, reference())
    requested_partitions = []

    def load_partition(name):
        requested_partitions.append(name)
        if name != "train":
            raise AssertionError(f"Unexpected partition access: {name}")
        return np.zeros((2, 2)), np.array([0, 1])

    monkeypatch.setattr(restore_model, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(restore_model, "RECONSTRUCTION_PATH", reference_path)
    monkeypatch.setattr(restore_model, "DESTINATION", artifact)
    monkeypatch.setattr(restore_model, "load_partition", load_partition)
    monkeypatch.setattr(restore_model, "build_model", FakePipeline)
    monkeypatch.setattr(
        restore_model.joblib,
        "dump",
        lambda model, path: Path(path).write_bytes(b"reconstructed-model"),
    )

    restore_model.main()

    assert requested_partitions == ["train"]
