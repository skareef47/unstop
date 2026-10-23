"""
Deterministic Diagnostic Workflow Engine
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.diagnostic import DiagnosticRun, DiagnosticStep
from app.simulators.diagnostic_tools import DiagnosticToolSimulator
from app.websockets.manager import ws_manager
from app.core.errors import BadRequestException, NotFoundException

# Predefined workflow definitions with deterministic state transitions
WORKFLOW_DEFINITIONS = {
    "auth_401_key_rotation": {
        "initial_step": "check_api_credentials",
        "steps": {
            "check_api_credentials": {
                "instruction": "Execute simulated check of API Gateway credential cache against secure secret vault.",
                "tool": "check_api_credentials",
                "transitions": {
                    "passed": "verify_token_claims",
                    "failed": "recommend_cache_invalidation",
                    "inconclusive": "inspect_client_auth_header",
                },
            },
            "inspect_client_auth_header": {
                "instruction": "Inspect Authorization header format and bearer token schema sent by client.",
                "tool": "gather_client_telemetry",
                "transitions": {
                    "passed": "recommend_cache_invalidation",
                    "failed": "escalate_to_auth_team",
                    "inconclusive": "recommend_cache_invalidation",
                },
            },
            "recommend_cache_invalidation": {
                "instruction": "Recommend executing simulated 'mock_config_correction' to invalidate stale gateway cache.",
                "tool": None,  # Requires simulated action or user confirmation
                "transitions": {
                    "passed": "verify_config_sync",
                    "failed": "escalate_to_auth_team",
                    "inconclusive": "verify_config_sync",
                },
            },
            "verify_config_sync": {
                "instruction": "Run simulated verification probe to confirm gateway cache reload.",
                "tool": "verify_config_sync",
                "transitions": {
                    "passed": "complete_resolved",
                    "failed": "escalate_to_auth_team",
                    "inconclusive": "escalate_to_auth_team",
                },
            },
            "verify_token_claims": {
                "instruction": "Validate JWT token claims and signature.",
                "tool": "verify_config_sync",
                "transitions": {
                    "passed": "complete_resolved",
                    "failed": "recommend_cache_invalidation",
                    "inconclusive": "recommend_cache_invalidation",
                },
            },
            "escalate_to_auth_team": {
                "instruction": "Automated recovery failed. Escalate incident to Identity and Access Management Tier 2.",
                "tool": None,
                "is_terminal": True,
                "terminal_status": "escalated",
            },
            "complete_resolved": {
                "instruction": "Authentication resolved. Confirmed valid token handshake.",
                "tool": None,
                "is_terminal": True,
                "terminal_status": "passed",
            },
        },
    },
    "crm_sync_timeout": {
        "initial_step": "check_crm_webhook_connectivity",
        "steps": {
            "check_crm_webhook_connectivity": {
                "instruction": "Ping external CRM webhook gateway and measure response latency.",
                "tool": "check_crm_webhook_connectivity",
                "transitions": {
                    "passed": "check_crm_queue_backlog",
                    "failed": "retry_webhook_probe",
                    "inconclusive": "retry_webhook_probe",
                },
            },
            "retry_webhook_probe": {
                "instruction": "Retry diagnostic probe to rule out transient network flutter.",
                "tool": "check_crm_webhook_connectivity",
                "transitions": {
                    "passed": "check_crm_queue_backlog",
                    "failed": "escalate_crm_timeout",
                    "inconclusive": "escalate_crm_timeout",
                },
            },
            "check_crm_queue_backlog": {
                "instruction": "Inspect pending synchronization queue depth.",
                "tool": "verify_config_sync",
                "transitions": {
                    "passed": "complete_resolved",
                    "failed": "escalate_crm_timeout",
                    "inconclusive": "escalate_crm_timeout",
                },
            },
            "escalate_crm_timeout": {
                "instruction": "External partner CRM endpoint unreachable after retries. Escalate to Integrations Tier 2.",
                "tool": None,
                "is_terminal": True,
                "terminal_status": "escalated",
            },
            "complete_resolved": {
                "instruction": "CRM synchronization resumed nominally.",
                "tool": None,
                "is_terminal": True,
                "terminal_status": "passed",
            },
        },
    },
    "platform_outage_triage": {
        "initial_step": "check_database_connection_pool",
        "steps": {
            "check_database_connection_pool": {
                "instruction": "Inspect primary database connection pool saturation.",
                "tool": "check_database_connection_pool",
                "transitions": {
                    "passed": "check_gateway_health",
                    "failed": "escalate_outage",
                    "inconclusive": "check_gateway_health",
                },
            },
            "check_gateway_health": {
                "instruction": "Check regional edge load balancer health.",
                "tool": "check_gateway_health",
                "transitions": {
                    "passed": "complete_resolved",
                    "failed": "escalate_outage",
                    "inconclusive": "escalate_outage",
                },
            },
            "escalate_outage": {
                "instruction": "Outage confirmed. Mandatory incident escalation to Incident Command and L3 DevOps.",
                "tool": None,
                "is_terminal": True,
                "terminal_status": "escalated",
            },
            "complete_resolved": {
                "instruction": "Platform health checks normal.",
                "tool": None,
                "is_terminal": True,
                "terminal_status": "passed",
            },
        },
    },
    "generic_diagnostic": {
        "initial_step": "gather_client_telemetry",
        "steps": {
            "gather_client_telemetry": {
                "instruction": "Gather specific HTTP status code, request URL, and error timestamp from customer.",
                "tool": "gather_client_telemetry",
                "transitions": {
                    "passed": "complete_resolved",
                    "failed": "complete_inconclusive",
                    "inconclusive": "complete_inconclusive",
                },
            },
            "complete_inconclusive": {
                "instruction": "Awaiting customer clarification before proceeding with automated diagnostics.",
                "tool": None,
                "is_terminal": True,
                "terminal_status": "inconclusive",
            },
            "complete_resolved": {
                "instruction": "Sufficient telemetry gathered.",
                "tool": None,
                "is_terminal": True,
                "terminal_status": "completed",
            },
        },
    },
}


class DiagnosticService:
    MAX_RETRIES_PER_STEP = 3

    @classmethod
    def deduce_workflow(cls, db: Session, conversation: Conversation) -> str:
        """Deduce appropriate workflow from conversation context."""
        area = (conversation.product_area or "").lower()
        if "auth" in area or "api" in area:
            return "auth_401_key_rotation"
        elif "crm" in area or "sync" in area:
            return "crm_sync_timeout"
        elif "outage" in area or "platform" in area or conversation.status == "escalated":
            return "platform_outage_triage"
        return "auth_401_key_rotation"

    @classmethod
    def start_diagnostic_run(
        cls,
        db: Session,
        conversation_id: str,
        workflow_key: Optional[str] = None,
    ) -> DiagnosticRun:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise NotFoundException("Conversation", conversation_id)

        if not workflow_key:
            workflow_key = cls.deduce_workflow(db, conversation)

        if workflow_key not in WORKFLOW_DEFINITIONS:
            workflow_key = "auth_401_key_rotation"

        wf = WORKFLOW_DEFINITIONS[workflow_key]
        initial_step_key = wf["initial_step"]
        step_meta = wf["steps"][initial_step_key]

        run = DiagnosticRun(
            conversation_id=conversation_id,
            workflow_key=workflow_key,
            status="running",
            current_step=initial_step_key,
        )
        db.add(run)
        db.flush()

        # If initial step has an automated simulator tool, generate initial telemetry
        initial_tool = step_meta.get("tool")
        evidence = {}
        if initial_tool:
            _, evidence = DiagnosticToolSimulator.execute_tool(initial_tool, {})

        step = DiagnosticStep(
            run_id=run.id,
            step_key=initial_step_key,
            instruction=step_meta["instruction"],
            result="pending",
            evidence=evidence,
        )
        db.add(step)

        # Update conversation status
        if conversation.status == "active":
            conversation.status = "diagnosing"

        db.commit()
        db.refresh(run)

        # Broadcast event
        ws_manager.broadcast_sync(
            event_type="diagnostic.step_completed",
            data={
                "run_id": run.id,
                "workflow_key": run.workflow_key,
                "current_step": step.step_key,
                "result": step.result,
                "evidence": step.evidence,
                "status": run.status,
            },
            conversation_id=conversation_id,
        )

        return run

    @classmethod
    def record_step_result(
        cls,
        db: Session,
        run_id: str,
        step_id: str,
        result: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> DiagnosticRun:
        """
        Record outcome of a step (passed, failed, inconclusive) and transition to next step.
        """
        run = db.query(DiagnosticRun).filter(DiagnosticRun.id == run_id).first()
        if not run:
            raise NotFoundException("DiagnosticRun", run_id)

        if run.status in ("passed", "failed", "escalated", "completed"):
            raise BadRequestException(f"Diagnostic run is already in terminal state '{run.status}'")

        step = db.query(DiagnosticStep).filter(DiagnosticStep.id == step_id, DiagnosticStep.run_id == run_id).first()
        if not step:
            raise NotFoundException("DiagnosticStep", step_id)

        # Check duplicate step execution prevention: if step already has a non-pending result
        if step.result in ("passed", "failed", "inconclusive"):
            raise BadRequestException(f"Step '{step.step_key}' has already been recorded with result '{step.result}'.")

        step.result = result
        if evidence:
            step.evidence.update(evidence)
        step.executed_at = datetime.now(timezone.utc)

        wf = WORKFLOW_DEFINITIONS.get(run.workflow_key)
        if not wf:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return run

        current_step_def = wf["steps"].get(step.step_key, {})

        # Check retry limit for failures of the same step
        same_step_failures = (
            db.query(DiagnosticStep)
            .filter(
                DiagnosticStep.run_id == run.id,
                DiagnosticStep.step_key == step.step_key,
                DiagnosticStep.result == "failed",
            )
            .count()
        )

        if result == "failed" and same_step_failures >= cls.MAX_RETRIES_PER_STEP:
            # Exceeded retries -> auto escalate
            run.status = "escalated"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return run

        # Determine next step from transitions
        transitions = current_step_def.get("transitions", {})
        next_step_key = transitions.get(result)

        if not next_step_key:
            # No transition defined -> complete run
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return run

        next_step_def = wf["steps"].get(next_step_key)
        if not next_step_def:
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return run

        # Check terminal state
        if next_step_def.get("is_terminal"):
            run.status = next_step_def.get("terminal_status", "completed")
            run.current_step = next_step_key
            run.completed_at = datetime.now(timezone.utc)

            # Record final terminal step
            term_step = DiagnosticStep(
                run_id=run.id,
                step_key=next_step_key,
                instruction=next_step_def["instruction"],
                result="passed" if run.status == "passed" else "failed",
                evidence={"terminal_reason": next_step_def["instruction"]},
            )
            db.add(term_step)

            # Update conversation if resolved or escalated
            conversation = db.query(Conversation).filter(Conversation.id == run.conversation_id).first()
            if conversation:
                if run.status == "passed":
                    conversation.status = "resolved"
                elif run.status == "escalated":
                    conversation.status = "escalated"

            db.commit()
            db.refresh(run)

            ws_manager.broadcast_sync(
                event_type="diagnostic.step_completed",
                data={"run_id": run.id, "current_step": next_step_key, "status": run.status},
                conversation_id=run.conversation_id,
            )
            return run

        # Advance to next step
        run.current_step = next_step_key
        next_tool = next_step_def.get("tool")
        next_result = "pending"
        next_evidence = {}
        if next_tool:
            # Check if previous step indicated a fix
            tool_params = {}
            if "correction" in step.step_key or "invalidation" in step.step_key:
                tool_params["cache_reloaded"] = True
                tool_params["simulate_fix"] = True
            _, next_evidence = DiagnosticToolSimulator.execute_tool(next_tool, tool_params)

        new_step = DiagnosticStep(
            run_id=run.id,
            step_key=next_step_key,
            instruction=next_step_def["instruction"],
            result="pending",
            evidence=next_evidence,
        )
        db.add(new_step)
        db.commit()
        db.refresh(run)

        ws_manager.broadcast_sync(
            event_type="diagnostic.step_completed",
            data={
                "run_id": run.id,
                "current_step": new_step.step_key,
                "result": new_step.result,
                "status": run.status,
            },
            conversation_id=run.conversation_id,
        )

        return run

    @staticmethod
    def get_run(db: Session, run_id: str) -> Optional[DiagnosticRun]:
        return db.query(DiagnosticRun).filter(DiagnosticRun.id == run_id).first()
