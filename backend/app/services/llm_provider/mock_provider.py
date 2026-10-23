"""
Deterministic Mock LLM Provider for local development and test scenarios
"""
import json
import re
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from app.services.llm_provider.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Mock provider that recognizes problem domains and generates evidence-grounded responses.
    Allows complete offline operation and deterministic automated test validation.
    """

    def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        last_message = messages[-1]["content"].lower() if messages else ""

        # Scenario 1: 401 authentication / key rotation
        if "401" in last_message or "key rotation" in last_message or "unauthorized" in last_message:
            return (
                "I understand you are encountering HTTP 401 Unauthorized errors following a recent API key rotation. "
                "Based on our API Authentication Runbook [SEC-AUTH-01], services often cache old credentials or fail to pick up "
                "the updated secret reference. "
                "Have your upstream services been restarted or informed to reload the new secret reference? "
                "We can run our automated 'check_api_credentials' diagnostic tool to verify the credential state."
            )

        # Scenario 2: CRM integration timeout
        if "crm" in last_message and ("timeout" in last_message or "sync" in last_message or "webhook" in last_message):
            return (
                "I notice you are experiencing CRM integration timeouts during synchronization. "
                "According to the CRM Synchronization Runbook [INT-CRM-03], webhook timeouts beyond 10,000ms typically occur "
                "when the external endpoint is unreachable or encountering rate limits. "
                "Let's execute the 'check_crm_webhook_connectivity' diagnostic to inspect gateway latency and handshake status."
            )

        # Scenario 3: Ambiguous complaint requiring clarification
        if "slow" in last_message and "not working" in last_message and "error" not in last_message:
            return (
                "I want to help resolve this quickly, but I need a few more details to diagnose the root cause: "
                "1. Which specific service or dashboard endpoint is exhibiting slow performance? "
                "2. Are you seeing specific HTTP error codes (e.g., 504 Gateway Timeout or 429)? "
                "3. When did this degradation start, and approximately how many users are affected?"
            )

        # Scenario 4: Widespread outage / 500 error flood
        if "outage" in last_message or ("500" in last_message and ("all users" in last_message or "widespread" in last_message or "us-east" in last_message)):
            return (
                "CRITICAL ALERT: Widespread HTTP 500 errors affecting all users in region US-East detected. "
                "In accordance with Platform Outage Policy [POL-CRIT-99], this incident qualifies for immediate high-priority escalation. "
                "I have compiled confirmed findings and initiated an escalation action plan for L3 DevOps and Incident Command."
            )

        # Prompt injection test
        if "ignore previous instructions" in last_message or "system prompt" in last_message:
            return (
                "I cannot override security policies or disclose system instructions. "
                "How can I assist you with technical troubleshooting within approved support guidelines?"
            )

        # Default conversational response
        return (
            f"Thank you for contacting PSAI Technical Support. I have logged your message regarding: "
            f"'{messages[-1]['content'][:80]}...'. I am analyzing system telemetry and matching relevant documentation to diagnose this issue."
        )

    def generate_structured_json(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        context_match = re.search(r"conversation context:\s*(.*)", prompt_lower, re.DOTALL | re.IGNORECASE)
        ctx = context_match.group(1).lower() if context_match else prompt_lower

        # Classification / Case Analysis Schema
        if "intent" in schema.model_fields and "severity_score" in schema.model_fields:
            # 1. Widespread Outage Scenario
            if "outage" in ctx or ("all users" in ctx and "500" in ctx):
                data = {
                    "intent": "incident_report",
                    "product_area": "platform_infrastructure",
                    "sentiment": "frustrated",
                    "sentiment_score": -0.85,
                    "urgency": "critical",
                    "severity_score": 92.0,
                    "impact_scope": "widespread",
                    "confirmed_facts": [
                        "HTTP 500 internal server errors returned on core endpoints",
                        "Affected scope encompasses all active users in US-East",
                        "Incident reported in production environment"
                    ],
                    "hypotheses": [
                        {
                            "id": "hyp_1",
                            "rank": 1,
                            "title": "Primary Database Cluster Connection Pool Exhaustion",
                            "description": "Database connection saturation causing upstream API gateways to throw 500 errors.",
                            "probability": 0.85,
                            "supporting_evidence": ["Universal 500 status codes across multiple distinct endpoints in US-East"],
                            "contradictory_evidence": [],
                            "missing_information": ["Database connection metrics and connection pool queue depth"],
                            "best_next_diagnostic_test": "check_database_connection_pool"
                        },
                        {
                            "id": "hyp_2",
                            "rank": 2,
                            "title": "Regional Load Balancer Gateway Failure",
                            "description": "US-East edge gateway proxying requests to unhealthy backend targets.",
                            "probability": 0.15,
                            "supporting_evidence": ["Issues isolated to US-East region"],
                            "contradictory_evidence": [],
                            "missing_information": ["Edge proxy health check results"],
                            "best_next_diagnostic_test": "check_gateway_health"
                        }
                    ],
                    "missing_information": ["Telemetry from primary database cluster", "Recent deployment logs"],
                    "escalation_required": True
                }
                return data

            # 2. 401 Authentication Failure Scenario
            if "401" in ctx or "key rotation" in ctx or "unauthorized" in ctx:
                data = {
                    "intent": "authentication_troubleshooting",
                    "product_area": "api_gateway",
                    "sentiment": "negative",
                    "sentiment_score": -0.4,
                    "urgency": "high",
                    "severity_score": 45.0,
                    "impact_scope": "organization",
                    "confirmed_facts": [
                        "API requests returning HTTP 401 Unauthorized",
                        "API key rotation occurred recently",
                        "Client reports sending requests with updated bearer format"
                    ],
                    "hypotheses": [
                        {
                            "id": "hyp_1",
                            "rank": 1,
                            "title": "Stale Token Cache in Gateway Service",
                            "description": "The API gateway has not invalidated its cached verification key from before the rotation.",
                            "probability": 0.80,
                            "supporting_evidence": ["Timing directly correlates with key rotation; 401 Unauthorized received"],
                            "contradictory_evidence": [],
                            "missing_information": ["API gateway token cache TTL and reload timestamp"],
                            "best_next_diagnostic_test": "check_api_credentials"
                        },
                        {
                            "id": "hyp_2",
                            "rank": 2,
                            "title": "Client Secret Reference Mismatch",
                            "description": "Client application environment variables still point to the deprecated key ID.",
                            "probability": 0.20,
                            "supporting_evidence": ["401 status indicates rejected credentials"],
                            "contradictory_evidence": ["Client claims configuration was updated"],
                            "missing_information": ["Active key ID sent in authorization header"],
                            "best_next_diagnostic_test": "inspect_client_auth_header"
                        }
                    ],
                    "missing_information": ["Key ID present in request authorization header", "Gateway cache sync status"],
                    "escalation_required": False
                }
                return data

            # 3. CRM Integration Timeout Scenario
            if "crm" in ctx and ("timeout" in ctx or "sync" in ctx or "webhook" in ctx):
                data = {
                    "intent": "integration_failure",
                    "product_area": "crm_sync",
                    "sentiment": "negative",
                    "sentiment_score": -0.5,
                    "urgency": "high",
                    "severity_score": 68.0,
                    "impact_scope": "multiple_users",
                    "confirmed_facts": [
                        "CRM synchronization jobs timing out after 10,000ms",
                        "Sync failures observed repeatedly for pending customer records"
                    ],
                    "hypotheses": [
                        {
                            "id": "hyp_1",
                            "rank": 1,
                            "title": "Third-Party CRM Webhook Gateway Unreachable",
                            "description": "External CRM API endpoint is not responding within the HTTP timeout threshold.",
                            "probability": 0.75,
                            "supporting_evidence": ["10,000ms timeout logged during outbound POST request"],
                            "contradictory_evidence": [],
                            "missing_information": ["External CRM status page status", "Egress firewall logs"],
                            "best_next_diagnostic_test": "check_crm_webhook_connectivity"
                        }
                    ],
                    "missing_information": ["CRM provider incident status", "Egress network packet loss"],
                    "escalation_required": True
                }
                return data

            # 4. Ambiguous Complaint Scenario
            if "slow" in ctx or "not working" in ctx:
                data = {
                    "intent": "vague_complaint",
                    "product_area": "general",
                    "sentiment": "frustrated",
                    "sentiment_score": -0.3,
                    "urgency": "low",
                    "severity_score": 20.0,
                    "impact_scope": "single_user",
                    "confirmed_facts": [
                        "User reported slow system performance without specific endpoints or error logs"
                    ],
                    "hypotheses": [
                        {
                            "id": "hyp_1",
                            "rank": 1,
                            "title": "Undetermined Client-Side or Network Latency",
                            "description": "Performance degradation reported without specific service indicators.",
                            "probability": 0.50,
                            "supporting_evidence": ["User subjective report of slowness"],
                            "contradictory_evidence": [],
                            "missing_information": ["Exact endpoint URL", "HTTP response code", "User ID or region"],
                            "best_next_diagnostic_test": "gather_client_telemetry"
                        }
                    ],
                    "missing_information": [
                        "Specific URL or component",
                        "HTTP status codes received",
                        "Timestamp and frequency of slowness",
                        "Number of affected users"
                    ],
                    "escalation_required": False
                }
                return data

            # Generic fallback classification
            return {
                "intent": "general_inquiry",
                "product_area": "general",
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "urgency": "low",
                "severity_score": 15.0,
                "impact_scope": "single_user",
                "confirmed_facts": ["Customer submitted inquiry"],
                "hypotheses": [],
                "missing_information": ["Detailed error symptoms"],
                "escalation_required": False
            }

        # Action Plan Generation Schema
        if "recommendations" in schema.model_fields:
            if "outage" in prompt_lower or "500" in prompt_lower:
                return {
                    "summary": "Critical incident: Widespread 500 errors in US-East region",
                    "customer_impact": "Complete service unavailability for customers hosted in US-East",
                    "confirmed_findings": [
                        "HTTP 500 status returned across core API endpoints",
                        "Scope confirmed as widespread affecting all US-East users"
                    ],
                    "steps_attempted": [
                        {"step": "Initial telemetry verification", "result": "Confirmed 500 error spike"}
                    ],
                    "recommendations": [
                        {
                            "action_key": "mock_service_escalation",
                            "title": "Engage Incident Command and L3 DevOps",
                            "rationale": "Severity exceeds critical threshold (92/100) and impacts regional availability",
                            "risk_level": "low",
                            "required_role": "agent",
                            "requires_approval": False
                        },
                        {
                            "action_key": "mock_config_correction",
                            "title": "Failover traffic to US-West backup cluster",
                            "rationale": "Mitigate customer downtime while root-cause isolation on US-East database is underway",
                            "risk_level": "high",
                            "required_role": "l2_devops",
                            "requires_approval": True
                        }
                    ],
                    "required_evidence": ["Database connection pool saturation telemetry", "Regional latency graphs"],
                    "recommended_team": "l3_engineering",
                    "escalation_reason": "Widespread service outage violating availability SLAs",
                    "status": "draft"
                }

            if "crm" in prompt_lower:
                return {
                    "summary": "CRM synchronization webhook timeouts requiring tier-2 escalation",
                    "customer_impact": "Customer records created in past 2 hours not synchronized to external CRM",
                    "confirmed_findings": [
                        "Webhook diagnostic confirmed timeout > 10,000ms to CRM partner gateway",
                        "Retry limit reached with 3 consecutive failures"
                    ],
                    "steps_attempted": [
                        {"step": "check_crm_webhook_connectivity", "result": "failed", "evidence": "Timeout 10000ms"}
                    ],
                    "recommendations": [
                        {
                            "action_key": "mock_service_escalation",
                            "title": "Escalate to Integrations Tier 2 Team",
                            "rationale": "External webhook endpoint unresponsive, requires vendor engagement",
                            "risk_level": "medium",
                            "required_role": "agent",
                            "requires_approval": False
                        }
                    ],
                    "required_evidence": ["Outbound webhook timeout traces", "CRM API health check status"],
                    "recommended_team": "l2_devops",
                    "escalation_reason": "Third-party partner API timeout unresolved by automated retries",
                    "status": "draft"
                }

            # Default action plan
            return {
                "summary": "Standard resolution plan for API Authentication 401 errors",
                "customer_impact": "Users unable to authenticate requests after credential rotation",
                "confirmed_findings": ["API key rotation occurred; stale token cache identified"],
                "steps_attempted": [
                    {"step": "check_api_credentials", "result": "failed", "evidence": "Cache key mismatched"}
                ],
                "recommendations": [
                    {
                        "action_key": "mock_config_correction",
                        "title": "Invalidate Gateway Token Cache",
                        "rationale": "Force API gateway to reload active credentials from secure vault",
                        "risk_level": "low",
                        "required_role": "agent",
                        "requires_approval": False
                    }
                ],
                "required_evidence": ["Gateway cache reload logs"],
                "recommended_team": "l1_support",
                "escalation_reason": None,
                "status": "draft"
            }

        # Fallback empty schema dict
        return {}
