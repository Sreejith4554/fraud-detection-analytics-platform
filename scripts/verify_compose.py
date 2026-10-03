"""Run only on a Docker-capable host after `docker compose up --build -d --wait`."""

import json
import subprocess
import time
import urllib.request
from pathlib import Path


def request(path, payload=None):
    req = urllib.request.Request(
        "http://127.0.0.1:8000" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())


def main():
    assert request("/ready")["prediction_ready"]
    initial = request("/analytics")["total_predictions"]
    payload = json.loads(Path("examples/synthetic-transaction.json").read_text())
    result = request("/predict", payload)
    assert result["persisted"] is True
    assert request("/analytics")["total_predictions"] == initial + 1
    with urllib.request.urlopen("http://127.0.0.1:8501/_stcore/health", timeout=10) as response:
        assert response.status == 200
    subprocess.run(["docker", "compose", "restart", "db"], check=True)
    for _ in range(30):
        try:
            assert request("/ready")["prediction_ready"]
            break
        except (OSError, AssertionError):
            time.sleep(1)
    else:
        raise RuntimeError("Readiness did not recover after database restart")
    history = request("/predictions?limit=100")
    assert result["prediction_id"] in {item["id"] for item in history["items"]}
    report = {
        "status": "PASSED",
        "method": "actual Compose HTTP checks and db container restart",
        "prediction_id": result["prediction_id"],
        "initial_count": initial,
        "final_count": request("/analytics")["total_predictions"],
        "dashboard_health": 200,
        "data_volume_preserved": True,
        "limitations": "local synthetic request; ordinary restart only; no backup recovery test",
    }
    Path("docs/evidence/compose-runtime.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Compose runtime checks PASSED; evidence written to docs/evidence/compose-runtime.json")


if __name__ == "__main__":
    main()
