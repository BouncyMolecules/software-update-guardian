"""Persistence and audit trail — SQLModel + SQLite with immutable classification rows."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pydantic import TypeAdapter
from sqlalchemy import desc, event
from sqlalchemy.engine import Engine, make_url
from sqlmodel import Session, SQLModel, create_engine, select

from update_guardian.config import Settings, get_settings
from update_guardian.core.models import (
    AssessmentInput,
    AuditAction,
    AuditTrailEntry,
    AuditTrailRecord,
    ClassificationResult,
    ClassificationResultRecord,
    GuardianError,
    PersistedAssessment,
    RuleContribution,
    SoftwareUpdateRecord,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)

# Persist only structural fields — omit computed aliases on ClassificationResult (round-trip safe JSON).
_CLASSIFICATION_RESULT_JSON_INCLUDE: frozenset[str] = frozenset(
    {
        "generated_at",
        "risk_score",
        "classification",
        "contributions",
        "decision_audit_trail",
        "executive_summary",
        "recommended_next_steps",
        "disclaimer",
    }
)


class StorageError(GuardianError):
    """Raised when persistence or audit logging fails in a user-visible way."""


AuditLogEntry = AuditTrailRecord
"""Backward-compatible name for :class:`AuditTrailRecord` rows used by the Streamlit history page."""


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    url = make_url(database_url)
    if url.drivername != "sqlite":
        return
    database = url.database
    if database is None or database == ":memory:":
        return
    path = Path(database)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite(engine: Engine) -> None:
    """Apply SQLite pragmas for foreign-key enforcement and WAL durability."""

    @event.listens_for(engine, "connect")
    def _sqlite_on_connect(dbapi_connection: Any, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()


def _dump_details(details: dict[str, object]) -> str:
    return TypeAdapter(dict[str, object]).dump_json(details).decode()


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize naive timestamps to UTC for consistent auditor-facing output."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class StorageService:
    """Coordinates schema lifecycle, transactional writes, and append-only audit logging.

    All classification persistence paths insert **immutable** rows — updates and deletes are not
    exposed, aligning with typical ALCOA+ expectations for reconstructable decisions.

    Attributes:
        engine: Active SQLAlchemy engine backing this service instance.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        engine_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        _ensure_sqlite_parent_dir(self._settings.database_url)
        connect_args: dict[str, object] = {}
        if self._settings.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        if engine_factory is not None:
            engine = engine_factory(self._settings.database_url, connect_args=connect_args)
        else:
            engine = create_engine(self._settings.database_url, connect_args=connect_args)
        if make_url(self._settings.database_url).drivername == "sqlite":
            _configure_sqlite(engine)
        self._engine = engine

    @property
    def engine(self) -> Engine:
        return cast("Engine", self._engine)

    def dispose(self) -> None:
        """Close pooled connections — use when tearing down tests or replacing the engine."""
        self._engine.dispose()

    def init_db(self) -> None:
        """Create database tables and indexes if they do not already exist."""
        try:
            SQLModel.metadata.create_all(self._engine)
            logger.info("Database schema verified.")
        except Exception as exc:
            logger.debug("Database initialization failed", exc_info=True)
            raise StorageError(
                "We could not initialize the local database. Verify file permissions and disk space.",
                detail=str(exc),
            ) from exc

    def record_audit_event(
        self,
        action: AuditAction,
        *,
        entity_table: str,
        entity_id: int | None,
        details: dict[str, object],
        actor: str = "system",
        correlation_id: str | None = None,
        classification_result_id: int | None = None,
        session: Session | None = None,
    ) -> None:
        """Persist a single audit row — pass ``session`` for atomic commits with classifications.

        Args:
            action: High-level verb drawn from :class:`AuditAction`.
            entity_table: Logical table or aggregate name under audit.
            entity_id: Primary key of the affected row, when applicable.
            details: Structured payload serialized to JSON (string values recommended).
            actor: Human or service principal captured for accountability.
            correlation_id: Optional business correlation copied for indexed audit queries.
            classification_result_id: Optional FK tying the event to a classification row.
            session: Existing SQLModel session; when omitted, a short-lived session commits alone.

        Raises:
            StorageError: If the database rejects the insert.
        """
        payload = AuditTrailRecord(
            action=action.value,
            entity_table=entity_table,
            entity_id=entity_id,
            correlation_id=correlation_id,
            classification_result_id=classification_result_id,
            actor=actor,
            details=_dump_details(details),
        )
        try:
            if session is not None:
                session.add(payload)
                session.flush()
            else:
                with Session(self._engine) as sess, sess.begin():
                    sess.add(payload)
        except Exception as exc:
            logger.debug("Audit log write failed", exc_info=True)
            raise StorageError(
                "Audit logging failed; the operation was rolled back to preserve traceability.",
                detail=str(exc),
            ) from exc

    def save_classification_result(
        self,
        *,
        correlation_id: str,
        assessment_input: AssessmentInput,
        result: ClassificationResult,
        actor: str = "interactive_user",
    ) -> PersistedAssessment:
        """Persist an immutable software-update snapshot and full classification bundle.

        Inserts a :class:`SoftwareUpdateRecord`, a :class:`ClassificationResultRecord`, and an
        audit row describing the persistence event. The stored JSON mirrors the engine outputs,
        including risk breakdown, contributions, and deterministic decision audit entries.

        Args:
            correlation_id: EU CT identifier, UDI-DI, or other durable business key for retrieval.
            assessment_input: Structured facts frozen at the time of classification.
            result: Complete :class:`ClassificationResult` from the classifier.
            actor: Principal attributed to the submission.

        Returns:
            A :class:`PersistedAssessment` view models can render without touching SQL rows.

        Raises:
            StorageError: When inputs are invalid or persistence fails.
        """
        trimmed = correlation_id.strip()
        if not trimmed:
            raise StorageError(
                "correlation_id must be a non-empty identifier.",
                detail="empty correlation_id",
            )

        contributions_dump = TypeAdapter(list[RuleContribution]).dump_json(result.contributions).decode()
        trail_dump = TypeAdapter(list[AuditTrailEntry]).dump_json(result.decision_audit_trail).decode()
        risk_dump = result.risk_score.model_dump_json()
        full_result_json = result.model_dump_json(
            include={key: True for key in _CLASSIFICATION_RESULT_JSON_INCLUDE},
        )
        generated_at = _ensure_utc(result.generated_at)

        sw_row = SoftwareUpdateRecord(
            correlation_id=trimmed,
            device_name=assessment_input.device_name,
            input_snapshot_json=assessment_input.model_dump_json(),
        )

        try:
            with Session(self._engine) as session, session.begin():
                session.add(sw_row)
                session.flush()
                sw_id = cast("int", sw_row.id)
                cls_row = ClassificationResultRecord(
                    software_update_record_id=sw_id,
                    generated_at_utc=generated_at,
                    classification_band=result.band.value,
                    total_points=result.total_score,
                    normalized_score=result.normalized_score,
                    risk_score_json=risk_dump,
                    contributions_json=contributions_dump,
                    decision_audit_trail_json=trail_dump,
                    full_result_snapshot_json=full_result_json,
                )
                session.add(cls_row)
                session.flush()
                cls_id = cast("int", cls_row.id)
                audit = AuditTrailRecord(
                    action=AuditAction.CLASSIFICATION_PERSISTED.value,
                    entity_table=ClassificationResultRecord.__tablename__,
                    entity_id=cls_id,
                    correlation_id=trimmed,
                    classification_result_id=cls_id,
                    actor=actor,
                    details=_dump_details(
                        {
                            "software_update_record_id": sw_id,
                            "classification_result_id": cls_id,
                            "device_name": assessment_input.device_name,
                            "correlation_id": trimmed,
                            "classification_band": result.band.value,
                            "total_points": result.total_score,
                            "normalized_score": result.normalized_score,
                            "generated_at_utc": generated_at.isoformat(),
                        }
                    ),
                )
                session.add(audit)
                persisted_at = cls_row.persisted_at_utc
        except StorageError:
            raise
        except Exception as exc:
            logger.debug("Classification persistence failed", exc_info=True)
            raise StorageError(
                "We could not save this classification. Confirm the database path in settings.",
                detail=str(exc),
            ) from exc

        persisted_at_utc = _ensure_utc(persisted_at)
        logger.info(
            "Classification persisted id=%s correlation=%s device=%s",
            cls_id,
            trimmed,
            assessment_input.device_name,
        )
        return PersistedAssessment(
            id=cls_id,
            created_at=persisted_at_utc,
            correlation_id=trimmed,
            software_update_record_id=sw_id,
            input=assessment_input,
            result=result,
        )

    def save_assessment(
        self,
        assessment_input: AssessmentInput,
        result: ClassificationResult,
        *,
        actor: str = "interactive_user",
        correlation_id: str | None = None,
    ) -> PersistedAssessment:
        """Backward-compatible wrapper defaulting ``correlation_id`` to ``device_name``.

        Args:
            assessment_input: Assessment facts submitted through legacy UI paths.
            result: Engine output bundle.
            actor: Interactive or batch actor label.
            correlation_id: Optional explicit key; defaults to stripped ``device_name``.

        Returns:
            Same shape as :meth:`save_classification_result`.
        """
        cid = correlation_id.strip() if correlation_id is not None else assessment_input.device_name.strip()
        return self.save_classification_result(
            correlation_id=cid,
            assessment_input=assessment_input,
            result=result,
            actor=actor,
        )

    def get_latest_classification(self, euct_or_device_id: str) -> PersistedAssessment | None:
        """Return the newest persisted classification for a correlation identifier.

        Args:
            euct_or_device_id: Business correlation key previously supplied to persistence.

        Returns:
            The latest row by ``persisted_at_utc``, or ``None`` when unknown.
        """
        trimmed = euct_or_device_id.strip()
        if not trimmed:
            raise StorageError("euct_or_device_id must be non-empty.", detail="empty id")

        stmt = (
            select(ClassificationResultRecord, SoftwareUpdateRecord)
            .join(SoftwareUpdateRecord)
            .where(SoftwareUpdateRecord.correlation_id == trimmed)
            .order_by(desc(cast("Any", ClassificationResultRecord.persisted_at_utc)))
            .limit(1)
        )
        try:
            with Session(self._engine) as session:
                row = session.exec(stmt).first()
        except Exception as exc:
            logger.debug("Latest classification lookup failed", exc_info=True)
            raise StorageError(
                "Unable to load the latest classification for that identifier.",
                detail=str(exc),
            ) from exc

        if row is None:
            return None
        cls_row, sw_row = row
        return self._rows_to_persisted(cls_row, sw_row)

    def get_classification_history(
        self,
        euct_or_device_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PersistedAssessment]:
        """Return chronological classification history for a correlation identifier (newest first).

        Args:
            euct_or_device_id: Same correlation key used during persistence.
            limit: Maximum rows to return (must be positive).
            offset: Number of newest rows to skip for pagination.

        Returns:
            Ordered list suitable for timeline rendering.

        Raises:
            StorageError: When arguments are invalid or the database cannot be read.
        """
        trimmed = euct_or_device_id.strip()
        if not trimmed:
            raise StorageError("euct_or_device_id must be non-empty.", detail="empty id")
        if limit <= 0:
            raise StorageError("limit must be positive.", detail="limit <= 0")
        if offset < 0:
            raise StorageError("offset must be non-negative.", detail="offset < 0")

        stmt = (
            select(ClassificationResultRecord, SoftwareUpdateRecord)
            .join(SoftwareUpdateRecord)
            .where(SoftwareUpdateRecord.correlation_id == trimmed)
            .order_by(desc(cast("Any", ClassificationResultRecord.persisted_at_utc)))
            .offset(offset)
            .limit(limit)
        )
        try:
            with Session(self._engine) as session:
                pairs = list(session.exec(stmt).all())
        except Exception as exc:
            logger.debug("Classification history query failed", exc_info=True)
            raise StorageError("Unable to read classification history.", detail=str(exc)) from exc

        return [self._rows_to_persisted(c, s) for c, s in pairs]

    def list_assessments(self, *, limit: int = 100) -> list[PersistedAssessment]:
        """Return recent classifications across all correlation identifiers (newest first).

        Args:
            limit: Maximum rows to return.

        Returns:
            Persisted bundles ordered by classification insert time.
        """
        if limit <= 0:
            raise StorageError("limit must be positive", detail="limit <= 0")
        stmt = (
            select(ClassificationResultRecord, SoftwareUpdateRecord)
            .join(SoftwareUpdateRecord)
            .order_by(desc(cast("Any", ClassificationResultRecord.persisted_at_utc)))
            .limit(limit)
        )
        try:
            with Session(self._engine) as session:
                pairs = list(session.exec(stmt).all())
        except Exception as exc:
            logger.debug("Global listing failed", exc_info=True)
            raise StorageError("Unable to read assessment history.", detail=str(exc)) from exc

        return [self._rows_to_persisted(c, s) for c, s in pairs]

    def get_assessment(self, assessment_id: int) -> PersistedAssessment | None:
        """Fetch a single classification by primary key."""
        try:
            with Session(self._engine) as session:
                cls_row = session.get(ClassificationResultRecord, assessment_id)
                if cls_row is None:
                    return None
                sw_row = session.get(SoftwareUpdateRecord, cls_row.software_update_record_id)
        except Exception as exc:
            logger.debug("Assessment fetch failed", exc_info=True)
            raise StorageError("Unable to load that assessment record.", detail=str(exc)) from exc

        if sw_row is None:
            raise StorageError(
                "Classification row is orphaned — software snapshot missing.",
                detail=f"classification_id={assessment_id}",
            )

        persisted = self._rows_to_persisted(cls_row, sw_row)
        self.record_audit_event(
            AuditAction.CLASSIFICATION_ACCESSED,
            entity_table=ClassificationResultRecord.__tablename__,
            entity_id=assessment_id,
            correlation_id=sw_row.correlation_id,
            classification_result_id=assessment_id,
            details={
                "classification_result_id": assessment_id,
                "correlation_id": sw_row.correlation_id,
            },
        )
        return persisted

    def get_audit_trail(
        self,
        *,
        correlation_id: str | None = None,
        classification_result_id: int | None = None,
        limit: int = 200,
    ) -> list[AuditTrailRecord]:
        """Return append-only audit events with optional filters (newest first).

        Args:
            correlation_id: Restrict to events carrying this correlation id.
            classification_result_id: Restrict to rows linked to a classification PK.
            limit: Maximum events to return.

        Returns:
            Concrete :class:`AuditTrailRecord` rows suitable for compliance review exports.

        Raises:
            StorageError: When limits are invalid or the database cannot be queried.
        """
        if limit <= 0:
            raise StorageError("limit must be positive", detail="limit <= 0")

        stmt = select(AuditTrailRecord)
        if correlation_id is not None:
            trimmed = correlation_id.strip()
            if not trimmed:
                raise StorageError("correlation_id filter must be non-empty when provided.", detail="empty")
            stmt = stmt.where(AuditTrailRecord.correlation_id == trimmed)
        if classification_result_id is not None:
            stmt = stmt.where(AuditTrailRecord.classification_result_id == classification_result_id)
        stmt = stmt.order_by(desc(cast("Any", AuditTrailRecord.timestamp))).limit(limit)

        try:
            with Session(self._engine) as session:
                return list(session.exec(stmt).all())
        except Exception as exc:
            logger.debug("Audit listing failed", exc_info=True)
            raise StorageError("Unable to read audit trail.", detail=str(exc)) from exc

    def audit_trail(self, *, limit: int = 200) -> list[AuditTrailRecord]:
        """Most recent audit events (newest first) — alias for :meth:`get_audit_trail` without filters."""
        return self.get_audit_trail(limit=limit)

    def _rows_to_persisted(
        self,
        cls_row: ClassificationResultRecord,
        sw_row: SoftwareUpdateRecord,
    ) -> PersistedAssessment:
        """Materialize a persisted bundle from joined SQL rows."""
        input_model = AssessmentInput.model_validate_json(sw_row.input_snapshot_json)
        result_model = ClassificationResult.model_validate_json(cls_row.full_result_snapshot_json)
        cls_id = cls_row.id
        sw_id = sw_row.id
        if cls_id is None or sw_id is None:
            raise StorageError("Incomplete row — missing surrogate keys.", detail="null pk")
        return PersistedAssessment(
            id=cls_id,
            created_at=_ensure_utc(cls_row.persisted_at_utc),
            correlation_id=sw_row.correlation_id,
            software_update_record_id=sw_id,
            input=input_model,
            result=result_model,
        )


GuardianStorage = StorageService
"""Backward-compatible alias retained for incremental UI refactors."""


_storage_singleton: StorageService | None = None


def get_storage() -> StorageService:
    """Shared storage handle for application layers (including Streamlit)."""
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = StorageService()
        _storage_singleton.init_db()
    return _storage_singleton


def reset_storage_singleton() -> None:
    """Testing helper — drops singleton handle and closes its SQLite pool if present."""
    global _storage_singleton
    if _storage_singleton is not None:
        _storage_singleton.dispose()
    _storage_singleton = None


__all__ = [
    "AuditLogEntry",
    "ClassificationResultRecord",
    "GuardianStorage",
    "SoftwareUpdateRecord",
    "StorageError",
    "StorageService",
    "get_storage",
    "reset_storage_singleton",
]
