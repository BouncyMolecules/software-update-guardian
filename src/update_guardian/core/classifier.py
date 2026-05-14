"""Deterministic, explainable software-update classification and risk scoring."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

from update_guardian.core.models import (
    AuditTrailEntry,
    ClassificationBand,
    ClassificationResult,
    DeviceClass,
    DistributionScope,
    RegulatoryRuleCategory,
    RiskScore,
    RuleContribution,
    SoftwareSafetyClass,
    SoftwareUpdate,
    UpdateClassification,
    UpdateTypeIndication,
)

logger = logging.getLogger(__name__)


class AssessmentProcessingError(Exception):
    """Raised when deterministic evaluation cannot complete safely."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.detail = detail


# ---------------------------------------------------------------------------
# Rule identifiers — stable for change control, CAPA references, and CSV export
# ---------------------------------------------------------------------------

RULE_SOFTWARE_SAFETY_C_POSTURE = "R-SAF-SW-CLASS-C-POSTURE"
RULE_DEVICE_CLASS_III = "R-DEV-CLASS-III"
RULE_DEVICE_CLASS_IIB = "R-DEV-CLASS-IIB"
RULE_DISTRIBUTION_GLOBAL = "R-DIST-GLOBAL"
RULE_DISTRIBUTION_REGIONAL = "R-DIST-REGIONAL"
RULE_UPDATE_ALGORITHM = "R-TYPE-ALGORITHM"
RULE_UPDATE_ENHANCEMENT = "R-TYPE-ENHANCEMENT"
RULE_UPDATE_THIRD_PARTY = "R-TYPE-THIRD-PARTY"
RULE_UPDATE_SECURITY_PATCH = "R-TYPE-SECURITY-PATCH"
RULE_UPDATE_CONFIG_WORKFLOW = "R-TYPE-CONFIG-WORKFLOW"
RULE_MAINTENANCE_DEFECT_CORRECTION = "R-MAINT-DEFECT-CORRECTION-BASELINE"
RULE_CLINICAL_FUNCTION = "R-SAF-CLINICAL-FUNCTION"
RULE_CLINICAL_DECISION = "R-SAF-CLINICAL-DECISION"
RULE_LABELING = "R-REG-LABELING-IFU"
RULE_CONNECTIVITY = "R-NET-REMOTE-INTERFACE"
RULE_SECURITY_VULN = "R-CYB-VULNERABILITY"
RULE_DATA_INTEGRITY = "R-DI-GXP-RECORDS"
RULE_PRIOR_FIELD_ISSUES = "R-CAPA-PRIOR-FIELD"
RULE_PMS_RISK = "R-PMS-RISK-CONTROLS"
RULE_INTENDED_USE = "R-REG-INTENDED-USE"
RULE_RELEASE_NOTES_RISK_ALIGNMENT = "R-RN-PATIENT-RISK-ASSERTION"
RULE_WORKAROUND = "R-RISK-WORKAROUND-MITIGATES"
RULE_CORRECTION_REMOVAL_COMPOSITE = "R-REG-CORRECTION-REMOVAL-SIGNAL"


REF_FDA_QMS_CORRECTION = (
    "FDA QS regulation (21 CFR Part 820) distinguishes corrections/removals; reportability is "
    "fact-specific — compare to 21 CFR Part 806 concepts when health risk or requisite reporting arises."
)
REF_EU_MDR_POSTMARKET = (
    "EU MDR Art. 87-92 and implementing acts frame vigilance and field safety; significant changes "
    "may require notified body involvement per Annex VII and technical documentation updates."
)
REF_EMA_GVP_AND_QMS = (
    "EMA GVP modules and national competent authorities expect structured benefit-risk updates when "
    "safety-impacting software is distributed in the EEA."
)
REF_IEC_62304 = (
    "IEC 62304 software safety classification informs validation rigor; Class C requires strongest "
    "defense in depth."
)
REF_CYBER_POSITIONS = (
    "FDA Postmarket Cybersecurity guidance (2023+ expectations) and EU MDR Annex I cybersecurity "
    "principles drive documentation for network-enabled devices."
)

