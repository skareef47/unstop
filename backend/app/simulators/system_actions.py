"""
Simulated System Actions
"""
import uuid
from typing import Any, Dict, Tuple


class SystemActionSimulator:
    """
    Executes mock system actions in an isolated environment.
    Never interacts with real billing or production customer infrastructure.
    """

    @classmethod
    def execute_action(
        cls,
        action_key: str,
        parameters: Dict[str, Any],
        actor_role: str = "agent",
    ) -> Tuple[str, Dict[str, Any], str]:
        """
        Returns (status: 'success' | 'failed' | 'rejected', result_payload: dict, message: str)
        """
        action = action_key.lower().strip()
        execution_id = f"sim_act_{uuid.uuid4().hex[:10]}"

        if action == "mock_config_correction":
            # Example: Invalidate gateway token cache or update key reference
            target = parameters.get("target_service", "api_gateway")
            return (
                "success",
                {
                    "execution_id": execution_id,
                    "target_service": target,
                    "action_applied": "cache_invalidation",
                    "keys_reloaded": ["auth_token_secret_v2"],
                    "latency_impact_ms": 0,
                    "new_state": "cache_synchronized",
                },
                f"Successfully invalidated cache and refreshed credentials on '{target}'.",
            )

        elif action == "mock_integration_health_check":
            target_endpoint = parameters.get("endpoint", "crm_webhook")
            return (
                "success",
                {
                    "execution_id": execution_id,
                    "target": target_endpoint,
                    "probe_status": "completed",
                    "http_status": 200,
                    "rtt_ms": 115,
                },
                f"Synthetic health check probe completed for '{target_endpoint}'.",
            )

        elif action == "mock_service_escalation":
            team = parameters.get("target_team", "l2_devops")
            urgency = parameters.get("urgency", "high")
            incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
            return (
                "success",
                {
                    "execution_id": execution_id,
                    "incident_id": incident_id,
                    "assigned_team": team,
                    "pager_alert_dispatched": True,
                    "escalation_level": urgency,
                },
                f"Escalation incident {incident_id} created and dispatched to {team}.",
            )

        elif action == "mock_compensation":
            downtime_minutes = parameters.get("downtime_minutes", 120)
            monthly_fee = parameters.get("monthly_fee", 500.0)
            # Recommend 10% credit for major incidents
            credit_amount = round(monthly_fee * 0.10, 2)
            return (
                "success",
                {
                    "execution_id": execution_id,
                    "calculated_credit_usd": credit_amount,
                    "sla_downtime_minutes": downtime_minutes,
                    "approval_status": "recommended_for_billing_review",
                },
                f"SLA compensation discount of ${credit_amount:.2f} calculated and recommended for billing approval.",
            )

        else:
            return (
                "failed",
                {"execution_id": execution_id, "unknown_action": action_key},
                f"Unsupported simulated action '{action_key}'.",
            )
