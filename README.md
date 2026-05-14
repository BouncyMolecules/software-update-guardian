# Software Update Guardian

**Structured decision support for remote software updates** in environments where **traceability**, **cross-functional alignment**, and **controlled change narratives** matter as much as release velocity.

Regulatory Operations and Quality Systems teams routinely face the same friction: an engineering or clinical-systems patch arrives with incomplete context, stakeholders interpret risk differently, and the **why we classified it this way** story is reconstructed weeks later from email. This application provides a **deterministic, explainable triage workflow**—rule identifiers, weighted contributions, risk bands, and append-style history—so Regulatory, Quality, Clinical IT, and Digital Transformation leads can **anchor discussions in documented drivers** before commitments appear in technical files, change records, or field communications.

It is built as a **production-minded portfolio artifact**: strict static typing, lint-clean Python, **core logic isolated from the Streamlit UI**, automated tests, and persistence suited to demonstration and internal piloting (SQLite by default; replaceable via configuration).

---

## Live demo

**Hosted Streamlit application (replace after deployment):**

`https://YOUR_APP.streamlit.app`

Example pattern once published: `https://software-update-guardian.streamlit.app`

Pin Python and dependency versions on the host, restrict access appropriately, and label non-production deployments clearly. Map hosting choices to your internal validation or risk assessment norms—Community Cloud is convenient for visibility; **regulated production** typically belongs on governed infrastructure.

---

## Screenshots

Add PNG or WebP captures under `docs/screenshots/` (or link to your CDN). Captions below describe the narrative each image should convey for hiring packets and stakeholder decks.

| Preview | Caption |
|--------|---------|
| ![Dashboard — replace with capture](docs/screenshots/01-dashboard.png) | **Operational dashboard** — distribution of recent classifications, band summaries, and navigation into supporting detail for QA and Regulatory review. |
| ![Classify update — replace with capture](docs/screenshots/02-classify.png) | **Structured intake** — device and update metadata captured in one pass; inputs feed a reproducible scoring path tied to stable rule IDs for change control references. |
| ![Explainable rationale — replace with capture](docs/screenshots/03-rationale.png) | **Transparent rationale** — contributions and references surfaced for professional scrutiny; framing draws on public regulatory concepts (e.g., QMS, vigilance themes, software lifecycle posture) and remains **illustrative**, not determinative for any single submission. |
| ![History and audit trail — replace with capture](docs/screenshots/04-history.png) | **Assessment history** — append-style records supporting export and inclusion in internal assessment packages or training scenarios. |

Until images exist, paths above are intentional placeholders.

---

## What it solves

- **Inconsistent first-pass triage** — Teams default to informal labels (“minor patch,” “just IT”) without a shared, versioned interpretation baseline.
- **Weak narrative traceability** — Decisions made under time pressure are hard to reconstruct for audits, CAPA, or management review.
- **Costly cross-functional cycling** — Clinical operations platforms, CRO interfaces, and sponsor quality systems require a **common vocabulary** (rules, bands, documented factors) before formal documentation or escalation paths lock in.

---

## What the tool does

- **Deterministic classification** of a described software update into risk **bands** using an explicit rule library and weighted contributions (`src/update_guardian/core/classifier.py`).
- **Stable rule identifiers** suitable for CSV export, change records, and internal CAPA cross-references.
- **SQLite persistence** via SQLModel for assessments and audit-oriented storage; swap `UPDATE_GUARDIAN_DATABASE_URL` when your architecture requires a managed database.
- **Streamlit application** with **Dashboard**, **Classify update**, and **History** flows—UI code under `ui/`, domain logic importable and covered by tests.

---

## Engineering and quality posture

- **`pip install -e ".[dev]"`** pulls lint/test tools plus **stub packages** (`pandas-stubs`, `types-fpdf2`, …) so **`python -m mypy --strict`** is reproducible—runtime `pip install -e .` alone does not guarantee clean typing against pandas-heavy UI modules.
- **mypy strict** over `src/update_guardian` (see `[tool.mypy]` in `pyproject.toml`); **ruff** for lint and import hygiene.
- **Separation of concerns**: core models, classifier, and storage are free of Streamlit imports.
- **Configuration** via `pydantic-settings` and environment variables (`UPDATE_GUARDIAN_*`).

This balance is deliberate: hiring managers in Regulatory Operations and Digital Transformation increasingly expect candidates who can **translate GxP expectations into software structure**, not only slide decks.

---

## GxP / regulatory compliance posture

Plain language, no implied certifications:

