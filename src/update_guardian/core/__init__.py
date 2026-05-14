"""Core domain package — pure logic, no Streamlit."""

from update_guardian.core.classifier import (
    AssessmentProcessingError,
    SoftwareUpdateClassifier,
    classify_update,
)
from update_guardian.core.models import (
    AssessmentInput,
    AuditAction,
    AuditTrailEntry,
    ClassificationBand,
    ClassificationResult,
    DeviceClass,
    DistributionScope,
    RegulatoryRuleCategory,
    RiskFactor,
    RiskScore,
    RuleContribution,
    SoftwareSafetyClass,
    SoftwareUpdate,
    UpdateClassification,
    UpdateTypeIndication,
)

__all__ = [
    "AssessmentInput",
    "AssessmentProcessingError",
    "AuditAction",
    "AuditTrailEntry",
    "ClassificationBand",
    "ClassificationResult",
    "DeviceClass",
    "DistributionScope",
    "RegulatoryRuleCategory",
    "RiskFactor",
    "RiskScore",
    "RuleContribution",
    "SoftwareSafetyClass",
    "SoftwareUpdate",
    "SoftwareUpdateClassifier",
    "UpdateClassification",
    "UpdateTypeIndication",
    "classify_update",
]
