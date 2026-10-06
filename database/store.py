"""Single-transaction prediction storage and bounded history queries."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database.schema_version import LATEST_SCHEMA_REVISION

metadata = MetaData()
revision = Table("schema_revision", metadata, Column("version", Integer, primary_key=True))
transactions = Table(
    "transactions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("source", String(30), nullable=False),
    Column("schema_version", String(10), nullable=False),
    Column("amount", Float, nullable=False),
    Column("elapsed_seconds", Float, nullable=False),
    Column("components", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("source IN ('SYNTHETIC','DATASET_REPLAY')"),
    CheckConstraint("amount >= 0"),
    CheckConstraint("elapsed_seconds >= 0"),
    CheckConstraint("jsonb_array_length(components) = 28"),
)
predictions = Table(
    "predictions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "transaction_id",
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=False,
        unique=True,
    ),
    Column("model_score", Float, nullable=False),
    Column("threshold", Float, nullable=False),
    Column("risk_category", String(10), nullable=False),
    Column("decision", String(30), nullable=False),
    Column("model_version", String(100), nullable=False),
    Column("model_sha256", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, index=True),
    CheckConstraint("model_score >= 0 AND model_score <= 1"),
    CheckConstraint("threshold >= 0 AND threshold <= 1"),
    CheckConstraint(
        "(model_score >= threshold AND risk_category='HIGH' AND decision='FLAG_FOR_REVIEW') OR "
        "(model_score < threshold AND risk_category='LOW' AND decision='NO_REVIEW_TRIGGERED')"
    ),
)
alerts = Table(
    "alerts",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column(
        "prediction_id",
        UUID(as_uuid=True),
        ForeignKey("predictions.id"),
        nullable=False,
        unique=True,
    ),
    Column("status", String(20), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    Column("resolved_at", DateTime(timezone=True), nullable=True),
)


def connect(url):
    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"},
    )
    if engine.dialect.name != "postgresql":
        engine.dispose()
        raise ValueError("PostgreSQL required")
    return engine


def install(engine):
    """Install or verify the latest schema; existing older schemas require migration."""
    with engine.begin() as conn:
        metadata.create_all(conn)
        versions = conn.execute(select(revision.c.version)).scalars().all()
        if not versions:
            conn.execute(insert(revision).values(version=LATEST_SCHEMA_REVISION))
        elif versions != [LATEST_SCHEMA_REVISION]:
            raise ValueError("Unsupported schema version")


def verify_schema(engine):
    """Verify the installed revision and required latest-schema columns."""
    with engine.connect() as conn:
        if conn.execute(select(revision.c.version)).scalars().all() != [LATEST_SCHEMA_REVISION]:
            raise ValueError("Schema not installed or incompatible")
        # Compile and execute zero-row selects to verify required table columns.
        for table in [transactions, predictions, alerts]:
            conn.execute(select(table).limit(0))


class Store:
    def __init__(self, url):
        self.engine = connect(url)

    def ready(self):
        verify_schema(self.engine)

    def persist(self, transaction, result, model_hash):
        now = datetime.now(timezone.utc)
        tid, pid = uuid4(), uuid4()
        alert_id = uuid4() if result["risk_category"] == "HIGH" else None
        with self.engine.begin() as conn:
            conn.execute(
                insert(transactions).values(
                    id=tid,
                    source=transaction.source,
                    schema_version=transaction.schema_version,
                    amount=transaction.amount,
                    elapsed_seconds=transaction.time,
                    components=transaction.v,
                    created_at=now,
                )
            )
            conn.execute(
                insert(predictions).values(
                    id=pid,
                    transaction_id=tid,
                    **{
                        k: result[k]
                        for k in [
                            "model_score",
                            "threshold",
                            "risk_category",
                            "decision",
                            "model_version",
                        ]
                    },
                    model_sha256=model_hash,
                    created_at=now,
                )
            )
            if alert_id:
                conn.execute(
                    insert(alerts).values(
                        id=alert_id,
                        prediction_id=pid,
                        status="OPEN",
                        created_at=now,
                        updated_at=now,
                    )
                )
        # Only return after the transaction commits successfully.
        return {
            **result,
            "persisted": True,
            "prediction_id": str(pid),
            "transaction_id": str(tid),
            "alert_id": str(alert_id) if alert_id else None,
            "created_at": now.isoformat(),
        }

    def history(self, limit, offset):
        with self.engine.connect() as conn:
            total = conn.scalar(select(func.count()).select_from(predictions))
            rows = conn.execute(
                select(predictions, transactions.c.source)
                .join(transactions)
                .order_by(predictions.c.created_at.desc(), predictions.c.id.desc())
                .limit(limit)
                .offset(offset)
            )
            items = []
            for row in rows.mappings():
                item = dict(row)
                for key in ["id", "transaction_id"]:
                    item[key] = str(item[key])
                item["created_at"] = item["created_at"].isoformat()
                items.append(item)
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    def analytics(self):
        # One repeatable-read snapshot keeps totals, categories and bins consistent.
        with self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
            total = conn.scalar(select(func.count()).select_from(predictions))
            high = conn.scalar(
                select(func.count())
                .select_from(predictions)
                .where(predictions.c.risk_category == "HIGH")
            )
            mean = conn.scalar(select(func.avg(predictions.c.model_score)))
            alert_count = conn.scalar(select(func.count()).select_from(alerts))
            bin_expr = func.least(func.floor(predictions.c.model_score * 10), 9).cast(Integer)
            bins = {
                int(k): int(v)
                for k, v in conn.execute(select(bin_expr, func.count()).group_by(bin_expr))
            }
            day = func.date_trunc("day", func.timezone("UTC", predictions.c.created_at))
            daily = [
                {"day": d.date().isoformat(), "count": int(n)}
                for d, n in conn.execute(select(day, func.count()).group_by(day).order_by(day))
            ]
            sources = {
                k: int(v)
                for k, v in conn.execute(
                    select(transactions.c.source, func.count()).group_by(transactions.c.source)
                )
            }
        return {
            "total_predictions": total,
            "high_risk": high,
            "low_risk": total - high,
            "flagged_share": high / total if total else 0.0,
            "mean_model_score": float(mean) if mean is not None else None,
            "alerts": alert_count,
            "score_bins": [
                {"lower": i / 10, "upper": (i + 1) / 10, "count": bins.get(i, 0)} for i in range(10)
            ],
            "daily": daily,
            "sources": sources,
            "scope": "All persisted predictions; UTC dates; no confirmed fraud labels",
        }

    def resolve_alert(self, alert_id):
        """Resolve an open alert; repeated resolution is idempotent."""
        now = datetime.now(timezone.utc)

        with self.engine.begin() as conn:
            row = (
                conn.execute(
                    select(alerts)
                    .where(alerts.c.id == alert_id)
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )

            if row is None:
                return None

            if row["status"] == "OPEN":
                row = (
                    conn.execute(
                        update(alerts)
                        .where(alerts.c.id == alert_id)
                        .values(
                            status="RESOLVED",
                            updated_at=now,
                            resolved_at=now,
                        )
                        .returning(alerts)
                    )
                    .mappings()
                    .one()
                )
            elif row["status"] != "RESOLVED":
                raise ValueError(f"Unsupported alert status: {row['status']}")

            item = dict(row)
            for key in ["id", "prediction_id"]:
                item[key] = str(item[key])
            for key in ["created_at", "updated_at", "resolved_at"]:
                item[key] = item[key].isoformat() if item[key] is not None else None
            return item

    def alert_history(self, limit, offset):
        with self.engine.connect() as conn:
            total = conn.scalar(select(func.count()).select_from(alerts))
            rows = conn.execute(
                select(
                    alerts,
                    predictions.c.model_score,
                    predictions.c.threshold,
                    predictions.c.model_version,
                    transactions.c.source,
                )
                .select_from(alerts.join(predictions).join(transactions))
                .order_by(alerts.c.created_at.desc(), alerts.c.id.desc())
                .limit(limit)
                .offset(offset)
            )
            items = []
            for row in rows.mappings():
                item = dict(row)
                for key in ["id", "prediction_id"]:
                    item[key] = str(item[key])
                item["created_at"] = item["created_at"].isoformat()
                item["updated_at"] = item["updated_at"].isoformat()
                item["resolved_at"] = (
                    item["resolved_at"].isoformat()
                    if item["resolved_at"] is not None
                    else None
                )
                items.append(item)
        return {"total": total, "limit": limit, "offset": offset, "items": items}
