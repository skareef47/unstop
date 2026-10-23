"""
Simulated Action Execution and Authorization Service
"""
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.schemas.action import SimulatedActionResponse
from app.simulators.system_actions import SystemActionSimulator
from app.services.audit_service import AuditService
from app.websockets.manager import ws_manager
from app.core.errors import BadRequestException, ForbiddenException, NotFoundException


# Consequential actions that strictly require confirmed human approval
CONSEQUENTIAL_ACTIONS = {
    "mock_config_correction",
    "mock_service_escalation",
    "mock_compensation",
}

# Roles required for specific actions
ACTION_ROLE_PERMISSIONS = {
    "mock_config_correction": ["agent", "admin", "l2_devops"],
    "mock_integration_health_check": ["customer", "agent", "admin", "l2_devops"],
    "mock_service_escalation": ["agent", "admin", "l2_devops"],
    "mock_compensation": ["admin", "billing_manager"],
}


class ActionService:
    @classmethod
    def execute_action(
        cls,
        db: Session,
        conversation_id: str,
        action_key: str,
        parameters: Optional[Dict[str, Any]] = None,
        confirmed_approval: bool = False,
        actor: str = "agent",
        actor_role: str = "agent",
    ) -> SimulatedActionResponse:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise NotFoundException("Conversation", conversation_id)

        params = parameters or {}
        norm_key = action_key.lower().strip()

        # 1. Role-based permission check
        allowed_roles = ACTION_ROLE_PERMISSIONS.get(norm_key, ["agent", "admin"])
        if actor_role not in allowed_roles:
            raise ForbiddenException(
                f"Role '{actor_role}' is not authorized to execute action '{action_key}'. "
                f"Required roles: {allowed_roles}"
            )

        # 2. Consequential action human approval check
        if norm_key in CONSEQUENTIAL_ACTIONS and not confirmed_approval:
            raise BadRequestException(
                f"Action '{action_key}' is consequential and requires explicit confirmed_approval=True."
            )

        # 3. Execute Simulator
        status, result, message = SystemActionSimulator.execute_action(
            action_key=norm_key,
            parameters=params,
            actor_role=actor_role,
        )

        if status == "failed":
            raise BadRequestException(f"Simulator execution failed: {message}")

        # 4. Audit Trail
        audit_event = AuditService.log_event(
            db=db,
            actor=actor,
            event_type="action.executed",
            payload={
                "action_key": norm_key,
                "status": status,
                "result": result,
                "parameters": params,
                "actor_role": actor_role,
            },
            conversation_id=conversation_id,
        )

        # 5. Broadcast to real-time dashboard
        ws_manager.broadcast_sync(
            event_type="action.completed",
            data={
                "action_key": norm_key,
                "status": status,
                "execution_id": result.get("execution_id"),
                "audit_event_id": audit_event.id,
                "message": message,
            },
            conversation_id=conversation_id,
        )

        return SimulatedActionResponse(
            action_key=norm_key,
            status=status,
            execution_id=result.get("execution_id", "sim_unknown"),
            result=result,
            audit_event_id=audit_event.id,
            message=message,
        )