# Upper bound on simultaneously applicable **positive** points (exclusive groups take max).
_THEORETICAL_MAX_POSITIVE_POINTS = (
    12  # software Class C
    + 10  # device Class III (max of III / IIb / I)
    + 12  # distribution global (max of regional/global/single)
    + 24  # update type — algorithm worst among enumerated buckets
    + 22  # clinical function
    + 28  # clinical decisioning
    + 18  # labeling
    + 14  # connectivity
    + 20  # active cybersecurity mitigation
    + 20  # data integrity
    + 16  # prior field
    + 18  # PMS / risk controls
    + 30  # intended-use drift
    + 10  # release documentation gap
)


@dataclass(frozen=True, slots=True)
class RegulatoryRule:
    """Declarative rule — evaluated in catalogue order."""

    rule_id: str
    category: RegulatoryRuleCategory
    title: str
    point_value: int
    weight: float
    rationale: str
    regulatory_reference: str
    applies_when: Callable[[SoftwareUpdate], bool]


def _contribution_from_rule(rule: RegulatoryRule) -> RuleContribution:
    awarded = round(rule.point_value * rule.weight)
    return RuleContribution(
        rule_id=rule.rule_id,
        category=rule.category,
        title=rule.title,
        rationale=rule.rationale,
        regulatory_reference=rule.regulatory_reference,
        point_value=rule.point_value,
        weight=rule.weight,
        points_awarded=awarded,
    )


