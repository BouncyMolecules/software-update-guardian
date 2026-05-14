"""Non-UI entry points and launcher helpers."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from update_guardian import __version__
from update_guardian.config import get_settings


def configure_logging() -> None:
    """Configure root logging from application settings."""
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _package_streamlit_app_path() -> Path:
    """Resolve the packaged Streamlit driver next to this module."""
    return Path(__file__).resolve().parent / "ui" / "app.py"


def launch_ui() -> None:
    """Launch Streamlit using the packaged UI entry (works from any working directory)."""
    configure_logging()
    log = logging.getLogger(__name__)
    target = _package_streamlit_app_path()
    if not target.is_file():
        log.error("Packaged UI entry missing at %s", target)
        raise SystemExit(1)
    log.info("Starting Streamlit UI (%s)", target)
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(target)],
        )
    )


def main() -> None:
    """CLI entry: print version and usage."""
    configure_logging()
    print(f"Software Update Guardian v{__version__}")
    print("Launch the UI with:")
    print(f"  streamlit run {_package_streamlit_app_path()}")
    print("Or install the package and run:")
    print("  update-guardian")
