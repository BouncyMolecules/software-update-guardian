"""Main Streamlit shell — navigation, onboarding, theming, and page routing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import streamlit as st

from update_guardian.main import configure_logging
from update_guardian.ui.pages import dashboard, history, upload
from update_guardian.ui.utils import session as session_utils
from update_guardian.ui.utils import theme

if TYPE_CHECKING:
    from collections.abc import Callable

    from update_guardian.ui.utils.session import ThemeMode

logger = logging.getLogger(__name__)

_PAGE_REGISTRY: dict[str, Callable[[], None]] = {
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


def _render_onboarding_banner() -> None:
    if session_utils.is_onboarding_dismissed():
        return
    st.markdown(
        f"""
        <div class="{theme.onboarding_banner_class()}">
            <p style="margin:0 0 0.6rem 0; font-size:1.05rem;">
                <strong>Welcome to Software Update Guardian</strong>
            </p>
            <p style="margin:0; color: inherit; opacity: 0.9;">
                This workspace helps structure <strong>software-update classification decision-support</strong>
                for regulated products. Results are heuristics only — qualified Regulatory and Quality
                professionals must confirm obligations under your SOPs and applicable law.
            </p>
            <p style="margin:0.6rem 0 0 0; font-size:0.95rem;">
                Start with <strong>Classify update</strong> to capture facts, then review immutable history under
                <strong>History & audit</strong>. Use correlation IDs consistently for traceability.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        "Dismiss onboarding banner",
        key="ug_dismiss_onboarding",
        help="Preference is stored for this browser session only.",
    ):
        session_utils.dismiss_onboarding()
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

    _render_onboarding_banner()
    _PAGE_REGISTRY[choice]()
