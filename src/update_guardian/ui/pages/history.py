"""Classification history with paired engine trace and system audit log."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import streamlit as st

if TYPE_CHECKING:
    from update_guardian.core.models import PersistedAssessment

from update_guardian.core.storage import StorageError, get_storage
from update_guardian.ui.utils import caching
from update_guardian.ui.utils import session as session_utils

logger = logging.getLogger(__name__)


def render() -> None:
    st.title("History & audit")
    st.caption("Immutable snapshots with deterministic rule traces — export via your browser as needed.")

    try:
        storage = get_storage()
    except StorageError as exc:
        st.error(exc.message)
        return

    col_f, col_r = st.columns([2, 1])
    with col_f:
        correlation_input = st.text_input(
            "Filter by correlation ID",
            value=session_utils.get_selected_correlation_filter(),
            placeholder="EU CT / UDI-DI / internal key — leave blank for all recent rows",
        )
    with col_r:
        st.write("")
        st.write("")
        if st.button("Apply filter", type="primary", use_container_width=True):
            session_utils.set_selected_correlation_filter(correlation_input)
            st.rerun()
        if st.button("Clear filter", use_container_width=True):
            session_utils.set_selected_correlation_filter("")
            st.rerun()

    active_filter = session_utils.get_selected_correlation_filter()
    try:
        with st.spinner("Retrieving history…"):
            if active_filter:
                items = storage.get_classification_history(active_filter, limit=200)
            else:
                items = caching.load_recent_assessments(200, session_utils.assessment_cache_version())
    except StorageError as exc:
        logger.info("History query failed: %s", exc.message)
        st.error(exc.message)
        return

    if not items:
        st.info(
            "No saved classifications match this view. Run **Classify update** or clear the correlation filter."
        )
        return

    by_id: dict[int, PersistedAssessment] = {r.id: r for r in items}

    preferred = session_utils.get_selected_assessment_id()
    default_key = preferred if preferred in by_id else max(by_id.keys())

    def _label(record_id: int) -> str:
        rec = by_id[record_id]
        return (
            f"#{record_id} · {rec.created_at:%Y-%m-%d %H:%M UTC} · {rec.input.device_name} · "
            f"{rec.correlation_id}"
        )

    choice = st.selectbox(
        "Selected classification",
        options=sorted(by_id.keys(), reverse=True),
        format_func=_label,
        index=sorted(by_id.keys(), reverse=True).index(default_key) if default_key in by_id else 0,
        key="ug_history_selection",
    )
    session_utils.set_selected_assessment_id(int(choice))
    selected = by_id[int(choice)]

    tab_summary, tab_engine, tab_system = st.tabs(
        ["Summary", "Engine decision trace", "System audit log"]
    )

    with tab_summary:
        st.markdown(f"**Band:** `{selected.result.band.value}`")
        s1, s2, s3 = st.columns(3)
        s1.metric("Normalized score", f"{selected.result.normalized_score}")
        s2.metric("Total points", f"{selected.result.total_score}")
        s3.metric("Generated (UTC)", selected.result.generated_at.strftime("%Y-%m-%d %H:%M"))
        st.markdown(selected.result.executive_summary)
        with st.expander("Input snapshot (structured facts)"):
            st.json(selected.input.model_dump(mode="json"))
        with st.expander("Contributing factors"):
            rows: list[dict[str, Any]] = []
            for factor in selected.result.factors:
                rows.append(
                    {
                        "Rule": factor.rule_id,
                        "Title": factor.title,
                        "Points": factor.points_awarded,
                        "Category": factor.category.value,
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)

    with tab_engine:
        st.caption("Deterministic evaluation order from the rules engine — suitable for QMS appendices.")
        trail = [
            {
                "Step": entry.step,
                "Time (UTC)": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Message": entry.message,
                "Rule": entry.rule_id or "",
                "Metadata": entry.metadata,
            }
            for entry in selected.result.decision_audit_trail
        ]
        st.dataframe(trail, use_container_width=True, height=480, hide_index=True)

    with tab_system:
        st.caption("Append-only storage and access events captured by the application database.")
        try:
            db_audits = storage.get_audit_trail(
                correlation_id=selected.correlation_id,
                classification_result_id=selected.id,
                limit=200,
            )
        except StorageError as exc:
            st.error(exc.message)
        else:
            if not db_audits:
                st.info("No audit rows matched this selection — the record may predate audit capture.")
            else:
                st.dataframe(
                    [
                        {
                            "ID": a.id,
                            "UTC": a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            "Action": a.action,
                            "Table": a.entity_table,
                            "Record": a.entity_id,
                            "Actor": a.actor,
                            "Details": a.details,
                        }
                        for a in db_audits
                    ],
                    use_container_width=True,
                    hide_index=True,
                    height=420,
                )
                with st.expander("Details JSON (latest event)"):
                    if db_audits:
                        try:
                            st.json(json.loads(db_audits[0].details))
                        except json.JSONDecodeError:
                            st.code(db_audits[0].details)
