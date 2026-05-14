"""Pydantic domain models for software-update assessment and audit-grade outputs."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from sqlalchemy import Column, Index, Text
from sqlmodel import Field as SQLField
from sqlmodel import SQLModel


class GuardianError(Exception):
    """Base error for user-facing guardian failures."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class AssessmentValidationError(GuardianError):
    """Raised when assessment inputs fail validation for classification."""


class DeviceClass(StrEnum):
    """EU MDR-style device class abstraction (coarse, for risk posture only)."""

    CLASS_I = "class_i"
    CLASS_IIA = "class_iia"
    CLASS_IIB = "class_iib"
    CLASS_III = "class_iii"


class SoftwareSafetyClass(StrEnum):
    """IEC 62304-style software safety class - drives residual-risk posture."""

    CLASS_A = "class_a"
    CLASS_B = "class_b"
    CLASS_C = "class_c"


class DistributionScope(StrEnum):
    """Geographic reach of the update — affects recall and communication surface area."""

    SINGLE_SITE = "single_site"
    REGIONAL = "regional"
    GLOBAL = "global"


class UpdateTypeIndication(StrEnum):
    """Primary technical characterization of the change set."""

    DEFECT_CORRECTION = "defect_correction"
    SECURITY_PATCH = "security_patch"
    ENHANCEMENT = "enhancement"
    ALGORITHM_CHANGE = "algorithm_change"
    CONFIG_OR_WORKFLOW = "config_or_workflow"
    THIRD_PARTY_COMPONENT = "third_party_component"


class ClassificationBand(StrEnum):
    """Heuristic output bucket — informational only, not a legal determination."""

    ROUTINE_QUALITY_FIX = "routine_quality_fix"
    BORDERLINE_FIELD_INVESTIGATION = "borderline_field_investigation"
    ELEVATED_REPORTING_AND_FIELD_ACTION_LIKELIHOOD = (
        "elevated_reporting_and_field_action_likelihood"
    )


class RegulatoryRuleCategory(StrEnum):
    """Buckets for filtering contributions in reports and for extending the rule set."""

    DEVICE_AND_SAFETY_CLASS = "device_and_safety_class"
    DISTRIBUTION = "distribution"
    CHANGE_CHARACTERIZATION = "change_characterization"
    CLINICAL_PERFORMANCE = "clinical_performance"
    LABELING_INTENDED_USE = "labeling_intended_use"
    CONNECTIVITY_CYBER = "connectivity_cyber"
    DATA_GOVERNANCE = "data_governance"
    POSTMARKET_AND_PMS = "postmarket_and_pms"
    CORRECTION_REMOVAL_SIGNAL = "correction_removal_signal"
    RISK_OFFSET = "risk_offset"
    MAINTENANCE_POSTURE = "maintenance_posture"


class AuditAction(StrEnum):
    """Audit trail verbs used by persistence (database layer)."""

    ASSESSMENT_CREATED = "assessment_created"
    ASSESSMENT_ACCESSED = "assessment_accessed"
    DATABASE_INITIALIZED = "database_initialized"
    CLASSIFICATION_PERSISTED = "classification_persisted"
    CLASSIFICATION_ACCESSED = "classification_accessed"