def _rule_catalogue() -> tuple[RegulatoryRule, ...]:
    """Explicit regulatory rule set — append-only for extensions."""
    return (
        RegulatoryRule(
            rule_id=RULE_SOFTWARE_SAFETY_C_POSTURE,
            category=RegulatoryRuleCategory.DEVICE_AND_SAFETY_CLASS,
            title="Software safety Class C posture",
            point_value=12,
            weight=1.0,
            rationale=(
                "Class C software can directly contribute to unacceptable harm; treat remote updates "
                "conservatively unless scope is trivially decoupled from patient harm."
            ),
            regulatory_reference=REF_IEC_62304,
            applies_when=lambda u: u.software_safety_class == SoftwareSafetyClass.CLASS_C,
        ),
        RegulatoryRule(
            rule_id=RULE_DEVICE_CLASS_III,
            category=RegulatoryRuleCategory.DEVICE_AND_SAFETY_CLASS,
            title="Class III device footprint",
            point_value=10,
            weight=1.0,
            rationale=(
                "High-class implants and life-sustaining systems attract heightened agency scrutiny, "
                "including for distributed software changes."
            ),
            regulatory_reference=REF_FDA_QMS_CORRECTION,
            applies_when=lambda u: u.device_class == DeviceClass.CLASS_III,
        ),
        RegulatoryRule(
            rule_id=RULE_DEVICE_CLASS_IIB,
            category=RegulatoryRuleCategory.DEVICE_AND_SAFETY_CLASS,
            title="Class IIb device footprint",
            point_value=6,
            weight=1.0,
            rationale=(
                "Class IIb devices carry meaningful patient exposure; multi-site updates should assume "
                "RA review beyond a pure maintenance narrative."
            ),
            regulatory_reference=REF_EU_MDR_POSTMARKET,
            applies_when=lambda u: u.device_class == DeviceClass.CLASS_IIB,
        ),
        RegulatoryRule(
            rule_id=RULE_DISTRIBUTION_GLOBAL,
            category=RegulatoryRuleCategory.DISTRIBUTION,
            title="Global distribution scope",
            point_value=12,
            weight=1.0,
            rationale=(
                "Worldwide deployment widens population-at-risk and complicates containment if a defect "
                "escapes verification."
            ),
            regulatory_reference=REF_EMA_GVP_AND_QMS,
            applies_when=lambda u: u.distribution_scope == DistributionScope.GLOBAL,
        ),
        RegulatoryRule(
            rule_id=RULE_DISTRIBUTION_REGIONAL,
            category=RegulatoryRuleCategory.DISTRIBUTION,
            title="Regional distribution scope",
            point_value=5,
            weight=1.0,
            rationale=(
                "Regional reach implies heterogeneous health systems and patch cadences — coordination cost "
                "and communication obligations rise versus a single site."
            ),
            regulatory_reference=REF_EMA_GVP_AND_QMS,
            applies_when=lambda u: u.distribution_scope == DistributionScope.REGIONAL,
        ),
        RegulatoryRule(
            rule_id=RULE_UPDATE_ALGORITHM,
            category=RegulatoryRuleCategory.CHANGE_CHARACTERIZATION,
            title="Algorithm or model-evaluation change",
            point_value=24,
            weight=1.0,
            rationale=(
                "Algorithmic changes can silently shift sensitivity/specificity; expect clinical "
                "evaluation, labeling synchronization, and often enhanced V&V evidence."
            ),
            regulatory_reference=REF_EU_MDR_POSTMARKET,
            applies_when=lambda u: u.update_type == UpdateTypeIndication.ALGORITHM_CHANGE,
        ),
        RegulatoryRule(
            rule_id=RULE_UPDATE_ENHANCEMENT,
            category=RegulatoryRuleCategory.CHANGE_CHARACTERIZATION,
            title="Enhancement beyond pure maintenance",
            point_value=12,
            weight=1.0,
            rationale=(
                'Enhancements may exceed "bug fix" framing if user-facing performance, claims, or '
                "risk controls evolve — compare against cleared/approved intended use."
            ),
            regulatory_reference=REF_FDA_QMS_CORRECTION,
            applies_when=lambda u: u.update_type == UpdateTypeIndication.ENHANCEMENT,
        ),
        RegulatoryRule(
            rule_id=RULE_UPDATE_THIRD_PARTY,
            category=RegulatoryRuleCategory.CHANGE_CHARACTERIZATION,
            title="Third-party component or SBOM-impacting dependency change",
            point_value=10,
            weight=1.0,
            rationale=(
                "Supply-chain updates can invalidate prior cybersecurity evidence unless dependency risk, "
                "vulnerability screening, and regression tests are re-baselined."
            ),
            regulatory_reference=REF_CYBER_POSITIONS,
            applies_when=lambda u: u.update_type == UpdateTypeIndication.THIRD_PARTY_COMPONENT,
        ),
        RegulatoryRule(
            rule_id=RULE_UPDATE_SECURITY_PATCH,
            category=RegulatoryRuleCategory.CHANGE_CHARACTERIZATION,
            title="Security patch distribution",
            point_value=8,
            weight=1.0,
            rationale=(
                "Security-driven releases intersect FDA cybersecurity documentation, CE-mark cybersecurity "
                "annex expectations, and coordinated disclosure timelines."
            ),
            regulatory_reference=REF_CYBER_POSITIONS,
            applies_when=lambda u: u.update_type == UpdateTypeIndication.SECURITY_PATCH,
        ),
        RegulatoryRule(
            rule_id=RULE_UPDATE_CONFIG_WORKFLOW,
            category=RegulatoryRuleCategory.CHANGE_CHARACTERIZATION,
            title="Configuration or workflow reprogramming",
            point_value=6,
            weight=1.0,
            rationale=(
                "Workflow and configuration changes affect human factors and traceability — often "
                "scrutinized in audits if not tied to validated instruction."
            ),
            regulatory_reference=REF_FDA_QMS_CORRECTION,
            applies_when=lambda u: u.update_type == UpdateTypeIndication.CONFIG_OR_WORKFLOW,
        ),
        RegulatoryRule(
            rule_id=RULE_MAINTENANCE_DEFECT_CORRECTION,
            category=RegulatoryRuleCategory.MAINTENANCE_POSTURE,
            title="Defect correction baseline (maintenance posture)",
            point_value=0,
            weight=1.0,
            rationale=(
                "Pure defect-correction narratives align with routine quality maintenance **when** scope "
                "is confirmed not to alter clinical performance, labeling, or risk controls. This rule "
                "records that posture for audit; it awards no points."
            ),
            regulatory_reference=REF_FDA_QMS_CORRECTION,
            applies_when=lambda u: u.update_type == UpdateTypeIndication.DEFECT_CORRECTION,
        ),
        RegulatoryRule(
            rule_id=RULE_CLINICAL_FUNCTION,
            category=RegulatoryRuleCategory.CLINICAL_PERFORMANCE,
            title="Affects clinical function or output",
            point_value=22,
            weight=1.0,
            rationale=(
                "Changes to clinical outputs can disturb benefit-risk; require traceable verification "
                "evidence and, where applicable, notification pathways."
            ),
            regulatory_reference=REF_EU_MDR_POSTMARKET,
            applies_when=lambda u: u.affects_clinical_function_or_output,
        ),
        RegulatoryRule(
            rule_id=RULE_CLINICAL_DECISION,
            category=RegulatoryRuleCategory.CLINICAL_PERFORMANCE,
            title="Impacts diagnostic or treatment decision-making",
            point_value=28,
            weight=1.0,
            rationale=(
                "Decision-support changes often map to the highest software concern tiers and may implicate "
                "clinical evaluation reports (EU) and predetermination of reporting duties (US)."
            ),
            regulatory_reference=REF_EMA_GVP_AND_QMS,
            applies_when=lambda u: u.affects_diagnostic_or_treatment_decisioning,
        ),
        RegulatoryRule(
            rule_id=RULE_LABELING,
            category=RegulatoryRuleCategory.LABELING_INTENDED_USE,
            title="Labeling or IFU impacts",
            point_value=18,
            weight=1.0,
            rationale=(
                "Label drift without timely submissions can create misbranding exposure; harmonize IFU, "
                "screen captures, and claims."
            ),
            regulatory_reference=REF_FDA_QMS_CORRECTION,
            applies_when=lambda u: u.changes_device_labeling_or_ifu,
        ),
        RegulatoryRule(
            rule_id=RULE_CONNECTIVITY,
            category=RegulatoryRuleCategory.CONNECTIVITY_CYBER,
            title="Connectivity or remote interface changes",
            point_value=14,
            weight=1.0,
            rationale=(
                "Remote interfaces alter attack surface and data flows — expect cybersecurity impact "
                "analysis and, where applicable, coordinated disclosure discipline."
            ),
            regulatory_reference=REF_CYBER_POSITIONS,
            applies_when=lambda u: u.introduces_or_changes_connectivity_or_remote_interfaces,
        ),
        RegulatoryRule(
            rule_id=RULE_SECURITY_VULN,
            category=RegulatoryRuleCategory.CONNECTIVITY_CYBER,
            title="Mitigates known or suspected vulnerability",
            point_value=20,
            weight=1.0,
            rationale=(
                "Credible vulnerabilities frequently trigger postmarket communications and may intersect "
                "correction/removal style analyses when unmitigated use could harm patients."
            ),
            regulatory_reference=REF_CYBER_POSITIONS,
            applies_when=lambda u: u.mitigates_known_or_suspected_security_vulnerability,
        ),
        RegulatoryRule(
            rule_id=RULE_DATA_INTEGRITY,
            category=RegulatoryRuleCategory.DATA_GOVERNANCE,
            title="Data integrity / GxP records impact",
            point_value=20,
            weight=1.0,
            rationale=(
                "Records underpinning GxP decisions demand ALCOA+ controls — changes may invoke CSV, "
                "audit trail review, and Part 11/Annex 11 considerations."
            ),
            regulatory_reference="EU GMP Annex 11; FDA 21 CFR Part 11 (where applicable).",
            applies_when=lambda u: u.impacts_data_integrity_audit_trails_or_records_used_for_gxp,
        ),
        RegulatoryRule(
            rule_id=RULE_PRIOR_FIELD_ISSUES,
            category=RegulatoryRuleCategory.POSTMARKET_AND_PMS,
            title="Prior field signals or complaints",
            point_value=16,
            weight=1.0,
            rationale=(
                "Repeated complaints suggest systemic inadequacy of existing controls — regulators treat "
                "recurrence as elevation risk rather than an isolated maintenance item."
            ),
            regulatory_reference=REF_EU_MDR_POSTMARKET,
            applies_when=lambda u: u.prior_similar_issues_in_field_or_complaints,
        ),
        RegulatoryRule(
            rule_id=RULE_PMS_RISK,
            category=RegulatoryRuleCategory.POSTMARKET_AND_PMS,
            title="Postmarket surveillance or ISO 14971 control impact",
            point_value=18,
            weight=1.0,
            rationale=(
                "Surveillance and risk-control edits can shift residual risk acceptance and must align "
                "with the approved risk management file."
            ),
            regulatory_reference="ISO 14971; EU MDR PMS requirements.",
            applies_when=lambda u: u.affects_post_market_surveillance_or_risk_controls,
        ),
        RegulatoryRule(
            rule_id=RULE_INTENDED_USE,
            category=RegulatoryRuleCategory.LABELING_INTENDED_USE,
            title="Intended use / indication discussion",
            point_value=30,
            weight=1.0,
            rationale=(
                "Indication creep is a high-energy regulatory trigger — often reclassifies the change "
                "away from maintenance and toward explicit submissions."
            ),
            regulatory_reference=REF_EMA_GVP_AND_QMS,
            applies_when=lambda u: u.intended_use_change_or_new_indication_discussed,
        ),
        RegulatoryRule(
            rule_id=RULE_RELEASE_NOTES_RISK_ALIGNMENT,
            category=RegulatoryRuleCategory.MAINTENANCE_POSTURE,
            title="Release documentation does not assert controlled safety rationale",
            point_value=10,
            weight=1.0,
            rationale=(
                "Absent controlled release records summarizing patient risk disposition, agencies may infer "
                "incomplete verification or hidden residual defects."
            ),
            regulatory_reference=REF_FDA_QMS_CORRECTION,
            applies_when=lambda u: not u.release_notes_assert_no_patient_risk,
        ),
        RegulatoryRule(
            rule_id=RULE_WORKAROUND,
            category=RegulatoryRuleCategory.RISK_OFFSET,
            title="Documented workaround with acceptable clinical posture",
            point_value=-12,
            weight=1.0,
            rationale=(
                "Operational mitigations can reduce urgency **if** human-factors and clinical risk analyses "
                "confirm the workaround is reliable — negative points must never substitute for RA sign-off."
            ),
            regulatory_reference="ISO 14971 risk reduction hierarchy; internal risk file linkage required.",
            applies_when=lambda u: u.workaround_available_without_clinical_compromise,
        ),
        RegulatoryRule(
            rule_id=RULE_CORRECTION_REMOVAL_COMPOSITE,
            category=RegulatoryRuleCategory.CORRECTION_REMOVAL_SIGNAL,
            title="Composite correction / field-action investigatory signal",
            point_value=0,
            weight=1.0,
            rationale=(
                "When multiple high-impact safety, cybersecurity, or labeling drivers co-occur, treat the "
                "bundle like a **correction/removal style investigation** even if legalese differs by "
                "jurisdiction — this rule produces an explicit audit flag without changing the numeric score."
            ),
            regulatory_reference=REF_FDA_QMS_CORRECTION + " " + REF_EU_MDR_POSTMARKET,
            applies_when=_correction_removal_cluster,
        ),
    )


