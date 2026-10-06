"""Local demonstration dashboard backed entirely by the project HTTP API."""

import json
import os
from datetime import datetime, timezone

import httpx
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Fraud Analytics | Delivery Platform", page_icon="◈", layout="wide")
BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def call(path, payload=None):
    with httpx.Client(timeout=10) as client:
        response = (
            client.get(BASE + path) if payload is None else client.post(BASE + path, json=payload)
        )
        response.raise_for_status()
        return response.json()


st.caption("SREEJITH SIVAKUMAR  /  TECHNICAL DELIVERY PORTFOLIO")
st.title("Fraud Detection & Analytics")
st.write("Follow a demonstration transaction from model score to a persisted review alert.")
st.warning(
    "PORTFOLIO PROOF-OF-CONCEPT · Predictions must not be used for real financial decisions."
)
with st.sidebar:
    st.header("Delivery status")
    st.caption("ML → API → PostgreSQL → Analytics")
    st.button("Refresh data", width="stretch")
    st.caption("Local demonstration. No bank connection or external notifications.")
    st.caption(
        "Scores are uncalibrated. HIGH means the model threshold triggered review, not confirmed fraud."
    )
try:
    call("/ready")
    analytics = call("/analytics")
    recent = call("/predictions?limit=20")
    model = call("/model-info")
except (httpx.HTTPError, ValueError):
    st.error(
        "Service unavailable. Start the API and PostgreSQL, install the schema, and verify /ready."
    )
    st.stop()

st.caption(
    "Connected · "
    + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    + " · All persisted records"
)
columns = st.columns(4)
columns[0].metric("Transactions processed", analytics["total_predictions"])
columns[1].metric("Flagged for review", analytics["high_risk"])
columns[2].metric("Flagged share", f"{analytics['flagged_share']:.2%}")
columns[3].metric("Stored alerts", analytics["alerts"])
st.caption(
    "Flagged share is not the fraud rate. No human-reviewed ground-truth outcomes are collected."
)
overview, queue, submit, operations = st.tabs(
    ["Overview", "Review queue", "Submit demo", "Model & operations"]
)
with overview:
    left, right = st.columns(2)
    with left:
        st.subheader("Model score distribution")
        bins = analytics["score_bins"]
        histogram = pd.DataFrame(
            {
                "Score interval": [f"{b['lower']:.1f}–{b['upper']:.1f}" for b in bins],
                "Transactions": [b["count"] for b in bins],
            }
        )
        st.bar_chart(histogram, x="Score interval", y="Transactions", color="#5BD6C4")
        st.caption(
            "Intervals include their lower boundary; the last includes 1.0. Uncalibrated scores."
        )
    with right:
        st.subheader("Processed over time")
        if analytics["daily"]:
            st.bar_chart(pd.DataFrame(analytics["daily"]), x="day", y="count", color="#7BA7FF")
        else:
            st.info("No stored predictions yet. Submit a synthetic demo to begin.")
        mean = analytics["mean_model_score"]
        st.caption("Mean model score: " + (f"{mean:.6f}" if mean is not None else "No data"))
    st.subheader("Latest predictions")
    st.caption(
        f"Showing up to 20 of {recent['total']} records. KPI totals and charts cover all records."
    )
    st.dataframe(pd.DataFrame(recent["items"]), hide_index=True, width="stretch")
    st.caption("Input sources: " + json.dumps(analytics["sources"]))
with queue:
    st.subheader("Persisted review alerts")
    st.caption(
        "Demonstration investigation queue. Alerts can be marked RESOLVED, "
        "but analyst assignment, notes, authentication, and case management "
        "are not implemented."
    )
    alert_status = st.radio(
        "Alert status",
        ["OPEN", "RESOLVED"],
        horizontal=True,
    )
    offset = st.number_input("Alert offset", min_value=0, step=20, value=0)
    try:
        alerts = call(
            f"/alerts?status={alert_status}&limit=20&offset={offset}"
        )
        st.write(
            f"{alerts['total']} {alert_status.lower()} alerts total - "
            "up to 20 on this page"
        )
        if alerts["items"]:
            st.dataframe(
                pd.DataFrame(alerts["items"]),
                hide_index=True,
                width="stretch",
            )
            if alert_status == "OPEN":
                st.caption(
                    "Resolving an alert records its lifecycle state only; "
                    "it does not establish whether fraud occurred."
                )
                for alert in alerts["items"]:
                    if st.button(
                        f"Resolve alert {alert['id']}",
                        key=f"resolve-{alert['id']}",
                    ):
                        try:
                            call(f"/alerts/{alert['id']}/resolve", {})
                            st.rerun()
                        except (httpx.HTTPError, ValueError):
                            st.error(
                                "Alert resolution failed. Refresh and verify "
                                "the alert state before retrying."
                            )
        else:
            st.info(f"No {alert_status.lower()} alerts on this page.")
    except (httpx.HTTPError, ValueError):
        st.error("Alert history unavailable. Refresh after checking the API.")
