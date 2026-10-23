"""
Action Plan Generation and Human Approval Service
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.case_analysis import CaseAnalysis
from app.models.diagnostic import DiagnosticRun
from app.models.action_plan import ActionPlan
from app.schemas.action_plan import ActionPlanResponse
from app.services.llm_provider.factory import get_llm_provider
from app.services.audit_service import AuditService
from app.prompts.templates import ACTION_PLAN_PROMPT_TEMPLATE
from app.websockets.manager import ws_manager
from app.core.errors import BadRequestException, NotFoundException


class ActionPlanService:
    @classmethod
    def generate_plan(
        cls,
        db: Session,
        conversation_id: str,
        actor: str = "agent",
    ) -> ActionPlan:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise NotFoundException("Conversation", conversation_id)

        # Gather context: latest analysis and diagnostic runs
        latest_analysis = (
            db.query(CaseAnalysis)
            .filter(CaseAnalysis.conversation_id == conversation_id)
            .order_by(CaseAnalysis.created_at.desc())
            .first()
        )

        diagnostic_runs = (
            db.query(DiagnosticRun)
            .filter(DiagnosticRun.conversation_id == conversation_id)
            .all()
        )

        steps_attempted = []
        for r in diagnostic_runs:
            for s in r.steps:
                steps_attempted.append({
                    "step": s.step_key,
                    "result": s.result,
                    "evidence": s.evidence,
                })

        case_context_lines = [
            f"Product Area: {conversation.product_area}",
            f"Current Status: {conversation.status}",
        ]
        if latest_analysis:
            case_context_lines.append(f"Intent: {latest_analysis.intent}")
            case_context_lines.append(f"Severity Score: {latest_analysis.severity_score}")
            case_context_lines.append(f"Confirmed Facts: {latest_analysis.confirmed_facts}")
            case_context_lines.append(f"Missing Information: {latest_analysis.missing_information}")

        case_context = "\n".join(case_context_lines)
        prompt = ACTION_PLAN_PROMPT_TEMPLATE.format(case_context=case_context)

        llm = get_llm_provider()
        plan_dict = llm.generate_structured_json(prompt=prompt, schema=ActionPlanResponse)

        summary = plan_dict.get("summary", f"Action plan for {conversation.product_area}")
        customer_impact = plan_dict.get("customer_impact", "Service degraded")
        confirmed_findings = plan_dict.get("confirmed_findings", latest_analysis.confirmed_facts if latest_analysis else [])
        recommendations = plan_dict.get("recommendations", [])
        required_evidence = plan_dict.get("required_evidence", [])
        recommended_team = plan_dict.get("recommended_team", "l1_support")
        escalation_reason = plan_dict.get("escalation_reason")

        plan = ActionPlan(
            conversation_id=conversation_id,
            summary=summary,
            customer_impact=customer_impact,
            confirmed_findings=confirmed_findings,
            steps_attempted=steps_attempted,
            recommendations=recommendations,
            required_evidence=required_evidence,
            recommended_team=recommended_team,
            escalation_reason=escalation_reason,
            status="draft",
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        # Audit Event
        AuditService.log_event(
            db=db,
            actor=actor,
            event_type="action_plan.generated",
            payload={"plan_id": plan.id, "summary": summary, "recommendations_count": len(recommendations)},
            conversation_id=conversation_id,
        )

        # Broadcast
        ws_manager.broadcast_sync(
            event_type="action_plan.generated",
            data={
                "plan_id": plan.id,
                "summary": plan.summary,
                "status": plan.status,
                "recommendations": plan.recommendations,
            },
            conversation_id=conversation_id,
        )

        return plan

    @staticmethod
    def get_latest_plan(db: Session, conversation_id: str) -> Optional[ActionPlan]:
        return (
            db.query(ActionPlan)
            .filter(ActionPlan.conversation_id == conversation_id)
            .order_by(ActionPlan.created_at.desc())
            .first()
        )

    @classmethod
    def approve_plan(cls, db: Session, plan_id: str, actor: str = "agent") -> ActionPlan:
        plan = db.query(ActionPlan).filter(ActionPlan.id == plan_id).first()
        if not plan:
            raise NotFoundException("ActionPlan", plan_id)

        if plan.status != "draft":
            raise BadRequestException(f"Plan is already in status '{plan.status}'")

        plan.status = "approved"
        plan.approved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(plan)

        AuditService.log_event(
            db=db,
            actor=actor,
            event_type="action_plan.approved",
            payload={"plan_id": plan.id, "approved_at": plan.approved_at.isoformat()},
            conversation_id=plan.conversation_id,
        )

        ws_manager.broadcast_sync(
            event_type="case.updated",
            data={"plan_id": plan.id, "status": "approved"},
            conversation_id=plan.conversation_id,
        )
        return plan

    @classmethod
    def reject_plan(cls, db: Session, plan_id: str, actor: str = "agent") -> ActionPlan:
        plan = db.query(ActionPlan).filter(ActionPlan.id == plan_id).first()
        if not plan:
            raise NotFoundException("ActionPlan", plan_id)

        plan.status = "rejected"
        db.commit()
        db.refresh(plan)

        AuditService.log_event(
            db=db,
            actor=actor,
            event_type="action_plan.rejected",
            payload={"plan_id": plan.id},
            conversation_id=plan.conversation_id,
        )

        ws_manager.broadcast_sync(
            event_type="case.updated",
            data={"plan_id": plan.id, "status": "rejected"},
            conversation_id=plan.conversation_id,
        )
        return plan
