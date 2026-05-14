"""Streamlit caching helpers — keep expensive reads predictable."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

from update_guardian.core.storage import get_storage

if TYPE_CHECKING:
    from update_guardian.core.models import PersistedAssessment


@st.cache_data(ttl=30, show_spinner=False)
def load_recent_assessments(limit: int, cache_bump: int) -> list[PersistedAssessment]:
    """Load assessments; ``cache_bump`` is a session-driven invalidation token."""
    _ = cache_bump
    return get_storage().list_assessments(limit=limit)
