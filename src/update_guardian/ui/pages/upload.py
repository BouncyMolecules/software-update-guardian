"""Capture release notes, structured facts, classify, and optionally persist."""

from __future__ import annotations

import logging

import streamlit as st
from pydantic import ValidationError

from update_guardian.core.classifier import AssessmentProcessingError, classify_update
from update_guardian.core.models import (
    AssessmentInput,
    ClassificationResult,
    DeviceClass,
    DistributionScope,
    SoftwareSafetyClass,
    UpdateTypeIndication,
)
from update_guardian.core.storage import StorageError, get_storage
from update_guardian.ui.utils import session as session_utils

logger = logging.getLogger(__name__)

_MAX_SUMMARY_CHARS = 8000


def _merge_notes(*, uploaded_document: str, manual_notes: str) -> str:
    parts: list[str] = []
    u = uploaded_document.strip()
    m = manual_notes.strip()
    if u:
        parts.append("--- Uploaded document ---\n" + u)
    if m:
        parts.append("--- Additional notes ---\n" + m)
    merged = "\n\n".join(parts).strip()
    if len(merged) > _MAX_SUMMARY_CHARS:
        return merged[:_MAX_SUMMARY_CHARS]
    return merged


def _render_pending_review(
    *,
    assessment_input: AssessmentInput,
    result: ClassificationResult,
    correlation_id: str,
) -> None:
    st.success("Classification complete — review the trace below before persisting.")
    st.subheader("Outcome")
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Normalized score",
        f"{result.normalized_score}",
        help="0-100 heuristic scale - informational only.",
    )
    m2.metric("Total points", f"{result.total_score}")
    m3.metric("Band", result.band.value.replace("_", " ").title())

    st.markdown(result.executive_summary)
    with st.expander("Contributing factors (rule-level trace)"):
        for factor in result.factors:
            st.markdown(
                f"- **{factor.rule_id}** · {factor.title} · **{factor.points_awarded:+d}** — {factor.rationale}"
            )
    st.markdown("**Recommended next steps**")
    for step in result.recommended_next_steps:
        st.markdown(f"- {step}")
    st.caption(result.disclaimer)

    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("Persist to local audit database", type="primary", key="ug_save_classification"):
            try:
                get_storage().save_assessment(
                    assessment_input,
                    result,
                    correlation_id=correlation_id if correlation_id.strip() else None,
                )
                session_utils.bump_assessment_cache()
                session_utils.clear_pending_classification()
                st.toast("Saved — record is available under History & audit.", icon="✅")
            except StorageError as exc:
                logger.info("Save failed: %s", exc.message)
                st.error(exc.message)
            except Exception:
                logger.exception("Unexpected save failure")
                st.error("Could not save this classification. Check logs for details.")
            else:
                st.rerun()
    with col_clear:
        if st.button("Discard draft result", key="ug_clear_classification"):
            session_utils.clear_pending_classification()
            st.rerun()