def _correction_removal_cluster(u: SoftwareUpdate) -> bool:
    """Heuristic cluster mirroring reportability **questions** regulators ask — not a legal conclusion."""
    clinical = (
        u.affects_diagnostic_or_treatment_decisioning or u.affects_clinical_function_or_output
    )
    cyber = (
        u.mitigates_known_or_suspected_security_vulnerability
        or u.introduces_or_changes_connectivity_or_remote_interfaces
    )
    labeling = u.changes_device_labeling_or_ifu or u.intended_use_change_or_new_indication_discussed
    serious_postmarket = u.prior_similar_issues_in_field_or_complaints
    return (clinical and cyber) or (clinical and labeling) or (serious_postmarket and clinical)


class SoftwareUpdateClassifier:
    """Weighted scoring engine with explicit, auditable regulatory contributions."""

    def __init__(self, *, rules: tuple[RegulatoryRule, ...] | None = None) -> None:
        self._rules = rules if rules is not None else _rule_catalogue()

    def classify_update(self, update: SoftwareUpdate) -> ClassificationResult:
        """Run deterministic classification — returns traceable contributions and audit entries."""
        logger.debug("Classifying software update for device=%s", update.device_name)
        started = datetime.now(UTC)
        audit: list[AuditTrailEntry] = [
            AuditTrailEntry(
                timestamp=started,
                step="ENGINE_START",
                message="Beginning evaluation of SoftwareUpdate against regulatory rule catalogue.",
                metadata={"device": update.device_name},
            )
        ]
        contributions: list[RuleContribution] = []
        for rule in self._rules:
            try:
                applies = rule.applies_when(update)
            except Exception as exc:
                logger.exception("Rule evaluation failed rule_id=%s", rule.rule_id)
                raise AssessmentProcessingError(
                    f"Rule {rule.rule_id} failed during evaluation.",
                    detail=str(exc),
                ) from exc
            audit.append(
                AuditTrailEntry(
                    step="RULE_TESTED",
                    message=f"Evaluated {rule.rule_id} — applied={applies}",
                    rule_id=rule.rule_id,
                    metadata={"applied": str(applies)},
                )
            )
            if applies:
                contrib = _contribution_from_rule(rule)
                contributions.append(contrib)
                audit.append(
                    AuditTrailEntry(
                        step="RULE_FIRED",
                        message=f"{rule.rule_id} contributed {contrib.points_awarded} points.",
                        rule_id=rule.rule_id,
                        metadata={"points_awarded": str(contrib.points_awarded)},
                    )
                )

        raw_total = sum(c.points_awarded for c in contributions)
        total_points = raw_total if raw_total > 0 else 0
        normalized = round(
            min(100.0, (total_points / _THEORETICAL_MAX_POSITIVE_POINTS) * 100.0),
            1,
        )
        formula = (
            f"normalized_0_100 = min(100, round((total_points / {_THEORETICAL_MAX_POSITIVE_POINTS}) * 100, 1)); "
            f"total_points = max(0, sum(points_awarded)); raw_total={raw_total}."
        )
        risk_score = RiskScore(
            total_points=total_points,
            normalized_0_100=normalized,
            theoretical_max_points=float(_THEORETICAL_MAX_POSITIVE_POINTS),
            normalization_formula=formula,
        )
        band = _band_for_normalized_score(normalized)
        audit.append(
            AuditTrailEntry(
                step="BAND_SELECTED",
                message=f"Band {band.value} selected for normalized score {normalized}.",
                metadata={"band": band.value, "normalized": str(normalized)},
            )
        )
        classification = _build_update_classification(update, band, contributions)
        executive, steps = _executive_narrative(band, contributions, update)
        audit.append(
            AuditTrailEntry(
                step="ENGINE_COMPLETE",
                message="Classification complete; narrative and next steps materialized.",
                metadata={},
            )
        )
        return ClassificationResult(
            risk_score=risk_score,
            classification=classification,
            contributions=contributions,
            decision_audit_trail=audit,
            executive_summary=executive,
            recommended_next_steps=steps,
        )


