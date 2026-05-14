"""Classification rule engine."""

from __future__ import annotations

from update_guardian.core.classifier import classify_update
from update_guardian.core.models import (
    AssessmentInput,
    ClassificationBand,
    DeviceClass,
    DistributionScope,
    SoftwareSafetyClass,
    UpdateTypeIndication,
)


def test_routine_band_for_minimal_fix() -> None:
    assessment = AssessmentInput(
        device_name="Bench analyzer",
        device_class=DeviceClass.CLASS_I,
        software_safety_class=SoftwareSafetyClass.CLASS_A,
        distribution_scope=DistributionScope.SINGLE_SITE,
        update_type=UpdateTypeIndication.DEFECT_CORRECTION,
    )
    result = classify_update(assessment)
    assert result.band == ClassificationBand.ROUTINE_QUALITY_FIX
    assert result.total_score >= 0
    assert 0 <= result.normalized_score <= 100


def test_elevated_when_high_risk_stack() -> None:
    assessment = AssessmentInput(
        device_name="Critical pump",
        device_class=DeviceClass.CLASS_III,
        software_safety_class=SoftwareSafetyClass.CLASS_C,
        distribution_scope=DistributionScope.GLOBAL,
        update_type=UpdateTypeIndication.ALGORITHM_CHANGE,
        affects_clinical_function_or_output=True,
        affects_diagnostic_or_treatment_decisioning=True,
        changes_device_labeling_or_ifu=True,
        mitigates_known_or_suspected_security_vulnerability=True,
        prior_similar_issues_in_field_or_complaints=True,
        intended_use_change_or_new_indication_discussed=True,
        release_notes_assert_no_patient_risk=False,
    )
    result = classify_update(assessment)
    assert result.band == ClassificationBand.ELEVATED_REPORTING_AND_FIELD_ACTION_LIKELIHOOD
    assert any(f.rule_id == "R-REG-INTENDED-USE" for f in result.factors)
