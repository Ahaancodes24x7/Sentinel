"""
Sentinel Database Layer.

Production PostgreSQL integration with SQLAlchemy 2.0.
Configured via DATABASE_URL environment variable (with automatic normalization
for Render's postgres:// URLs).

Strictly enforces PostgreSQL in normal operation and disallows silent fallback to SQLite.
"""

import os
from datetime import datetime, timezone
from typing import Generator

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.types import JSON

Base = declarative_base()


def _now():
    return datetime.now(timezone.utc)


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    isolated_test = os.getenv("TEST_ISOLATED_SQLITE", "0") == "1"

    if not url:
        if isolated_test:
            return "sqlite:///:memory:"
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. Please provide a valid "
            "PostgreSQL connection string (e.g. postgresql://postgres:password@localhost:5432/sentinel_db). "
            "In accordance with Sentinel production standards, silent fallback to SQLite is disabled."
        )

    # Auto-normalize Render connection strings
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if url.startswith("sqlite") and not isolated_test:
        raise RuntimeError(
            "SQLite connection specified but TEST_ISOLATED_SQLITE=1 is not set. "
            "Sentinel requires a PostgreSQL database for standard operation."
        )

    return url


from sqlalchemy.pool import StaticPool

# Create Engine
_db_url = get_database_url()
_is_sqlite = _db_url.startswith("sqlite")

_engine_kwargs = {"pool_pre_ping": True}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(_db_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# SQLAlchemy Models
# ---------------------------------------------------------------------------
class ReportModel(Base):
    __tablename__ = "reports"

    report_id = Column(String(64), primary_key=True, index=True)
    site = Column(String(128), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)
    source = Column(String(32), nullable=False, default="synthetic")
    report_text = Column(Text, nullable=False)
    sif_potential = Column(Boolean, nullable=False, default=False, index=True)
    bucket = Column(String(32), nullable=False, default="HIGH_CONF_NON_SIF", index=True)
    lsr_tag = Column(String(128), nullable=False, default="Energy Isolation", index=True)
    extracted_fields = Column(JSON, nullable=False)
    classification = Column(JSON, nullable=False)
    model_version = Column(String(64), nullable=False)
    review_status = Column(String(32), nullable=False, default="pending", index=True)
    batch_id = Column(String(64), nullable=True, index=True)

    # --- Structured event frame -------------------------------------------
    # These are denormalised out of `extracted_fields` on ingest. The pattern
    # layer clusters and mines over the STRUCTURED frame, not raw text, so it
    # needs these as first-class indexed columns; digging them out of a JSON
    # blob for every one of 25k rows on every dashboard request would be both
    # slow and unfilterable in SQL.
    activity = Column(String(256), nullable=True, index=True)
    energy_type = Column(String(128), nullable=True, index=True)
    barrier_type = Column(String(128), nullable=True, index=True)
    barrier_status = Column(String(64), nullable=True, index=True)
    barrier_failure_mode = Column(String(256), nullable=True)
    exposure = Column(String(64), nullable=True, index=True)
    magnitude_class = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    is_high_energy = Column(Boolean, nullable=True, index=True)
    reporter_role = Column(String(64), nullable=True)
    cluster_id = Column(String(64), nullable=True, index=True)

    review_actions = relationship(
        "ReviewActionModel",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReviewActionModel.created_at",
    )


class BatchTrackerModel(Base):
    __tablename__ = "batch_tracker"

    batch_id = Column(String(64), primary_key=True, index=True)
    total = Column(Integer, nullable=False, default=0)
    classified = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="processing")  # processing | complete | failed
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class ReviewActionModel(Base):
    __tablename__ = "review_actions"

    review_action_id = Column(String(64), primary_key=True, index=True)
    report_id = Column(String(64), ForeignKey("reports.report_id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_username = Column(String(128), nullable=False)
    action = Column(String(32), nullable=False)  # confirm | correct | reject
    corrected_sif_potential = Column(Boolean, nullable=True)
    corrected_lsr_tag = Column(String(128), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)

    report = relationship("ReportModel", back_populates="review_actions")


class ActionPlanModel(Base):
    __tablename__ = "action_plans"

    action_plan_id = Column(String(64), primary_key=True, index=True)
    pattern_id = Column(String(64), nullable=False, index=True)
    selected_interventions = Column(JSON, nullable=False)
    target_sites = Column(JSON, nullable=False)
    planned_start_date = Column(Date, nullable=False)
    actual_start_date = Column(Date, nullable=True)
    status = Column(String(32), nullable=False, default="planned")  # planned | in_progress | complete
    created_by = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class PrecursorClusterModel(Base):
    """Output of the batch clustering job (AI/ML Stage 4).

    Clustering 25k structured frames takes seconds, not milliseconds, so it is
    computed by a batch job and read from here — matching the batch-first
    deployment posture the blueprint recommends, rather than pretending the
    dashboard recomputes it live on every page load.
    """

    __tablename__ = "precursor_clusters"

    cluster_id = Column(String(64), primary_key=True, index=True)
    pattern_summary = Column(Text, nullable=False)
    member_report_ids = Column(JSON, nullable=False)
    member_count = Column(Integer, nullable=False, default=0)
    sites = Column(JSON, nullable=False)
    site_count = Column(Integer, nullable=False, default=0)
    primary_lsr = Column(String(128), nullable=False, default="N/A")
    primary_barrier_failure = Column(String(256), nullable=True)
    barrier_type = Column(String(128), nullable=True)
    pattern_type = Column(String(48), nullable=False, default="established")
    sif_member_count = Column(Integer, nullable=False, default=0)
    sif_share = Column(Float, nullable=False, default=0.0)
    mean_magnitude = Column(Float, nullable=False, default=0.0)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    edges = Column(JSON, nullable=True)
    computed_at = Column(DateTime(timezone=True), nullable=False, default=_now)


class VisionEventModel(Base):
    """Durable log of Live Safety Vision hazard events.

    Session-level live state (active flag, rolling people/vehicle counts,
    per-rule dedupe cooldowns) stays in-memory in
    sif_engine.vision.stream_processor - it is ephemeral by nature, like a
    CCTV system's current tally. Once a hazard rule fires, the resulting
    event is durable here, same as every other safety-relevant record in
    Sentinel.
    """

    __tablename__ = "vision_events"

    event_id = Column(String(64), primary_key=True, index=True)
    site_id = Column(String(64), nullable=False, index=True)
    camera_id = Column(String(64), nullable=False, index=True)
    camera_name = Column(String(256), nullable=True)
    event_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), nullable=False, index=True)
    confidence = Column(Float, nullable=False, default=0.0)
    objects = Column(JSON, nullable=False)
    evidence = Column(Text, nullable=False)
    roi = Column(String(128), nullable=True)
    observed = Column(Text, nullable=False)
    inference = Column(Text, nullable=False)
    sif_relevance = Column(Text, nullable=False)
    lsr_tag = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False, default="active", index=True)
    acknowledged_by = Column(String(128), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(String(64), primary_key=True, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    actor = Column(String(128), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=_now, index=True)


def init_db():
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator:
    """Dependency for obtaining an isolated DB session with cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> str:
    """Check connectivity to the database."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "connected"
    except Exception as exc:
        return f"error: {str(exc)}"