with submit:
    st.subheader("Submit a synthetic transaction")
    st.caption(
        "These are numerical PCA components, not location or device inputs. Arbitrary values may be out of distribution."
    )
    with st.form("demo"):
        amount = st.number_input("Amount", min_value=0.0, value=12.5)
        elapsed = st.number_input("Elapsed seconds", min_value=0.0, value=0.0)
        components = st.text_area("V1–V28 (JSON array)", value=json.dumps([0.0] * 28))
        sent = st.form_submit_button("Score and save")
    if sent:
        st.session_state.pop("last_prediction", None)
        try:
            vector = json.loads(components)
            payload = {
                "schema_version": "1",
                "source": "SYNTHETIC",
                "amount": amount,
                "time": elapsed,
                "v": vector,
            }
            st.session_state["last_prediction"] = call("/predict", payload)
            st.rerun()
        except (ValueError, httpx.HTTPError):
            st.error(
                "Submission failed. Check the 28-number array and service readiness; no success is assumed. If the response was lost, check history before retrying."
            )
    if "last_prediction" in st.session_state:
        result = st.session_state["last_prediction"]
        st.success("Saved prediction " + result["prediction_id"])
        st.json(
            {
                k: result[k]
                for k in ["model_score", "risk_category", "decision", "persisted", "alert_id"]
            }
        )
    st.divider()
    st.subheader("Alert-path stress test")
    st.warning(
        "Functional demonstration only. This uses an intentionally extreme "
        "synthetic out-of-distribution vector to exercise the model threshold, "
        "durable prediction, alert creation, and review-queue path. It is not "
        "a realistic transaction and is not evidence of real-world fraud."
    )
    st.caption(
        "The model and verified threshold are unchanged. The stress vector "
        "follows the same deterministic mechanism exercised by the PostgreSQL "
        "integration tests."
    )

    stress_vector = [
        1000.0,
        1000.0,
        1000.0,
        1000.0,
        1000.0,
        -1000.0,
        -1000.0,
        -1000.0,
        -1000.0,
        -1000.0,
        1000.0,
        -1000.0,
        -1000.0,
        -1000.0,
        -1000.0,
        -1000.0,
        -1000.0,
        -1000.0,
        1000.0,
        -1000.0,
        1000.0,
        1000.0,
        1000.0,
        -1000.0,
        1000.0,
        -1000.0,
        -1000.0,
        1000.0,
    ]

    if st.button("Run synthetic alert-path stress test"):
        st.session_state.pop("last_stress_prediction", None)
        try:
            stress_payload = {
                "schema_version": "1",
                "source": "SYNTHETIC",
                "amount": 12.5,
                "time": 0.0,
                "v": stress_vector,
            }
            st.session_state["last_stress_prediction"] = call(
                "/predict", stress_payload
            )
            st.rerun()
        except (ValueError, httpx.HTTPError):
            st.error(
                "Stress-test submission failed. No success is assumed; "
                "check prediction history before retrying."
            )

    if "last_stress_prediction" in st.session_state:
        stress_result = st.session_state["last_stress_prediction"]
        st.success(
            "Synthetic stress-test prediction saved "
            + stress_result["prediction_id"]
        )
        st.json(
            {
                k: stress_result[k]
                for k in [
                    "model_score",
                    "risk_category",
                    "decision",
                    "persisted",
                    "alert_id",
                ]
            }
        )
with operations:
    st.subheader("Model provenance")
    st.json(model)
    st.caption(
        "MBA research extension, implemented with AI assistance. Offline model results and limitations are documented in the repository."
    )
    try:
        st.json(call("/metrics"))
    except (httpx.HTTPError, ValueError):
        st.info("Operational metrics temporarily unavailable.")
