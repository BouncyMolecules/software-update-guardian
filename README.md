# Software Update Guardian

**Explainable triage for remote software updates** in settings where informal “it’s only a patch” judgments collide with obligations for **traceability**, **controlled change narratives**, and **cross-functional alignment**—Regulatory Operations, Quality Systems, Clinical IT, and digital clinical platforms working from the same factual baseline.

Patches and platform releases routinely arrive with **partial context**: who assessed impact, how severity was inferred, and which factors drove a classification disappear into mail threads or local notes. Weeks later, management review, vendor oversight, or an audit asks for **the contemporaneous rationale**. This repository is a **production-minded portfolio build**: a deterministic rules engine with stable identifiers, weighted contributions to a risk band, append-style persistence, and a Streamlit front end—with **domain logic isolated from the UI**, **mypy strict** typing, **Ruff-clean** linting, automated tests, and CI on Python 3.11.

Use it as **internal decision support**, training sandboxes, or a hosted demo—not as a validated system of record unless your organization maps it explicitly into IQ/OQ/PQ and procedural controls.

**Portfolio:** [LinkedIn — Ela Halilovic](https://www.linkedin.com/in/ela-halilovic) · [Clinical Future (Substack)](https://clinicalfuture.substack.com) · [GitHub — BouncyMolecules](https://github.com/BouncyMolecules)

---

## Try the live demo

**Hosted Streamlit (replace after deployment):**

`https://YOUR_APP.streamlit.app`

For example, once published under Community Cloud following your repo name:  
`https://software-update-guardian.streamlit.app`

**Suggested checks:** run through **Monitored portfolio** with at least two saved assessments, submit **Classify update** with different factor combinations, then open **History & audit** and compare the engine trace with the application audit tab. Banner any public instance as **non-production** and use synthetic identifiers only—Community Cloud persistence and access controls are suited to demonstration, not to confidential trial or patient data without additional architecture.

Pin Python **3.11+** on the host, install from this repository with **`pip install .`** (omit `[dev]`), configure secrets outside the codebase, and treat hosting choices like any other computerized system classification in your **GAMP**/risk posture.

---

## Screenshots *(placeholders for portfolio packets)*

Add PNG or WebP files under **`docs/screenshots/`** (or swap paths to your CDN). Each block below describes what reviewers should **see** in the eventual capture—no substitute for capturing your own branded deployment.

### 1 — Monitored portfolio (dashboard)

**Placeholder:** `docs/screenshots/01-dashboard.png`  
**Caption:** Windowed KPIs across recent persisted assessments—elevated versus borderline versus routine bands, normalized score trajectory, and a concise table of the latest classifications. Signals that the UI is aggregation and review support, not a replacement for validated trending in your QMS.

### 2 — Classify update (structured intake)

**Placeholder:** `docs/screenshots/02-classify.png`  
**Caption:** Single-pass capture of device and update metadata flowing into the rules engine—inputs anchored to reproducible scoring and stable rule IDs suitable for referencing in internal change wording or appendix tables before formal templates are finalized.

### 3 — Transparent rationale & factors

**Placeholder:** `docs/screenshots/03-rationale.png`  
**Caption:** Band outcome with contributing rules, points, and categories laid out for professional scrutiny framing draws on publicly discussed concepts (risk management, change control, vigilance-aware thinking) while remaining **illustrative**: outcomes still require sponsor- and geography-specific Regulatory and Quality sign-off.

### 4 — History & audit alignment

**Placeholder:** `docs/screenshots/04-history.png`  
**Caption:** Immutable saved snapshot alongside the **deterministic decision trace** and **system audit rows** retrieved from persistence—emphasizes append-only narrative suitable for exporting into internal assessment packs or training scenarios rather than asserting Part 11–ready signatures.

Until files exist at these paths, the references are intentional scaffolding for hiring packets and stakeholder decks.

---

## What it addresses

| Friction | How the tool responds |
|---------|----------------------|
| Inconsistent first-pass triage | Shared rule set, explicit contributions, reproducible totals into named bands—not ad hoc verbal labels alone. |
| Weak narrative traceability | Engine audit trail plus stored JSON aligned to the classification bundle; correlate with persistence audit events. |
| Cross-functional deadlock | Stable vocabulary (rule IDs, categories, bands) usable by Clinical Operations, CRO-facing IT, QA, and sponsor digital leads before escalation paths harden in email. |

---

## What it does technically

- **Deterministic classification** into risk **bands** from an explicit rule library and weighted contributions (`src/update_guardian/core/classifier.py`).
- **SQLite** persistence via SQLModel—swap **`UPDATE_GUARDIAN_DATABASE_URL`** for a managed DB when redundancy or concurrency demands it.
- **Streamlit** UI: dashboard, classify, and history—with **`StorageService` injected into `render(storage=…)`** so pages do not depend on implicit singletons (`ui/` versus `core/` separation).
- **Configuration** via `pydantic-settings` and prefixed environment variables (**`UPDATE_GUARDIAN_*`**).
- **Wheel typing:** **`update_guardian/py.typed`** is included so downstream projects can strict-type against the package surface.

[![CI](https://github.com/BouncyMolecules/software-update-guardian/actions/workflows/ci.yml/badge.svg)](https://github.com/BouncyMolecules/software-update-guardian/actions/workflows/ci.yml)

---

## Engineering and quality posture

- **Install:** `pip install -e ".[dev]"` pulls runtime deps plus **`mypy`**, **`ruff`**, **`pytest`**, **`pytest-cov`**, **`pandas-stubs`**, **`types-python-dateutil`** — enough for **`mypy --strict`** to mirror CI locally without ad hoc stub installs.
- **CI:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs **Ruff** lint, **Ruff format --check**, **`mypy --strict`**, and **pytest** on pushes and PRs (**Python 3.11**).
- **SQLite tests:** Dedicated engines and **`StorageService`** instances per test; **`pythonpath = ["src"]`** in **`pyproject.toml`** so **`pytest`** works from a clean clone after **`pip install -e ".[dev]"`**.
- **Coverage honesty:** **`[tool.coverage.run].omit`** excludes the Streamlit shell and **`ui/`** pages; **`fail_under`** applies to **`core/`** and **`config.py`**—adjust in lockstep with **`pytest … --cov-report=term`**.

---

## Regulatory and GxP posture *(plain language)*

This section states limitations clearly so hiring managers and compliance-minded reviewers see proportionate framing—not implied certifications.

| Topic | Position |
|--------|----------|
| **Intended use** | **Decision support**, training, and capability demonstration—not a validated medical device, not a substitute for qualified regulatory judgment or your approved procedures. |
| **Validation lifecycle** | In GxP contexts, classify the tool under your **CSV / GAMP** approach: IQ/OQ/PQ scope, segregation of duties, backup and retention, and SDLC records are organizational deliverables—not claims made by this README. |
| **Rules & thresholds** | Implemented scoring exemplifies a transparent pattern; thresholds and rule text require **document-controlled** endorsement when used beyond sandboxes—revisit when policy, jurisdictions, or product lines shift. |
| **Data residency & classification** | Default SQLite is local to the process; apply encryption, network zoning, identity, and data-classification discipline for identifiers that may touch **trial subjects**—this codebase does not implement enterprise security suites. |
| **21 CFR Part 11 / EU Annex 11** | No electronic signature workflow or Part 11 feature marketing. Where outputs qualify as regulated records in your interpretation, map controls explicitly in **Regulatory Affairs** and **QA** tooling assessments. |

All narrative and numeric outputs merit review alongside **clinical context**, reporting obligations (including vigilance-themed considerations where applicable), and agreed internal standards.

---

## Quick start

**Prerequisite:** Python **3.11+**

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows Command Prompt
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

**Environment**

```powershell
copy .env.example .env   # PowerShell / cmd — from repo root
```

```bash
cp .env.example .env      # macOS / Linux
```

Edit **`.env`** for log level, database URL, and optional organization display label. Never commit secrets, production JDBC-style URLs with credentials, or subject-identifying sample data.

**Run locally**

Preferred with the packaged console script:

```bash
update-guardian
```

Equivalent explicit invocation:

```bash
python -m streamlit run src/update_guardian/ui/app.py
```

From repository root **without** an editable install, the thin wrapper **`app.py`** is also supported if **`PYTHONPATH`** includes **`src`** or dependencies are installed as a package—**`pip install -e .`** avoids import drift with **mypy**/**pytest**.

---

## Deployment

### Streamlit Community Cloud *(demonstration)*

Connect this GitHub repository; select **Python 3.11** and point the main entry to **`src/update_guardian/ui/app.py`** (or to root **`app.py`** if your host requires a repo-root starter file—as long as the package is on **`PYTHONPATH`** or installed). Move secrets to platform **Secrets** (**`UPDATE_GUARDIAN_DATABASE_URL`**, **`UPDATE_GUARDIAN_ORGANIZATION_NAME`**, future keys)—never bake credentials into the image or enduring branch history. Label the deployment **non-production** and restrict access if screenshots may include internal naming.

### Internal / governed hosting

- Build an artefact layer with **`pip install .`** (omit **`[dev]`**).
- Terminate TLS at your ingress; implement **SSO**, **RBAC**, and segmentation consistent with Annex 11–style expectations where applicable at your organization—not claimed here line-by-line.
- Prefer **managed relational** backends when concurrent writers or RPO/RTO commitments exceed single-file SQLite practicality; pin wheels and retain **SBOM** or digest evidence with change tickets.

### Operational hygiene

- Steady-state: **`UPDATE_GUARDIAN_LOG_LEVEL=WARNING`** or **`ERROR`**, centralized log shipping, retention aligned to records policy.
- **Classifier or rule changes**: treat as **controlled software revisions**—regression **`pytest`** runs, documented configuration deltas, stakeholder communication according to **SOP**.
- Backup database files or DBaaS snapshots per **records management** directives.

---

## Development and verification

From an activated virtual environment with **`pip install -e ".[dev]"`** installed:

```bash
ruff check .
ruff format --check src tests
mypy --strict
pytest -q
```

CI runs the equivalent gates on **Ubuntu** with Python **3.11**. Optional enforced coverage slice (after **`[tool.coverage]`** omit rules):

```bash
pytest -q --cov=update_guardian --cov-config=pyproject.toml --cov-fail-under=80
```

---

## Packaging metadata

Publication-oriented fields match **`pyproject.toml`** (**PEP 621**):

| Field | Value |
|--------|--------|
| **Name** | **`software-update-guardian`** |
| **Version** | **`0.1.0`** (bump releases via release tags when distributing) |
| **Summary** | See **`[project.description]`** in **`pyproject.toml`** — deterministic, explainable triage for regulated-ops audiences. |
| **Requires-Python** | **`>=3.11`** |
| **License** | **Proprietary** (see below) |
| **Authors / maintainers** | **Ela Halilovic** |
| **Homepage / repository** | **`https://github.com/BouncyMolecules/software-update-guardian`** |
| **Entry script** | **`update-guardian`** → **`update_guardian.main:launch_ui`** |
| **Optional dev extra** | **`.[dev]`** — **mypy**, **ruff**, **pytest**, **pytest-cov**, typing stubs (**`pandas-stubs`**, **`types-python-dateutil`**) |

**Build backend:** Hatchling (`hatchling.build`). **Wheel:** packages under **`src/update_guardian`**, **`py.typed`** forced into the wheel for type consumers.

---

## Project layout

```text
src/update_guardian/
  core/           # Models, classifier, storage — no Streamlit imports
  ui/             # Streamlit app shell and pages
  config.py       # pydantic-settings
  main.py         # Logging + launcher
tests/
```

---

## License

**Proprietary** — suitable for portfolio display. Redistribution or commercial reuse requires explicit permission from the author.

---

## Disclaimer

This application assists **internal** decision-making and professional development only. Outputs depend on **user-supplied inputs** and **versioned rule configuration**. Determinations affecting reporting, vigilance submissions, labeling, clinical conduct, or field action require appropriately qualified personnel and geography-specific statutes and **SOPs**. **Not legal or regulatory advice.**