class SoftwareUpdate(BaseModel):
    """Structured facts describing a remote software update under regulatory review."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    device_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=500,
            description="Human-readable identifier for the device or system receiving the update.",
        ),
    ]
    device_class: Annotated[
        DeviceClass,
        Field(description="Representative device class; aligns to EU MDR style tiers."),
    ]
    software_safety_class: Annotated[
        SoftwareSafetyClass,
        Field(
            description="IEC 62304 mapping used by many manufacturers for software lifecycle rigor."
        ),
    ]
    distribution_scope: Annotated[
        DistributionScope,
        Field(description="Planned or actual geographic scope of release."),
    ]
    update_type: Annotated[
        UpdateTypeIndication,
        Field(
            description=(
                "Primary technical narrative of the change (defect fix, security patch, enhancement, "
                "algorithm modification, etc.)."
            ),
        ),
    ]

    affects_clinical_function_or_output: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True if behavior, outputs, or workflows that can influence clinical results are touched."
            ),
        ),
    ]
    affects_diagnostic_or_treatment_decisioning: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True if the change can influence diagnosis, therapy selection, dosing, or triage decisions."
            ),
        ),
    ]
    changes_device_labeling_or_ifu: Annotated[
        bool,
        Field(
            default=False,
            description="True if instructions for use, labeling, or claims visible to users change.",
        ),
    ]
    introduces_or_changes_connectivity_or_remote_interfaces: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True if network, remote service, FHIR/API, or telemetry interfaces are new or altered."
            ),
        ),
    ]
    mitigates_known_or_suspected_security_vulnerability: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True if the change exists to address a known, credible, or suspected cybersecurity flaw "
                "or exploit path."
            ),
        ),
    ]
    impacts_data_integrity_audit_trails_or_records_used_for_gxp: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True if ALCOA+ records, audit trails, e-signatures, or data relied on in GxP could be impacted."
            ),
        ),
    ]
    prior_similar_issues_in_field_or_complaints: Annotated[
        bool,
        Field(
            default=False,
            description="True if complaints, CAPAs, or field files suggest recurrence of this failure mode.",
        ),
    ]
    workaround_available_without_clinical_compromise: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True only when a controlled workaround exists and clinical risk is credibly contained "
                "(verified separately)."
            ),
        ),
    ]
    affects_post_market_surveillance_or_risk_controls: Annotated[
        bool,
        Field(
            default=False,
            description="True if PMS inputs, risk controls from ISO 14971, or safety analytics are affected.",
        ),
    ]

    intended_use_change_or_new_indication_discussed: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "True if marketing, clinical strategy, or RA discuss expanding indication or intended use."
            ),
        ),
    ]
    release_notes_assert_no_patient_risk: Annotated[
        bool,
        Field(
            default=True,
            description=(
                "True when controlled release documentation explicitly documents negligible patient risk "
                "for the scoped change."
            ),
        ),
    ]

    summary_text: Annotated[
        str,
        Field(
            default="",
            max_length=8000,
            description="Free text for internal traceability; not parsed by the deterministic engine.",
        ),
    ]


class RuleContribution(BaseModel):
    """Single weighted, explainable contribution to the aggregate score."""

    model_config = ConfigDict(extra="forbid")

    rule_id: Annotated[
        str,
        Field(
            min_length=1,
            max_length=80,
            description="Stable identifier referenced in change control and CSV exports.",
        ),
    ]
    category: RegulatoryRuleCategory = Field(description="Regulatory theme bucket for filtering.")
    title: Annotated[str, Field(min_length=1, max_length=300, description="Short human title.")]
    rationale: Annotated[
        str,
        Field(
            min_length=1,
            max_length=4000,
            description="Plain-language reason this factor applied — suitable for RA/QA review.",
        ),
    ]
    regulatory_reference: Annotated[
        str,
        Field(
            min_length=1,
            max_length=2000,
            description=(
                "Non-exhaustive pointer to the regulatory framing (FDA, MDR, EMA, IEC) — not legal advice."
            ),
        ),
    ]
    point_value: Annotated[
        int,
        Field(description="Nominal rule severity in integer points before weighting."),
    ]
    weight: Annotated[
        float,
        Field(
            default=1.0,
            ge=0.0,
            le=10.0,
            description="Multiplicative weight for scenario tuning — defaults to 1.0 for transparency.",
        ),
    ]
    points_awarded: Annotated[
        int,
        Field(
            description="Points applied after weighting — must match round(point_value * weight).",
        ),
    ]

    @model_validator(mode="after")
    def _weighted_points_are_consistent(self) -> Self:
        expected = round(self.point_value * self.weight)
        if expected != self.points_awarded:
            msg = (
                f"points_awarded ({self.points_awarded}) must equal "
                f"round(point_value * weight) ({expected}) for rule {self.rule_id}."
            )
            raise ValueError(msg)
        return self


class RiskScore(BaseModel):
    """Auditable numeric rollup for the classification."""

    model_config = ConfigDict(extra="forbid")

    total_points: Annotated[
        int,
        Field(
            ge=0,
            description="Non-negative sum of awarded points (negative contributions clamped at aggregate).",
        ),
    ]
    normalized_0_100: Annotated[
        float,
        Field(ge=0.0, le=100.0, description="Scaled score for dashboards — heuristic only."),
    ]
    theoretical_max_points: Annotated[
        float,
        Field(
            gt=0,
            description=(
                "Denominator used for normalization: sum of positive points in the simultaneously "
                "applicable worst-case combination of rules."
            ),
        ),
    ]
    normalization_formula: Annotated[
        str,
        Field(
            min_length=1,
            max_length=2000,
            description="Exact formula string so reviewers can reproduce the scaling offline.",
        ),
    ]


class UpdateClassification(BaseModel):
    """Narrative regulatory readout aligned to bug-fix vs field-action investigation paths."""

    model_config = ConfigDict(extra="forbid")

    band: ClassificationBand = Field(description="Heuristic band from normalized score thresholds.")
    bug_fix_characterization: Annotated[
        str,
        Field(
            min_length=1,
            max_length=8000,
            description=(
                "Explains whether facts resemble pure defect correction vs enhancement — framed for FDA "
                '"correction" maintenance and EU postmarket change expectations.'
            ),
        ),
    ]
    field_action_and_reporting_posture: Annotated[
        str,
        Field(
            min_length=1,
            max_length=8000,
            description=(
                "Summarizes factors that resemble FDA correction/removal reportability concepts and "
                "EMA/MDR vigilance or FSN triggers (always requires human sign-off)."
            ),
        ),
    ]
    dominant_regulatory_themes: Annotated[
        list[str],
        Field(
            description="Ordered list of headline themes (e.g., cybersecurity, clinical decision support).",
        ),
    ]


class AuditTrailEntry(BaseModel):
    """Append-only style decision log entry produced during a single classification run."""

    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when this step was recorded.",
    )
    step: Annotated[
        str,
        Field(
            min_length=1,
            max_length=120,
            description="Machine-oriented step key (e.g., RULE_EVALUATION, BAND_SELECTED).",
        ),
    ]
    message: Annotated[
        str, Field(min_length=1, max_length=8000, description="Auditor-facing message.")
    ]
    rule_id: Annotated[
        str | None,
        Field(description="Populated when the entry relates to a specific rule id."),
    ] = None
    metadata: Annotated[
        dict[str, str],
        Field(
            default_factory=dict,
            description="Small key/value strings only — keeps snapshots JSON-safe and simple.",
        ),
    ]


class ClassificationResult(BaseModel):
    """Structured outcome bundle suitable for persistence and executive review."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC time when the engine finalized this result.",
    )
    risk_score: RiskScore
    classification: UpdateClassification
    contributions: list[RuleContribution] = Field(
        default_factory=list,
        description="All rule contributions in evaluation order unless empty.",
    )
    decision_audit_trail: list[AuditTrailEntry] = Field(
        default_factory=list,
        description="Deterministic trace of engine steps for GxP review.",
    )
    executive_summary: Annotated[
        str,
        Field(
            min_length=1,
            max_length=12000,
            description="Markdown-friendly narrative for leadership.",
        ),
    ]
    recommended_next_steps: list[str] = Field(
        description="Action checklist — procedural, not a substitute for SOPs.",
    )
    disclaimer: str = Field(
        default=(
            "This result is decision-support only and does not constitute regulatory or legal advice. "
            "Qualified Regulatory and Quality personnel must confirm classification, reporting, and "
            "field action obligations under applicable regulations and SOPs."
        ),
        max_length=4000,
        description="Mandatory caution for regulated use.",
    )

    @property
    def total_score(self) -> int:
        """Backward-compatible total points alias used by dashboards and storage tests."""
        return self.risk_score.total_points

    @property
    def normalized_score(self) -> float:
        """Backward-compatible normalized score alias."""
        return self.risk_score.normalized_0_100

    @property
    def band(self) -> ClassificationBand:
        """Backward-compatible band alias."""
        return self.classification.band

    @property
    def factors(self) -> list[RuleContribution]:
        """Legacy name for contributors — identical ordering to ``contributions``."""
        return self.contributions


