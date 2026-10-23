"""
Classification, Sentiment, and Incident Analysis Service
"""
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.case_analysis import CaseAnalysis
from app.schemas.case_analysis import CaseAnalysisResponse, HypothesisItem
from app.services.llm_provider.factory import get_llm_provider
from app.prompts.templates import CLASSIFICATION_PROMPT_TEMPLATE
from app.policies.escalation_policy import EscalationPolicy
from app.websockets.manager import ws_manager
from app.core.errors import NotFoundException


class ClassificationService:
    @classmethod
    def analyze_conversation(cls, db: Session, conversation_id: str) -> CaseAnalysis:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise NotFoundException("Conversation", conversation_id)

        messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

        history_lines = [f"{m.role.upper()}: {m.content}" for m in messages]
        conversation_context = "\n".join(history_lines) if history_lines else "No messages recorded."

        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(conversation_context=conversation_context)

        llm = get_llm_provider()
        raw_result = llm.generate_structured_json(prompt=prompt, schema=CaseAnalysisResponse)

        intent = raw_result.get("intent", "troubleshooting")
        product_area = raw_result.get("product_area", conversation.product_area)
        sentiment = raw_result.get("sentiment", "neutral")
        sentiment_score = float(raw_result.get("sentiment_score", 0.0))
        urgency = raw_result.get("urgency", "low")
        impact_scope = raw_result.get("impact_scope", "single_user")
        confirmed_facts = raw_result.get("confirmed_facts", [])
        hypotheses = raw_result.get("hypotheses", [])
        missing_info = raw_result.get("missing_information", [])

        # Run deterministic severity policy
        is_widespread = impact_scope.lower() == "widespread" or "500" in conversation_context and "all users" in conversation_context
        is_security = "security" in intent.lower() or "breach" in conversation_context.lower()

        # Map impact based on scope and urgency
        impact_level = "moderate"
        if is_widespread:
            impact_level = "complete_outage"
        elif impact_scope in ("organization", "multiple_users"):
            impact_level = "major"
        elif urgency == "low":
            impact_level = "minor"

        severity = EscalationPolicy.calculate_severity(
            impact=impact_level,
            urgency=urgency,
            scope=impact_scope,
            sla_risk="at_risk" if urgency in ("high", "critical") else "safe",
            is_security_incident=is_security,
            is_widespread_outage=is_widespread,
        )

        analysis = CaseAnalysis(
            conversation_id=conversation_id,
            intent=intent,
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            urgency=urgency,
            severity_score=severity.final_score,
            impact_scope=impact_scope,
            confirmed_facts=confirmed_facts,
            hypotheses=hypotheses,
            missing_information=missing_info,
            escalation_required=severity.escalation_decision,
        )
        db.add(analysis)

        # Update conversation status if escalated
        if severity.escalation_decision and conversation.status not in ("resolved", "closed"):
            conversation.status = "escalated"

        conversation.product_area = product_area
        db.commit()
        db.refresh(analysis)

        # Broadcast live event
        ws_manager.broadcast_sync(
            event_type="classification.completed",
            data={
                "analysis_id": analysis.id,
                "intent": analysis.intent,
                "severity_score": analysis.severity_score,
                "severity_label": severity.severity_label,
                "escalation_required": analysis.escalation_required,
                "confirmed_facts_count": len(confirmed_facts),
            },
            conversation_id=conversation_id,
        )

        return analysis
