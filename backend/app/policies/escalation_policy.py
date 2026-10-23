"""
Deterministic Severity Scoring and Escalation Policy
"""
from typing import Dict, Any, Tuple, Optional
from app.schemas.case_analysis import SeverityBreakdown


class EscalationPolicy:
    """
    Implements deterministic severity scoring and escalation rules according to Section 9.

    Weights:
    - Customer / Service Impact: 35%
    - Urgency: 25%
    - Scope of affected users / services: 25%
    - SLA Risk: 15%
    """

    # Impact Weights (0-100 base)
    IMPACT_SCORES = {
        "none": 0.0,
        "minor": 20.0,
        "moderate": 50.0,
        "major": 80.0,
        "complete_outage": 100.0,
    }

    # Urgency Weights (0-100 base)
    URGENCY_SCORES = {
        "low": 15.0,
        "medium": 45.0,
        "high": 75.0,
        "critical": 100.0,
    }

    # Scope Weights (0-100 base)
    SCOPE_SCORES = {
        "single_user": 15.0,
        "multiple_users": 50.0,
        "organization": 80.0,
        "widespread": 100.0,
    }

    # SLA Risk Weights (0-100 base)
    SLA_SCORES = {
        "safe": 10.0,
        "warning": 50.0,
        "at_risk": 80.0,
        "breached": 100.0,
    }

    @classmethod
    def calculate_severity(
        cls,
        impact: str = "moderate",
        urgency: str = "medium",
        scope: str = "single_user",
        sla_risk: str = "safe",
        is_security_incident: bool = False,
        is_widespread_outage: bool = False,
    ) -> SeverityBreakdown:
        """
        Calculates explainable, deterministic severity score between 0.0 and 100.0.
        """
        # Map values safely with defaults
        imp_score = cls.IMPACT_SCORES.get(impact.lower(), 40.0)
        urg_score = cls.URGENCY_SCORES.get(urgency.lower(), 30.0)
        scp_score = cls.SCOPE_SCORES.get(scope.lower(), 25.0)
        sla_score = cls.SLA_SCORES.get(sla_risk.lower(), 10.0)

        # Weighted calculation
        raw_score = (
            (imp_score * 0.35)
            + (urg_score * 0.25)
            + (scp_score * 0.25)
            + (sla_score * 0.15)
        )

        final_score = round(min(100.0, max(0.0, raw_score)), 1)

        # Categorize label
        if final_score >= 85.0:
            severity_label = "critical"
        elif final_score >= 60.0:
            severity_label = "high"
        elif final_score >= 30.0:
            severity_label = "medium"
        else:
            severity_label = "low"

        # Mandatory escalation evaluation
        escalation_decision = False
        escalation_reason = None

        if is_security_incident:
            escalation_decision = True
            escalation_reason = "Mandatory escalation triggered: Critical security incident detected."
            final_score = max(final_score, 90.0)
            severity_label = "critical"
        elif is_widespread_outage or scope.lower() == "widespread":
            escalation_decision = True
            escalation_reason = "Mandatory escalation triggered: Confirmed widespread service outage."
            final_score = max(final_score, 88.0)
            severity_label = "critical"
        elif final_score >= 70.0:
            escalation_decision = True
            escalation_reason = f"High severity threshold reached ({final_score}/100) requiring specialist assignment."
        elif urgency.lower() == "critical" and scope.lower() in ("organization", "widespread"):
            escalation_decision = True
            escalation_reason = "Critical urgency combined with organization-wide impact."

        return SeverityBreakdown(
            impact_factor=imp_score,
            urgency_factor=urg_score,
            scope_factor=scp_score,
            sla_risk_factor=sla_score,
            final_score=final_score,
            severity_label=severity_label,
            escalation_decision=escalation_decision,
            escalation_reason=escalation_reason,
        )
