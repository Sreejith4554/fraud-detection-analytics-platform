"""Two-stage real HTTP persistence verification across an external DB restart."""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import joblib
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["seed", "verify"])
    args = parser.parse_args()
    assert os.environ.get("DATABASE_URL"), "DATABASE_URL required"
    with Path("/tmp/fraud-db-api.log").open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8766",
                "--no-access-log",
            ],
            stdout=log,
            stderr=log,
        )

        def request(path, data=None):
            req = urllib.request.Request(
                "http://127.0.0.1:8766" + path,
                data=json.dumps(data).encode() if data is not None else None,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read())

        try:
            for _ in range(100):
                try:
                    request("/ready")
                    break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError("API failed to start; inspect local log")
                    time.sleep(0.1)
            else:
                raise RuntimeError("Readiness timeout")
            evidence = Path("docs/evidence/postgresql-smoke.json")
            if args.stage == "seed":
                original = request("/predictions")["total"]
                data = json.loads(Path("examples/synthetic-transaction.json").read_text())
                ids = []
                for _ in range(99):
                    result = request("/predict", data)
                    assert result["persisted"] is True
                    ids.append(result["prediction_id"])
                model = joblib.load("artifacts/model.joblib")
                data["v"] = (np.sign(model[-1].coef_[0][1:29]) * 1000).tolist()
                high = request("/predict", data)
                assert high["risk_category"] == "HIGH" and high["alert_id"]
                ids.append(high["prediction_id"])
                assert request("/predictions")["total"] == original + 100
                report = {
                    "scope": "100 SYNTHETIC inputs; final high-risk input is an unrealistic stress vector",
                    "http_persisted": 100,
                    "initial_count": original,
                    "expected_count": original + 100,
                    "prediction_ids": ids,
                    "high_alert_id": high["alert_id"],
                    "restart_verified": False,
                }
            else:
                report = json.loads(evidence.read_text())
                history = request("/predictions?limit=100")
                assert history["total"] == report["expected_count"]
                assert set(report["prediction_ids"]).issubset({x["id"] for x in history["items"]})
                report["restart_verified"] = True
                report["readiness_after_restart"] = True
            evidence.write_text(json.dumps(report, indent=2) + "\n")
            print(args.stage, "PASS", report["expected_count"], "stored records")
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
