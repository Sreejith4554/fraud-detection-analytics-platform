"""Actual localhost smoke/latency check with clearly synthetic inputs."""

import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np


def main():
    payload = Path("examples/synthetic-transaction.json").read_bytes()
    log = Path("/tmp/fraud-phase5-server.log").open("w")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
            "--no-access-log",
        ],
        stdout=log,
        stderr=log,
    )
    base = "http://127.0.0.1:8765"

    def get(path, data=None):
        request = urllib.request.Request(
            base + path, data=data, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    try:
        for _ in range(100):
            try:
                status, health = get("/health")
                assert status == 200 and health["scoring_ready"]
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError("Server failed; inspect local server log")
                time.sleep(0.1)
        else:
            raise RuntimeError("Server startup timeout")
        status, first = get("/score", payload)
        assert status == 200 and first["persisted"] is False
        times = []
        for _ in range(100):
            start = time.perf_counter()
            status, result = get("/score", payload)
            times.append((time.perf_counter() - start) * 1000)
            assert status == 200 and result["model_score"] == first["model_score"]
        status, _ = get("/score", b"{}")
        assert status == 422
        status, _ = get("/predict", payload)
        assert status == 503
        status, _ = get("/ready")
        assert status == 503
        status, metrics = get("/metrics")
        assert status == 200
        assert metrics["score_requests"] == 101
        report = {
            "scope": "local sequential HTTP SYNTHETIC score previews; zero database writes",
            "requests_measured": 100,
            "concurrency": 1,
            "warmup_requests": 1,
            "p50_ms": float(np.percentile(times, 50)),
            "p95_ms": float(np.percentile(times, 95)),
            "max_ms": max(times),
            "example_response": first,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "invalid_input_status": 422,
            "durable_prediction_status": 503,
            "readiness_status": 503,
            "metrics": metrics,
        }
        Path("docs/evidence/api-smoke.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    finally:
        process.terminate()
        process.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
