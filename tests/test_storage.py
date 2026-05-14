"""SQLite persistence and audit-trail behaviour."""

from __future__ import annotations

import pytest
from sqlmodel import Session, select

from update_guardian.core.classifier import classify_update
from update_guardian.core.models import (
    AssessmentInput,
    DeviceClass,
    DistributionScope,
    SoftwareSafetyClass,
    UpdateTypeIndication,
)
from update_guardian.core.storage import AuditLogEntry, StorageError, StorageService


def test_save_and_roundtrip(storage: StorageService) -> None:
    assessment = AssessmentInput(
        device_name="Unit under test",
        device_class=DeviceClass.CLASS_IIB,
        software_safety_class=SoftwareSafetyClass.CLASS_C,
        distribution_scope=DistributionScope.REGIONAL,
        update_type=UpdateTypeIndication.DEFECT_CORRECTION,
    )
    result = classify_update(assessment)
    persisted = storage.save_assessment(assessment, result, actor="pytest")

    assert persisted.id >= 1
    assert persisted.correlation_id == assessment.device_name
    assert persisted.software_update_record_id >= 1

    loaded = storage.get_assessment(persisted.id)
    assert loaded is not None
    assert loaded.input.device_name == assessment.device_name
    assert loaded.result.total_score == result.total_score
    assert loaded.correlation_id == persisted.correlation_id

    with Session(storage.engine) as session:
        audits = list(session.exec(select(AuditLogEntry)))
        assert any(a.action == "classification_persisted" for a in audits)
        assert any(a.action == "classification_accessed" for a in audits)


def test_correlation_history_and_latest(storage: StorageService) -> None:
    corr = "EU-CT-2026-00042"
    base = dict(
        device_name="Trial device",
        device_class=DeviceClass.CLASS_III,
        software_safety_class=SoftwareSafetyClass.CLASS_C,
        distribution_scope=DistributionScope.GLOBAL,
        update_type=UpdateTypeIndication.SECURITY_PATCH,
        mitigates_known_or_suspected_security_vulnerability=True,
    )
    a1 = AssessmentInput(**base)
    r1 = classify_update(a1)
    storage.save_classification_result(
        correlation_id=corr, assessment_input=a1, result=r1, actor="u1"
    )

    a2 = AssessmentInput(**{**base, "prior_similar_issues_in_field_or_complaints": True})
    r2 = classify_update(a2)
    storage.save_classification_result(
        correlation_id=corr, assessment_input=a2, result=r2, actor="u2"
    )

    latest = storage.get_latest_classification(corr)
    assert latest is not None
    assert latest.result.total_score == r2.total_score

    hist = storage.get_classification_history(corr, limit=10)
    assert len(hist) == 2
    assert hist[0].result.total_score == r2.total_score
    assert hist[1].result.total_score == r1.total_score

    filtered_audit = storage.get_audit_trail(correlation_id=corr, limit=50)
    assert all(e.correlation_id == corr for e in filtered_audit)


def test_save_rejects_whitespace_only_correlation_id(storage: StorageService) -> None:
    assessment = AssessmentInput(
        device_name="Scoped id",
        device_class=DeviceClass.CLASS_IIA,
        software_safety_class=SoftwareSafetyClass.CLASS_B,
        distribution_scope=DistributionScope.SINGLE_SITE,
        update_type=UpdateTypeIndication.CONFIG_OR_WORKFLOW,
    )
    result = classify_update(assessment)
    with pytest.raises(StorageError, match="correlation_id"):
        storage.save_classification_result(
            correlation_id="  \t ",
            assessment_input=assessment,
            result=result,
            actor="pytest",
        )


def test_list_assessments_newest_first(storage: StorageService) -> None:
    assert storage.list_assessments(limit=10) == []

    base = dict(
        device_name="Lister",
        device_class=DeviceClass.CLASS_I,
        software_safety_class=SoftwareSafetyClass.CLASS_A,
        distribution_scope=DistributionScope.SINGLE_SITE,
        update_type=UpdateTypeIndication.THIRD_PARTY_COMPONENT,
    )
    a1 = AssessmentInput(**base)
    r1 = classify_update(a1)
    storage.save_classification_result(
        correlation_id="c1", assessment_input=a1, result=r1, actor="t1"
    )

    a2 = AssessmentInput(**{**base, "device_name": "Lister 2"})
    r2 = classify_update(a2)
    storage.save_classification_result(
        correlation_id="c2", assessment_input=a2, result=r2, actor="t2"
    )

    rows = storage.list_assessments(limit=10)
    assert len(rows) == 2
    assert rows[0].correlation_id == "c2"
    assert rows[1].correlation_id == "c1"
