"""Pydantic model constraints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from update_guardian.core.models import (
    AssessmentInput,
    DeviceClass,
    DistributionScope,
    SoftwareSafetyClass,
    UpdateTypeIndication,
)


def test_assessment_input_rejects_empty_device() -> None:
    with pytest.raises(ValidationError):
        AssessmentInput(
            device_name="",
            device_class=DeviceClass.CLASS_IIB,
            software_safety_class=SoftwareSafetyClass.CLASS_B,
            distribution_scope=DistributionScope.GLOBAL,
            update_type=UpdateTypeIndication.DEFECT_CORRECTION,
        )


def test_assessment_input_accepts_minimal() -> None:
    model = AssessmentInput(
        device_name="Test device",
        device_class=DeviceClass.CLASS_III,
        software_safety_class=SoftwareSafetyClass.CLASS_C,
        distribution_scope=DistributionScope.SINGLE_SITE,
        update_type=UpdateTypeIndication.SECURITY_PATCH,
    )
    assert model.device_name == "Test device"