def classify_update(update: SoftwareUpdate) -> ClassificationResult:
    """Backward-compatible functional entry point delegating to :class:`SoftwareUpdateClassifier`."""
    return SoftwareUpdateClassifier().classify_update(update)


def _band_for_normalized_score(normalized: float) -> ClassificationBand:
    if normalized < 40.0:
        return ClassificationBand.ROUTINE_QUALITY_FIX
    if normalized < 70.0:
        return ClassificationBand.BORDERLINE_FIELD_INVESTIGATION
    return ClassificationBand.ELEVATED_REPORTING_AND_FIELD_ACTION_LIKELIHOOD


def _build_update_classification(
    update: SoftwareUpdate,
    band: ClassificationBand,
    contributions: list[RuleContribution],
) -> UpdateClassification:
    """Synthesize regulatory narrative strings for auditors."""
    defect_only = update.update_type == UpdateTypeIndication.DEFECT_CORRECTION
    if defect_only and not _has_non_maintenance_flags(update):
        bug_fix = (
            "Facts resemble a **defect correction** path: the declared change type is maintenance-oriented "
            "and critical clinical, labeling, and cybersecurity drivers are not asserted. Align evidence "
            'with FDA "correction" maintenance concepts and EU technical documentation for software changes.'
        )
    elif update.update_type in (
        UpdateTypeIndication.ENHANCEMENT,
        UpdateTypeIndication.ALGORITHM_CHANGE,
    ):
        bug_fix = (
            "Declared change characterization moves beyond a narrow bug fix — treat as potential "
            "**functional or performance evolution** requiring benefit-risk reassessment."
        )
    else:
        bug_fix = (
            "Mixed or security-driven characterization — maintenance framing may still apply for sub-elements, "
            "but RA must confirm against cleared/approved documentation for each impacted function."
        )

    corr_fired = any(c.rule_id == RULE_CORRECTION_REMOVAL_COMPOSITE for c in contributions)
    high_energy = any(
        c.rule_id in {RULE_INTENDED_USE, RULE_CLINICAL_DECISION, RULE_SECURITY_VULN}
        for c in contributions
    )
    if corr_fired and high_energy:
        posture = (
            "Multiple drivers suggest **correction / field-safety style scrutiny**: overlap of clinical "
            "outputs, cybersecurity, labeling, or recurrent complaints mirrors questions agencies ask before "
            "mandating communications or device corrections. Prepare a jurisdictional matrix (US, EU, UK, "
            "others) and counsel review — this tool does not render reportability."
        )
    elif band == ClassificationBand.ELEVATED_REPORTING_AND_FIELD_ACTION_LIKELIHOOD:
        posture = (
            "Normalized score is elevated — plan for **integrated RA/QA investigation**, including "
            "health risk narrative, distribution analysis, and containment, even if a formal "
            "correction/removal filing may ultimately be unwarranted."
        )
    elif band == ClassificationBand.BORDERLINE_FIELD_INVESTIGATION:
        posture = (
            "Signals are mixed; expect **structured cross-functional review** with documented rationale "
            "before dismissing reporting or field actions."
        )
    else:
        posture = (
            "Heuristic posture is consistent with **routine maintenance**, assuming independent verification "
            "confirms no undisclosed labeling, clinical performance, or cybersecurity scope creep."
        )

    themes = _dominant_themes(contributions)
    return UpdateClassification(
        band=band,
        bug_fix_characterization=bug_fix,
        field_action_and_reporting_posture=posture,
        dominant_regulatory_themes=themes,
    )


