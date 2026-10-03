"""Start real servers; verify transport and AppTest elements against persisted demo data."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
from streamlit.testing.v1 import AppTest


def main():
    assert os.getenv("DATABASE_URL"), "DATABASE_URL required"
    os.environ["API_BASE_URL"] = "http://127.0.0.1:8009"
    processes = []
    log = Path("/tmp/fraud-dashboard-smoke.log").open("w")
    try:
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8009",
                    "--no-access-log",
                ],
                stdout=log,
                stderr=log,
            )
        )
        processes.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    "dashboard/app.py",
                    "--server.port",
                    "8510",
                    "--server.headless",
                    "true",
                ],
                stdout=log,
                stderr=log,
            )
        )
        for endpoint in ["http://127.0.0.1:8009/ready", "http://127.0.0.1:8510/_stcore/health"]:
            for _ in range(100):
                try:
                    if httpx.get(endpoint, timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError("Server startup failure; inspect local smoke log")
                time.sleep(0.1)
            else:
                raise RuntimeError("Readiness timeout")
        assert httpx.get("http://127.0.0.1:8510", timeout=5).status_code == 200
        summary = httpx.get("http://127.0.0.1:8009/analytics", timeout=5).json()
        ui = AppTest.from_file(Path("dashboard/app.py").resolve(), default_timeout=20).run()
        assert not ui.exception
        assert ui.metric[0].value == str(summary["total_predictions"])
        assert ui.metric[1].value == str(summary["high_risk"])
        assert ui.metric[3].value == str(summary["alerts"])
        result = {
            "api_ready_status": 200,
            "streamlit_health_status": 200,
            "streamlit_root_status": 200,
            "title": ui.title[0].value,
            "metrics": {m.label: m.value for m in ui.metric},
            "api_total": summary["total_predictions"],
            "api_alerts": summary["alerts"],
            "app_exceptions": 0,
            "backend": "real HTTP API and PostgreSQL",
            "visual_screenshot_review": False,
            "test_type": "AppTest functional widget verification, not browser pixels",
        }
        Path("docs/evidence/dashboard-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
