"""Populate the local portfolio dashboard with deterministic dataset replays.

Rows are taken sequentially from the validation partition. The ground-truth
Class column is deliberately ignored so demo selection cannot be influenced by
the known outcome. Each row is submitted through the real durable /predict API
and therefore exercises model inference, persistence, and alert creation.

This utility is for local portfolio demonstration only.
"""

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

DEFAULT_API = "http://127.0.0.1:8000"
DEFAULT_DATA = Path("data/processed/validation.csv")


def post_json(url, payload):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"POST {url} failed with HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


def main():
    parser = argparse.ArgumentParser(
        description="Replay deterministic validation rows through /predict."
    )
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of sequential validation rows to replay (default: 100).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Zero-based validation-row offset (default: 0).",
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API,
        help=f"API base URL (default: {DEFAULT_API}).",
    )
    args = parser.parse_args()

    if args.count < 1:
        raise SystemExit("--count must be at least 1")
    if args.offset < 0:
        raise SystemExit("--offset must be non-negative")
    if not DEFAULT_DATA.is_file():
        raise SystemExit(f"Validation data not found: {DEFAULT_DATA}")

    frame = pd.read_csv(DEFAULT_DATA)

    required = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise SystemExit(f"Validation data is missing columns: {missing}")

    selected = frame.iloc[args.offset : args.offset + args.count]
    if selected.empty:
        raise SystemExit("Requested row range contains no validation records.")

    if len(selected) != args.count:
        raise SystemExit(
            f"Requested {args.count} rows but only {len(selected)} are available "
            f"from offset {args.offset}."
        )

    results = []

    for row_number, (_, row) in enumerate(selected.iterrows(), start=1):
        payload = {
            "schema_version": "1",
            "source": "DATASET_REPLAY",
            "amount": float(row["Amount"]),
            "time": float(row["Time"]),
            "v": [float(row[f"V{i}"]) for i in range(1, 29)],
        }

        status, result = post_json(f"{args.api.rstrip('/')}/predict", payload)

        if status != 200:
            raise RuntimeError(
                f"Unexpected HTTP status for replay row {row_number}: {status}"
            )
        if result.get("persisted") is not True:
            raise RuntimeError(
                f"Replay row {row_number} was not confirmed as persisted."
            )

        results.append(result)

    flagged = [
        result
        for result in results
        if result["decision"] == "FLAG_FOR_REVIEW"
    ]
    alert_count = sum(result["alert_id"] is not None for result in results)
    scores = [float(result["model_score"]) for result in results]

    summary = {
        "source": "DATASET_REPLAY",
        "selection": {
            "partition": str(DEFAULT_DATA),
            "offset": args.offset,
            "count": len(results),
            "ground_truth_used_for_selection": False,
        },
        "persisted": len(results),
        "flagged_for_review": len(flagged),
        "alerts_created": alert_count,
        "minimum_model_score": min(scores),
        "maximum_model_score": max(scores),
        "average_model_score": sum(scores) / len(scores),
        "thresholds_observed": sorted(
            {float(result["threshold"]) for result in results}
        ),
        "model_versions_observed": sorted(
            {result["model_version"] for result in results}
        ),
    }

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
