"""First-run onboarding carousel — session UI with optional on-disk dismissal (per OS user profile)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TypedDict

import streamlit as st

from update_guardian.ui.utils import session as session_utils
from update_guardian.ui.utils import theme

logger = logging.getLogger(__name__)

_KEY_CAROUSEL_STEP = "ug_onboarding_carousel_step"
_PREF_SCHEMA_VERSION = 1


class _Step(TypedDict):
    title: str
    body_html: str


_STEPS: tuple[_Step, ...] = (
    {
        "title": "Welcome and purpose",
        "body_html": (
            "<p>Software Update Guardian is a structured workspace for <strong>software-change "
            "classification decision-support</strong> in regulated product settings. It helps "
            "teams align on facts, rule logic, and traceable outputs.</p>"
            "<p>All results are <strong>heuristic and informational only</strong>. They do not "
            "replace qualified Regulatory, Quality, or Clinical judgment, your approved procedures, "
            "or obligations under applicable regulations and standards.</p>"
        ),
    },
    {
        "title": "How to classify an update",
        "body_html": (
            "<p>Use <strong>Classify update</strong> to capture a concise, factual description of "
            "the change and relevant system context. Complete the prompts consistently so the rules "
            "engine can apply the same logic on each run.</p>"
            "<p>Assign and reuse a <strong>correlation identifier</strong> wherever your "
            "organization ties this assessment to change control, validation, or release records. "
            "Consistency supports audit readiness and cross-referencing.</p>"
        ),
    },
    {
        "title": "How risk scoring works",
        "body_html": (
            "<p>Risk posture is derived from a <strong>deterministic rules engine</strong> with "
            "explicit contributions. Each result should be readable as an explainable rollup of "
            "those contributions—not as a surrogate for formal risk-management deliverables "
            "(for example, your hazard analysis or benefit-risk conclusions).</p>"
            "<p>Treat numeric or banded summaries as prioritization aides for human review "
            "and documentation—not as standalone compliance decisions.</p>"
        ),
    },
    {
        "title": "History and audit use",
        "body_html": (
            "<p><strong>History &amp; audit</strong> retains assessments for traceability within "
            "this application. Use it to review prior decisions, support internal reviews, and "
            "maintain lineage alongside your authorised record-keeping practices.</p>"
            "<p>Operational retention, archival, e-signatures, and system validation remain "
            "governed by your Quality System and IT policies. Export or copy content into "
            "controlled repositories when your SOPs require it.</p>"
        ),
    },
)


def _preferences_path() -> Path:
    return Path.home() / ".software-update-guardian" / "preferences.json"


def hydrate_onboarding_from_disk() -> None:
    """If the user previously completed onboarding, keep the carousel dismissed for this session."""
    path = _preferences_path()
    if not path.is_file():
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Could not read onboarding preferences from %s: %s", path, exc)
        return
    if raw.get("onboarding_dismissed") is True:
        session_utils.dismiss_onboarding()


def _persist_onboarding_dismissed() -> None:
    path = _preferences_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": _PREF_SCHEMA_VERSION,
            "onboarding_dismissed": True,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not persist onboarding dismissal to %s: %s", path, exc)


def _ensure_carousel_step() -> None:
    if _KEY_CAROUSEL_STEP not in st.session_state:
        st.session_state[_KEY_CAROUSEL_STEP] = 1


def _step_indicator_html(step: int) -> str:
    parts: list[str] = []
    for i in range(1, len(_STEPS) + 1):
        cls = "ug-onboarding-dot active" if i == step else "ug-onboarding-dot"
        parts.append(f'<span class="{cls}" aria-hidden="true"></span>')
    return f'<div class="ug-onboarding-dots" role="presentation">{"".join(parts)}</div>'


def _card_markdown(step: int) -> str:
    entry = _STEPS[step - 1]
    shell = theme.onboarding_carousel_shell_class()
    meta = f"Step {step} of {len(_STEPS)} — Orientation"
    return f"""
<div class="{shell}">
  <p class="ug-onboarding-meta">{meta}</p>
  <h3>{entry["title"]}</h3>
  <div class="ug-onboarding-body">
    {entry["body_html"]}
  </div>
  {_step_indicator_html(step)}
</div>
"""


def render_onboarding_carousel() -> None:
    """Show a one-time (per profile) four-step onboarding carousel above page content."""
    if session_utils.is_onboarding_dismissed():
        return

    _ensure_carousel_step()
    step = int(st.session_state[_KEY_CAROUSEL_STEP])
    step = max(1, min(step, len(_STEPS)))
    st.session_state[_KEY_CAROUSEL_STEP] = step

    st.markdown(_card_markdown(step), unsafe_allow_html=True)

    prev_c, _spacer, next_c = st.columns([1, 2, 1])
    with prev_c:
        go_back = st.button(
            "Back",
            key="ug_onboarding_back",
            disabled=step <= 1,
            help="Return to the previous orientation step.",
        )
    with next_c:
        if step < len(_STEPS):
            go_next = st.button(
                "Next",
                key="ug_onboarding_next",
                help="Continue orientation.",
            )
            if go_next:
                st.session_state[_KEY_CAROUSEL_STEP] = step + 1
                st.rerun()
        else:
            finish = st.button(
                "Got it — let's get started",
                key="ug_onboarding_finish",
                type="primary",
                help="Dismiss this orientation for this browser profile. You can still use all features.",
            )
            if finish:
                session_utils.dismiss_onboarding()
                _persist_onboarding_dismissed()
                st.rerun()

    if go_back:
        st.session_state[_KEY_CAROUSEL_STEP] = step - 1
        st.rerun()
