"""Main Streamlit shell — navigation, onboarding, theming, and page routing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import streamlit as st

from update_guardian.core.storage import StorageService
from update_guardian.main import configure_logging
from update_guardian.ui.pages import dashboard, history, upload
from update_guardian.ui.utils import onboarding, theme
from update_guardian.ui.utils import session as session_utils

if TYPE_CHECKING:
    from update_guardian.ui.utils.session import ThemeMode

_SESSION_KEY_STORAGE = "ug_storage_service"


def _storage_for_session() -> StorageService:
    """Composition root: one ``StorageService`` per browser session (Streamlit rerun-safe)."""
    existing = st.session_state.get(_SESSION_KEY_STORAGE)
    if isinstance(existing, StorageService):
        return existing
    svc = StorageService()
    svc.init_db()
    st.session_state[_SESSION_KEY_STORAGE] = svc
    return svc


logger = logging.getLogger(__name__)

_PAGE_REGISTRY = {
    "Dashboard": dashboard.render,
    "Classify update": upload.render,
    "History & audit": history.render,
}


def _sync_theme_sidebar() -> None:
    idx = 0 if session_utils.get_theme_mode() == "light" else 1
    appearance = st.sidebar.selectbox(
        "Appearance",
        ["Light", "Dark"],
        index=idx,
        help="Applies a navy + teal regulatory shell. Browser `config.toml` base theme may still influence widgets.",
    )
    want: ThemeMode = "light" if appearance == "Light" else "dark"
    if want != session_utils.get_theme_mode():
        session_utils.set_theme_mode(want)
        st.rerun()


def run_app() -> None:
    """Primary Streamlit entrypoint (invoked from ``app.py`` or packaged launcher)."""
    configure_logging()
    logger.debug("Rendering Streamlit shell")

    st.set_page_config(
        page_title="Software Update Guardian",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    session_utils.ensure_defaults()
    theme.apply_theme(session_utils.get_theme_mode())
    onboarding.hydrate_onboarding_from_disk()

    st.sidebar.markdown("### Software Update Guardian")
    st.sidebar.caption("Regulatory decision-support · not legal advice")
    _sync_theme_sidebar()
    st.sidebar.divider()
    choice = st.sidebar.radio(
        "Navigate",
        list(_PAGE_REGISTRY.keys()),
        index=0,
        label_visibility="collapsed",
    )

    onboarding.render_onboarding_carousel()
    _PAGE_REGISTRY[choice](_storage_for_session())
