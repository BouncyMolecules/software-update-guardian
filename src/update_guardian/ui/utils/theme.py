"""Professional navy + teal regulatory theme — complements Streamlit layout and light/dark modes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from update_guardian.ui.utils.session import ThemeMode

# Navy / slate foundation + clinical teal accent (WCAG-conscious pairings).
_LIGHT = {
    "bg_app": "#f4f7fb",
    "bg_card": "#ffffff",
    "bg_sidebar": "#eef2f7",
    "text": "#0f172a",
    "muted": "#475569",
    "accent": "#0d9488",
    "accent_soft": "#ccfbf1",
    "border": "#cbd5e1",
    "navy": "#1e3a5f",
    "on_primary": "#0f172a",
    "shadow": "rgba(15, 23, 42, 0.06)",
}

_DARK = {
    "bg_app": "#0b1220",
    "bg_card": "#111b2d",
    "bg_sidebar": "#0f172a",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "accent": "#2dd4bf",
    "accent_soft": "#134e4a",
    "border": "#334155",
    "navy": "#38bdf8",
    "on_primary": "#042f2e",
    "shadow": "rgba(0, 0, 0, 0.35)",
}


def apply_theme(mode: ThemeMode) -> None:
    """Inject typography, spacing, and semantic colors for a trustworthy GxP-style shell."""
    t = _DARK if mode == "dark" else _LIGHT
    accent_glow = f"{t['accent_soft']}66"
    st.markdown(
        f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

            html, body, [class*="css"] {{
                font-family: 'DM Sans', 'Segoe UI', system-ui, -apple-system, sans-serif;
            }}

            .stApp {{
                background: radial-gradient(1200px 600px at 10% -10%, {accent_glow}, transparent),
                            linear-gradient(180deg, {t["bg_app"]} 0%, {t["bg_app"]} 100%);
                color: {t["text"]};
            }}

            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, {t["bg_sidebar"]} 0%, {t["bg_sidebar"]} 100%);
                border-right: 1px solid {t["border"]};
            }}

            [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label {{
                color: {t["text"]};
            }}

            div.block-container {{
                padding-top: 1.25rem;
                padding-bottom: 2.5rem;
                max-width: 1200px;
            }}

            h1, h2, h3 {{
                letter-spacing: -0.02em;
                font-weight: 600;
                color: {t["text"]};
            }}

            h1 {{
                font-size: 1.85rem;
                border-bottom: 2px solid {t["accent"]};
                padding-bottom: 0.35rem;
                margin-bottom: 1rem;
            }}

            h2 {{ font-size: 1.35rem; margin-top: 1.5rem; }}
            h3 {{ font-size: 1.1rem; margin-top: 1rem; }}

            [data-testid="stMetricValue"] {{
                color: {t["navy"]};
                font-weight: 700;
            }}

            [data-testid="stMetricLabel"] {{
                color: {t["muted"]};
                text-transform: uppercase;
                font-size: 0.75rem;
                letter-spacing: 0.06em;
            }}

            div[data-testid="stExpander"] details {{
                background-color: {t["bg_card"]};
                border: 1px solid {t["border"]};
                border-radius: 8px;
            }}

            .ug-banner {{
                background: {t["bg_card"]};
                border: 1px solid {t["border"]};
                border-left: 4px solid {t["accent"]};
                border-radius: 10px;
                padding: 1.25rem 1.5rem;
                margin-bottom: 1.25rem;
                box-shadow: 0 6px 24px {t["shadow"]};
            }}

            .stButton button[kind="primary"] {{
                background-color: {t["accent"]};
                border-color: {t["accent"]};
                color: {t["on_primary"]};
                font-weight: 600;
            }}

            .stButton button[kind="primary"]:hover {{
                filter: brightness(1.05);
            }}

            [data-testid="stDataFrame"] {{
                border: 1px solid {t["border"]};
                border-radius: 8px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def onboarding_banner_class() -> str:
    """CSS class name for the onboarding callout wrapper."""
    return "ug-banner"
