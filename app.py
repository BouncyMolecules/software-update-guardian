"""Hosted and local Streamlit entry point for Software Update Guardian.

This module is the single deployment entry point for Streamlit Community Cloud
(``streamlit run app.py`` from the repository root) and for equivalent local
workflows. It performs a small, explicit **path bootstrap** so the
``src``-layout package ``update_guardian`` is importable without relying on an
editable install or custom ``PYTHONPATH`` in the host environment—behavior that
differs between developer machines and managed PaaS runtimes.

For validation and audit: the runtime manipulates ``sys.path`` only to mirror
what ``pip install`` / ``pytest`` already do via configuration; application
logic remains in ``update_guardian.*``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve repository root and register ``src/`` on ``sys.path``
# ---------------------------------------------------------------------------
# Streamlit Community Cloud clones the repo and starts the app from the root.
# Unlike a local ``pip install -e .`` (or IDE test runner using ``pythonpath``),
# the cloud process does not automatically place ``src/`` on the import path.
# Prepending the resolved ``src`` directory makes ``import update_guardian`` and
# all first-party imports inside the package succeed on Windows, Linux, and
# macOS. We use ``Path.resolve()`` so symlinks and ``..`` segments do not
# introduce ambiguous locations in logs or duplicate path entries.

_ROOT_DIR = Path(__file__).resolve().parent
_SRC_DIR = _ROOT_DIR / "src"
_SRC_DIR_STR = str(_SRC_DIR)

if not _SRC_DIR.is_dir():
    print(
        "[software-update-guardian] ERROR: expected a ``src`` directory next to "
        f"``app.py`` at {_SRC_DIR}. The repository may be incomplete or this "
        "entry point may have been moved.",
        file=sys.stderr,
    )
    raise SystemExit(1)

if _SRC_DIR_STR not in sys.path:
    sys.path.insert(0, _SRC_DIR_STR)

# One concise line per process helps operators correlate container logs with a
# successful bootstrap without spamming every Streamlit script rerun (the env
# var persists for the lifetime of the Streamlit server process).
if not os.environ.get("SOFTWARE_UPDATE_GUARDIAN_BOOTSTRAP_LOGGED"):
    os.environ["SOFTWARE_UPDATE_GUARDIAN_BOOTSTRAP_LOGGED"] = "1"
    print(
        "[software-update-guardian] Bootstrap complete · "
        f"repo_root={_ROOT_DIR} · import_root={_SRC_DIR}",
        file=sys.stderr,
    )

try:
    from update_guardian.ui.app import run_app
except ModuleNotFoundError as exc:
    print(
        "[software-update-guardian] ERROR: could not import ``update_guardian`` "
        f"after adding ``{_SRC_DIR_STR}`` to ``sys.path``. "
        "Confirm ``src/update_guardian`` is present in the deployment and that "
        "dependencies declared for the app (e.g. in ``requirements.txt`` / "
        "``pyproject.toml``) are installed in the Streamlit environment.\n"
        f"Details: {exc}",
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

# Streamlit executes this file as ``__main__`` on each run; keep the surface
# minimal and delegate all product behavior to ``update_guardian.ui.app``.
run_app()