def render() -> None:
    st.title("Classify update")
    st.caption(
        "Upload release notes or describe the change, then confirm structured facts. "
        "Scoring is deterministic from explicit rules — narrative tone is not inferred."
    )

    pending = st.session_state.get(session_utils.KEY_PENDING_CLASSIFICATION)
    if isinstance(pending, dict) and "input" in pending and "result" in pending:
        try:
            loaded_input = AssessmentInput.model_validate(pending["input"])
            loaded_result = ClassificationResult.model_validate(pending["result"])
            corr = str(pending.get("correlation_id") or "")
        except ValidationError:
            logger.info("Dropped stale pending classification payload.")
            session_utils.clear_pending_classification()
        else:
            _render_pending_review(
                assessment_input=loaded_input,
                result=loaded_result,
                correlation_id=corr,
            )
            return

    with st.form("assessment_form"):
        correlation_id = st.text_input(
            "Correlation ID (recommended)",
            placeholder="EU CT / UDI-DI / internal device master key",
            help="Used for audit retrieval. When blank, the device name is used as the default key.",
        )
        device_name = st.text_input("Device / system name", placeholder="e.g., NeuroMonitor Pro")
        file = st.file_uploader(
            "Release notes or update description (optional)",
            type=["txt", "md"],
            help="Plain-text notes only (.txt / .md). Content is appended to the narrative field.",
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            device_class = st.selectbox(
                "Device class (representative)",
                options=list(DeviceClass),
                format_func=lambda x: x.value.replace("_", " ").title(),
            )
        with col2:
            safety_class = st.selectbox(
                "Software safety class (IEC 62304 style)",
                options=list(SoftwareSafetyClass),
                format_func=lambda x: x.value.replace("_", " ").title(),
            )
        with col3:
            dist_scope = st.selectbox(
                "Distribution scope",
                options=list(DistributionScope),
                format_func=lambda x: x.value.replace("_", " ").title(),
            )

        update_type = st.selectbox(
            "Primary technical characterization",
            options=list(UpdateTypeIndication),
            format_func=lambda x: x.value.replace("_", " ").title(),
        )

        st.markdown("**Risk drivers**")
        clinical = st.checkbox("Affects clinical function or output", value=False)
        decisioning = st.checkbox(
            "Affects diagnostic or treatment decision-making",
            value=False,
        )
        labeling = st.checkbox("Changes device labeling or IFU", value=False)
        connectivity = st.checkbox(
            "Introduces or changes connectivity / remote interfaces",
            value=False,
        )
        security = st.checkbox(
            "Mitigates known or suspected security vulnerability",
            value=False,
        )
        data_integrity = st.checkbox(
            "Impacts data integrity, audit trails, or GxP records",
            value=False,
        )
        prior_field = st.checkbox(
            "Prior similar issues in the field or complaint trend",
            value=False,
        )
        pms = st.checkbox("Affects postmarket surveillance or risk controls", value=False)
        intended_use = st.checkbox(
            "Intended use change or new indication is in discussion",
            value=False,
        )

        colw, colr = st.columns(2)
        with colw:
            workaround = st.checkbox(
                "Workaround exists without clinical compromise",
                value=False,
            )
        with colr:
            release_notes_safe = st.checkbox(
                "Release documentation asserts no patient risk from this change",
                value=True,
            )

        summary = st.text_area(
            "Narrative (internal notes)",
            placeholder="Add context that should travel with the audit snapshot.",
            height=140,
        )

        submitted = st.form_submit_button("Run classification", type="primary")

    if not submitted:
        return

    if not device_name.strip():
        st.warning("Device name is required.")
        return

    uploaded_text = ""
    if file is not None:
        try:
            uploaded_text = file.getvalue().decode("utf-8", errors="replace")
        except Exception:
            logger.exception("Failed to decode uploaded document")
            st.error("The uploaded document could not be read as UTF-8 text. Save as .txt and retry.")
            return
        if len(uploaded_text) > _MAX_SUMMARY_CHARS:
            st.warning(
                f"Uploaded document was truncated to {_MAX_SUMMARY_CHARS} characters "
                "to satisfy validation limits."
            )

    merged_summary = _merge_notes(uploaded_document=uploaded_text, manual_notes=summary)

    try:
        with st.spinner("Evaluating rules and compiling audit trace…"):
            assessment_input = AssessmentInput(
                device_name=device_name.strip(),
                device_class=device_class,
                software_safety_class=safety_class,
                distribution_scope=dist_scope,
                update_type=update_type,
                affects_clinical_function_or_output=clinical,
                affects_diagnostic_or_treatment_decisioning=decisioning,
                changes_device_labeling_or_ifu=labeling,
                introduces_or_changes_connectivity_or_remote_interfaces=connectivity,
                mitigates_known_or_suspected_security_vulnerability=security,
                impacts_data_integrity_audit_trails_or_records_used_for_gxp=data_integrity,
                prior_similar_issues_in_field_or_complaints=prior_field,
                workaround_available_without_clinical_compromise=workaround,
                affects_post_market_surveillance_or_risk_controls=pms,
                intended_use_change_or_new_indication_discussed=intended_use,
                release_notes_assert_no_patient_risk=release_notes_safe,
                summary_text=merged_summary,
            )
            result = classify_update(assessment_input)
    except ValidationError:
        logger.info("Assessment validation issue", exc_info=True)
        st.error("Some inputs could not be validated. Please review lengths and required fields.")
        return
    except AssessmentProcessingError as exc:
        logger.info("Classification engine error: %s", exc)
        st.error(exc.args[0] if exc.args else "Classification could not be completed.")
        return
    except Exception:
        logger.exception("Unexpected classification failure")
        st.error("Something went wrong while classifying. Try again or contact support.")
        return

    st.session_state[session_utils.KEY_PENDING_CLASSIFICATION] = {
        "input": assessment_input.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "correlation_id": correlation_id.strip(),
    }
    st.rerun()
