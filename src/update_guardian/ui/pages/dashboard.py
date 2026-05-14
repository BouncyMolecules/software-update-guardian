"""Executive dashboard — KPIs, monitored portfolio slice, and risk trajectory."""

from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from update_guardian.config import get_settings
from update_guardian.core.models import ClassificationBand
from update_guardian.core.storage import StorageError, StorageService
from update_guardian.ui.utils import caching
from update_guardian.ui.utils import session as session_utils

logger = logging.getLogger(__name__)


def render(storage: StorageService) -> None:
    settings = get_settings()
    st.title("Monitored portfolio")
    if settings.organization_name:
        st.caption(f"Organization context: **{settings.organization_name}**")
    st.caption(
        "Aggregated heuristics across saved classifications — not a substitute for formal trending in your QMS."
    )

    try:
        with st.spinner("Loading recent assessments…"):
            items = caching.load_recent_assessments(
                storage, 100, session_utils.assessment_cache_version()
            )
    except StorageError as exc:
        logger.info("Dashboard load failed: %s", exc.message)
        st.error(exc.message)
        return
    except Exception:
        logger.exception("Unexpected dashboard failure")
        st.error("Unable to load assessments. Confirm database settings and try again.")
        return

    if not items:
        st.info("No assessments yet — start with **Classify update** to build your portfolio view.")
        return

    elevated = sum(
        1
        for i in items
        if i.result.band == ClassificationBand.ELEVATED_REPORTING_AND_FIELD_ACTION_LIKELIHOOD
    )
    borderline = sum(
        1 for i in items if i.result.band == ClassificationBand.BORDERLINE_FIELD_INVESTIGATION
    )
    routine = sum(1 for i in items if i.result.band == ClassificationBand.ROUTINE_QUALITY_FIX)
    avg_score = sum(i.result.normalized_score for i in items) / max(len(items), 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Assessments (window)", len(items))
    c2.metric(
        "Elevated band",
        elevated,
        help="Heuristic band only — confirm with RA/QA before external communication.",
    )
    c3.metric("Borderline band", borderline)
    c4.metric("Routine / maintenance", routine)
    c5.metric("Avg. normalized score", f"{avg_score:.1f}")

    st.subheader("Risk trajectory")
    chron = list(reversed(items))
    series = pd.DataFrame(
        {
            "Recorded (UTC)": [i.created_at for i in chron],
            "Normalized score": [i.result.normalized_score for i in chron],
        }
    )
    if len(series) < 2:
        st.info("Save at least two assessments to plot a trajectory across time.")
    else:
        st.line_chart(series.set_index("Recorded (UTC)"), height=280)

    st.subheader("Latest classifications")
    st.dataframe(
        [
            {
                "ID": i.id,
                "Created (UTC)": i.created_at.strftime("%Y-%m-%d %H:%M"),
                "Correlation": i.correlation_id,
                "Device": i.input.device_name,
                "Band": i.result.band.value.replace("_", " ").title(),
                "Points": i.result.total_score,
                "Normalized": i.result.normalized_score,
            }
            for i in items[:25]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Band mix (count)")
    band_df = pd.DataFrame(
        {
            "Band": ["Elevated", "Borderline", "Routine"],
            "Count": [elevated, borderline, routine],
        }
    )
    st.bar_chart(band_df.set_index("Band"))

    corr_filter = session_utils.get_selected_correlation_filter()
    if corr_filter:
        try:
            scoped = storage.get_classification_history(corr_filter, limit=50)
        except StorageError as exc:
            st.warning(exc.message)
        else:
            if scoped:
                st.subheader(f"Focused history — `{corr_filter}`")
                st.dataframe(
                    [
                        {
                            "ID": r.id,
                            "Persisted (UTC)": r.created_at.strftime("%Y-%m-%d %H:%M"),
                            "Normalized": r.result.normalized_score,
                            "Band": r.result.band.value.replace("_", " ").title(),
                        }
                        for r in scoped
                    ],
                    use_container_width=True,
                    hide_index=True,
                )
