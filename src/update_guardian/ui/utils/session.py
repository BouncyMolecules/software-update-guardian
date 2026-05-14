"""Session-state helpers — UI concerns only (no core imports)."""

from __future__ import annotations

from typing import Literal

import streamlit as st

ThemeMode = Literal["light", "dark"]

KEY_ONBOARDING_DISMISSED = "ug_onboarding_dismissed"
KEY_THEME = "ug_theme_mode"
KEY_ASSESSMENT_CACHE_BUMP = "ug_assessment_cache_bump"
KEY_SELECTED_CORRELATION = "ug_selected_correlation"
KEY_SELECTED_ASSESSMENT_ID = "ug_selected_assessment_id"
KEY_PENDING_CLASSIFICATION = "ug_pending_classification_payload"


def ensure_defaults() -> None:
    """Initialize keys used for onboarding, theming, cache bumps, and drill-down selection."""
    if KEY_ASSESSMENT_CACHE_BUMP not in st.session_state:
        st.session_state[KEY_ASSESSMENT_CACHE_BUMP] = 0
    if KEY_ONBOARDING_DISMISSED not in st.session_state:
        st.session_state[KEY_ONBOARDING_DISMISSED] = False
    if KEY_THEME not in st.session_state:
        st.session_state[KEY_THEME] = "light"
    if KEY_SELECTED_CORRELATION not in st.session_state:
        st.session_state[KEY_SELECTED_CORRELATION] = ""
    if KEY_SELECTED_ASSESSMENT_ID not in st.session_state:
        st.session_state[KEY_SELECTED_ASSESSMENT_ID] = None
    if KEY_PENDING_CLASSIFICATION not in st.session_state:
        st.session_state[KEY_PENDING_CLASSIFICATION] = None


def bump_assessment_cache() -> None:
    """Call after mutating assessments so cached reads refresh."""
    st.session_state[KEY_ASSESSMENT_CACHE_BUMP] = int(st.session_state[KEY_ASSESSMENT_CACHE_BUMP]) + 1


def assessment_cache_version() -> int:
    return int(st.session_state[KEY_ASSESSMENT_CACHE_BUMP])


def dismiss_onboarding() -> None:
    st.session_state[KEY_ONBOARDING_DISMISSED] = True


def is_onboarding_dismissed() -> bool:
    return bool(st.session_state[KEY_ONBOARDING_DISMISSED])


def get_theme_mode() -> ThemeMode:
    raw = st.session_state[KEY_THEME]
    return "dark" if raw == "dark" else "light"


def set_theme_mode(mode: ThemeMode) -> None:
    st.session_state[KEY_THEME] = mode


def get_selected_correlation_filter() -> str:
    return str(st.session_state[KEY_SELECTED_CORRELATION] or "").strip()


def set_selected_correlation_filter(value: str) -> None:
    st.session_state[KEY_SELECTED_CORRELATION] = value.strip()


def get_selected_assessment_id() -> int | None:
    raw = st.session_state[KEY_SELECTED_ASSESSMENT_ID]
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def set_selected_assessment_id(assessment_id: int | None) -> None:
    st.session_state[KEY_SELECTED_ASSESSMENT_ID] = assessment_id


def clear_pending_classification() -> None:
    st.session_state[KEY_PENDING_CLASSIFICATION] = None
