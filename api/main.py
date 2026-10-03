"""Local-only model scoring and atomic PostgreSQL prediction persistence."""

import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.schemas import PredictionResponse, ScoreResponse, TransactionInput
from api.services.inference import InferenceService
from database.config import database_url as configured_database_url
from database.store import Store

ROOT = Path(__file__).resolve().parents[1]
DISCLAIMER = "PORTFOLIO PROOF-OF-CONCEPT. Not for real financial decisions."
SCORE_NOTE = "Uncalibrated model score; not an estimate of real-world fraud certainty."
logger = logging.getLogger("fraud_api")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


def create_app(artifact=None, manifest=None, database_url=None):
    database_url = database_url if database_url is not None else configured_database_url()
    artifact = Path(artifact) if artifact is not None else ROOT / "artifacts/model.joblib"
    manifest = (
        Path(manifest) if manifest is not None else ROOT / "docs/evidence/model-selection.json"
    )

    @asynccontextmanager
    async def lifespan(application):
        application.state.inference = None
        try:
            application.state.inference = InferenceService(artifact, manifest)
        except Exception:
            # Do not leak filesystem paths, artifact contents, or raw input.
            logger.error(json.dumps({"event": "model_unavailable"}))
        application.state.store = None
        if database_url:
            try:
                application.state.store = Store(database_url)
            except Exception:
                logger.error(json.dumps({"event": "database_configuration_failed"}))
        yield
        if application.state.store:
            application.state.store.engine.dispose()
        application.state.store = None
        application.state.inference = None

    app = FastAPI(
        title="Fraud Detection & Analytics Delivery Platform",
        version="0.7.0",
        description=DISCLAIMER,
        lifespan=lifespan,
    )
    app.state.inference = None
    app.state.store = None
    app.state.requests = 0
    app.state.errors = 0
    app.state.score_count = 0
    app.state.score_duration_ms = 0.0

    @app.middleware("http")
    async def observe(request: Request, call_next):
        request_id = str(uuid4())
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            response = JSONResponse(status_code=500, content={"detail": "Internal service error"})
        app.state.requests += 1
        app.state.errors += int(response.status_code >= 400)
        response.headers["X-Request-ID"] = request_id
        # Use the registered route template, never user-controlled path/query/body.
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "request_id": request_id,
                    "route": getattr(route, "path", "unmatched"),
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            )
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        # Default validation output echoes rejected input. Return safe field locations only.
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": list(error["loc"]), "type": error["type"]} for error in exc.errors()
                ]
            },
        )

    def inference():
        service = app.state.inference
        if service is None:
            raise HTTPException(status_code=503, detail="Model unavailable")
        return service

    @app.get("/health")
    async def health():
        return {
            "status": "alive",
            "release": "0.7.0",
            "scoring_ready": app.state.inference is not None,
            "readiness_endpoint": "/ready",
        }

    def database():
        store = app.state.store
        if store is None:
            raise HTTPException(status_code=503, detail="Database unavailable")
        try:
            store.ready()
        except Exception:
            raise HTTPException(
                status_code=503, detail="Database unavailable or schema not ready"
            ) from None
        return store

    @app.get("/ready")
    async def ready():
        inference()
        database()
        return {"scoring_ready": True, "prediction_ready": True, "schema_revision": 1}

    @app.get("/model-info")
    async def model_info():
        return {**inference().info(), "score_interpretation": SCORE_NOTE, "disclaimer": DISCLAIMER}

    @app.post("/score", response_model=ScoreResponse)
    async def score(transaction: TransactionInput):
        service = inference()
        start = time.perf_counter()
        try:
            value = service.score(transaction)
        except Exception:
            logger.error(json.dumps({"event": "inference_failed"}))
            raise HTTPException(status_code=500, detail="Model inference failed") from None
        app.state.score_count += 1
        app.state.score_duration_ms += (time.perf_counter() - start) * 1000
        threshold = service.manifest["threshold"]
        high = value >= threshold
        return {
            "model_score": value,
            "risk_category": "HIGH" if high else "LOW",
            "decision": "FLAG_FOR_REVIEW" if high else "NO_REVIEW_TRIGGERED",
            "threshold": threshold,
            "model_version": service.manifest["model_version"],
            "source": transaction.source,
            "persisted": False,
            "score_interpretation": SCORE_NOTE,
            "disclaimer": DISCLAIMER,
        }

    @app.post("/predict", response_model=PredictionResponse)
    async def predict(transaction: TransactionInput):
        store = database()
        result = await score(transaction)
        try:
            return store.persist(transaction, result, inference().manifest["model_sha256"])
        except Exception:
            logger.error(json.dumps({"event": "persistence_failed"}))
            raise HTTPException(
                status_code=503, detail="Prediction could not be persisted"
            ) from None

    @app.get("/predictions")
    async def predictions(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        store = database()
        try:
            return store.history(limit, offset)
        except Exception:
            raise HTTPException(status_code=503, detail="Prediction history unavailable") from None

    @app.get("/analytics")
    async def analytics():
        store = database()
        try:
            return store.analytics()
        except Exception:
            raise HTTPException(status_code=503, detail="Analytics unavailable") from None

    @app.get("/alerts")
    async def alert_history(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        store = database()
        try:
            return store.alert_history(limit, offset)
        except Exception:
            raise HTTPException(status_code=503, detail="Alerts unavailable") from None

    @app.get("/metrics")
    async def metrics():
        count = app.state.score_count
        return {
            "scope": "process lifetime; resets on restart",
            "requests": app.state.requests,
            "errors": app.state.errors,
            "score_requests": count,
            "mean_scoring_ms": app.state.score_duration_ms / count if count else None,
        }

    return app


app = create_app()