class PersistedAssessment(BaseModel):
    """Exchange model for API/UI — serializable assessment bundle."""

    model_config = ConfigDict(extra="forbid")

    id: int
    created_at: datetime
    correlation_id: str = Field(
        description=(
            "Business correlation identifier (for example EU CT number fragment, UDI-DI, or internal device key). "
            "Defaults to ``device_name`` when callers omit an explicit correlation id."
        ),
    )
    software_update_record_id: int = Field(
        description="Primary key of the immutable software-update snapshot row in persistent storage.",
    )
    input: SoftwareUpdate
    result: ClassificationResult


class SoftwareUpdateRecord(SQLModel, table=True):
    """Immutable persisted snapshot of :class:`SoftwareUpdate` inputs."""

    __tablename__ = "software_update_record"

    id: int | None = SQLField(default=None, primary_key=True)
    correlation_id: str = SQLField(
        index=True,
        max_length=500,
        description="EU CT / device id / internal correlation — indexed for history retrieval.",
    )
    device_name: str = SQLField(index=True, max_length=500)
    input_snapshot_json: str = SQLField(
        sa_column=Column(Text, nullable=False),
        description="Canonical JSON snapshot of the assessment input at persistence time.",
    )
    created_at_utc: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        index=True,
        description="UTC timestamp when the snapshot row was inserted.",
    )