| Topic | Posture |
|--------|---------|
| **Intended use** | **Internal decision support**, training, and portfolio demonstration—not a validated medical device, not a substitute for qualified regulatory judgment or controlled company procedures. |
| **Validation** | If deployed where GxP applies, treat the application like any other **GAMP Category** tool: IQ/OQ/PQ, access control, backup and retention, and SDLC controls are **organizational** responsibilities. |
| **Rules and thresholds** | Implemented scoring and bands are **exemplary**; they require sponsor/device-specific review, approval under **document control**, and periodic re-evaluation when policies or markets shift. |
| **Data** | Default SQLite stores data locally to the process environment. Apply encryption at rest, network segmentation, and data classification appropriate to **PII/PHI** and trial subjects—this repository does not implement enterprise security by itself. |
| **21 CFR Part 11 / Annex 11** | No electronic signatures or Part 11 feature claims. If outputs become **regulated records**, map requirements explicitly in your quality system. |

All outputs warrant review by **Regulatory Affairs**, **Quality Assurance**, and operational owners familiar with the product, geography, and pharmacovigilance or device reporting obligations.

---

## Quick start

**Prerequisites:** Python **3.11+**

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

**Environment**

```powershell
# Windows (PowerShell / cmd)
copy .env.example .env
```

```bash
# macOS / Linux
cp .env.example .env
```

Edit `.env` for log level, database URL, and optional organization display string. Never commit secrets or production connection strings.

**Run the UI**

```bash
update-guardian
```

Alternative from the repository root after an editable install:

```bash
python -m streamlit run src/update_guardian/ui/app.py
```

For ad hoc runs without installing the package, prefer `pip install -e .` so imports resolve consistently; otherwise set `PYTHONPATH` to `src` from the repo root with the understanding that tooling (mypy, pytest) already targets `src/` layout.

---

## Deployment

### Streamlit Community Cloud (demonstration)

- Connect the GitHub repository; select **Python 3.11**.
- Main file: `src/update_guardian/ui/app.py` (or a thin wrapper at repo root if your host requires a single entry filename).
- Move sensitive values to the platform **Secrets** store (`UPDATE_GUARDIAN_DATABASE_URL`, `UPDATE_GUARDIAN_ORGANIZATION_NAME`, and any future keys)—do not embed credentials in the image or public branch history.
- Use synthetic or anonymized data for public demos; banner the environment as **non-production**.

### Internal / enterprise hosting

- Build an image with `pip install .` (omit `[dev]` in production layers).
- Terminate TLS at your ingress; enforce **SSO**, **RBAC**, and network policies aligned to your security standard.
- Prefer a **managed relational database** when multiple instances write concurrently or when backup RPO/RTO commitments exceed single-file SQLite practicality.
- Pin dependency versions in the deployment artifact and record **SBOM** or lockfile digest in the release record alongside change tickets.

### Operational hygiene

- Set `UPDATE_GUARDIAN_LOG_LEVEL` to `WARNING` or `ERROR` in steady-state production to limit noise; forward logs to your centralized observability stack with retention per SOP.
- Back up database files or managed instances according to records-management policy.
- Treat classifier and threshold changes as **controlled software changes**: regression testing, approved configuration records, and communication to Operations stakeholders.

---

## Development and quality gates

Use **`pip install -e ".[dev]"`** once per environment so mypy sees optional stub packages aligned with Streamlit/pandas transitive imports.

```bash
python -m ruff check .
python -m ruff format --check src tests
python -m mypy --strict
python -m pytest -q
```

**Coverage (truthful gate):** pytest-cov reads `[tool.coverage.*]` from `pyproject.toml`. The Streamlit launcher and `ui/` tree are **omitted from measurement**—automated tests target the domain layer (`core/`, `config.py`), while the UI is exercised manually or in hosted demos. Enforce the configured threshold with:

```bash
python -m pytest -q --cov=update_guardian --cov-config=pyproject.toml --cov-fail-under=78
```

(`fail_under` is defined next to `omit` under `[tool.coverage]`—raise it only when new tests materially cover previously omitted paths or extend core coverage.)

---

## Project layout

```text
src/update_guardian/
  core/           # Models, classifier, storage (no Streamlit)
  ui/             # Streamlit entrypoint and pages
  config.py       # pydantic-settings
  main.py         # Logging and UI launcher
tests/
```

---

## License

**Proprietary** — suitable for portfolio display. Redistribution and commercial use require explicit permission from the author.

---

## Attribution

- **LinkedIn:** [Ela Halilovic](https://www.linkedin.com/in/ela-halilovic)
- **Clinical Future (Substack):** [clinicalfuture.substack.com](https://clinicalfuture.substack.com)
- **GitHub:** [BouncyMolecules](https://github.com/BouncyMolecules)

---

## Disclaimer

This application supports **internal** decision-making, capability demonstration, and professional development only. Classification outputs depend on **user-supplied inputs** and **configurable rules**. **Final regulatory determinations** require qualified Regulatory and Quality review and may depend on jurisdiction, product classification, clinical context, and approved procedures. **Not legal or regulatory advice.**