def _has_non_maintenance_flags(u: SoftwareUpdate) -> bool:
    return any(
        (
            u.affects_clinical_function_or_output,
            u.affects_diagnostic_or_treatment_decisioning,
            u.changes_device_labeling_or_ifu,
            u.introduces_or_changes_connectivity_or_remote_interfaces,
            u.mitigates_known_or_suspected_security_vulnerability,
            u.impacts_data_integrity_audit_trails_or_records_used_for_gxp,
            u.prior_similar_issues_in_field_or_complaints,
            u.affects_post_market_surveillance_or_risk_controls,
            u.intended_use_change_or_new_indication_discussed,
            not u.release_notes_assert_no_patient_risk,
        )
    )


def _dominant_themes(contributions: list[RuleContribution]) -> list[str]:
    by_impact = sorted(contributions, key=lambda c: abs(c.points_awarded), reverse=True)
    themes: list[str] = []
    for contrib in by_impact[:5]:
        if contrib.points_awarded == 0 and contrib.rule_id != RULE_CORRECTION_REMOVAL_COMPOSITE:
            continue
        themes.append(f"{contrib.category.value}: {contrib.title} ({contrib.rule_id})")
    return themes or ["no material scored contributions"]


def _executive_narrative(
    band: ClassificationBand,
    contributions: list[RuleContribution],
    update: SoftwareUpdate,
) -> tuple[str, list[str]]:
    scored = [
        c
        for c in contributions
        if c.points_awarded != 0 or c.rule_id == RULE_CORRECTION_REMOVAL_COMPOSITE
    ]
    ordered = sorted(scored, key=lambda c: abs(c.points_awarded), reverse=True)
    top = ", ".join(f"{c.rule_id}" for c in ordered[:3]) or "no scored factors"

    if band == ClassificationBand.ROUTINE_QUALITY_FIX:
        summary = (
            f'Composite posture for "{update.device_name}" aligns with **routine quality maintenance** '
            f"on the heuristic scale, assuming independent verification backs the declared scope. "
            f"Dominant contributors: {top}."
        )
        steps = [
            "Confirm scope against the approved risk management file, DHF/DMR indices, and labeling.",
            "Archive verification evidence, cybersecurity impact analysis, and regression rationale.",
        ]
    elif band == ClassificationBand.BORDERLINE_FIELD_INVESTIGATION:
        summary = (
            f'Mixed signals for "{update.device_name}" — treat as **borderline**: convene RA/QA/clinical '
            f"and cyber stakeholders with a traceable decision record. Dominant contributors: {top}."
        )
        steps = [
            "Complete a documented impact assessment linking patient risk, labeling, and vigilance obligations.",
            "Map complaints/CAPA history and determine whether trending triggers expanded reporting.",
            "Engage competent regulatory counsel before final jurisdictional conclusions.",
        ]
    else:
        summary = (
            f'High-weight pattern for "{update.device_name}" — **elevated reporting / field-action planning** '
            f"should begin until disproven with evidence. Dominant contributors: {top}."
        )
        steps = [
            "Stand up a controlled room decision log with RA, QA, and clinical safety signatories.",
            "Draft timelines, distribution lists, mitigations, and regulator-facing narratives.",
            "Preserve immutable logs, SBOM deltas, and service records supporting the decision.",
        ]

    return summary, steps


__all__ = [
    "AssessmentProcessingError",
    "SoftwareUpdateClassifier",
    "classify_update",
]