class ClassificationResultRecord(SQLModel, table=True):
    """Immutable persisted classification outcome linked to a single software-update snapshot."""

    __tablename__ = "classification_result_record"
    __table_args__ = (
        Index(
            "ix_classification_software_persisted",
            "software_update_record_id",
            "persisted_at_utc",
        ),
    )

    id: int | None = SQLField(default=None, primary_key=True)
    software_update_record_id: int = SQLField(
        foreign_key="software_update_record.id",
        index=True,
    )
    persisted_at_utc: datetime = SQLField(
        default_factory=lambda: datetime.now(UTC),
        index=True,
        description="UTC insert time for this immutable classification row.",
    )
    generated_at_utc: datetime = SQLField(
        index=True,
        description="UTC ``ClassificationResult.generated_at`` copied for querying.",
    )
    classification_band: str = SQLField(index=True, max_length=200)
    total_points: int = SQLField(index=True)
    normalized_score: float = SQLField(index=True)
    risk_score_json: str = SQLField(
        sa_column=Column(Text, nullable=False),
        description="Serialized :class:`RiskScore` for standalone inspection.",
    )
    contributions_json: str = SQLField(
        sa_column=Column(Text, nullable=False),
        description="Serialized rule contributions list — mirrors ``ClassificationResult.contributions``.",
    )
    decision_audit_trail_json: str = SQLField(
        sa_column=Column(Text, nullable=False),
        description="Serialized engine :class:`AuditTrailEntry` trace — mirrors ``decision_audit_trail``.",
    )
    full_result_snapshot_json: str = SQLField(
        sa_column=Column(Text, nullable=False),
        description="Complete ``ClassificationResult`` JSON for byte-stable round-trip reproduction.",
    )


class AuditTrailRecord(SQLModel, table=True):
    """Append-only guardian audit row — logical updates are forbidden by the storage API."""

    __tablename__ = "audit_trail_record"
    __table_args__ = (Index("ix_audit_corr_time", "correlation_id", "timestamp"),)

    id: int | None = SQLField(default=None, primary_key=True)
    timestamp: datetime = SQLField(default_factory=lambda: datetime.now(UTC), index=True)
    action: str = SQLField(index=True, max_length=120)
    entity_table: str = SQLField(max_length=120)
    entity_id: int | None = SQLField(default=None, index=True)
    correlation_id: str | None = SQLField(default=None, index=True, max_length=500)
    classification_result_id: int | None = SQLField(
        default=None,
        foreign_key="classification_result_record.id",
        index=True,
    )
    actor: str = SQLField(default="system", max_length=200)
    details: str = SQLField(default="{}", sa_column=Column(Text, nullable=False))


# Backward-compatible alias — existing UI and persistence imports use ``AssessmentInput``.
AssessmentInput = SoftwareUpdate

# Legacy name retained for importers expecting ``RiskFactor`` (tuple shape matches RuleContribution).
RiskFactor = RuleContribution
