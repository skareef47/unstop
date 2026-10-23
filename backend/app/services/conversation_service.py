"""
Conversation and Chat Orchestration Service
"""
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.case_analysis import CaseAnalysis
from app.schemas.message import MessageSubmitResponse, MessageResponse, Citation
from app.services.knowledge_service import KnowledgeService
from app.services.classification_service import ClassificationService
from app.services.llm_provider.factory import get_llm_provider
from app.prompts.templates import CUSTOMER_SUPPORT_SYSTEM_PROMPT
from app.core.security import detect_prompt_injection, sanitize_input
from app.websockets.manager import ws_manager
from app.core.errors import NotFoundException


class ConversationService:
    @staticmethod
    def create_conversation(
        db: Session,
        product_area: str = "api_gateway",
        environment: str = "production",
    ) -> Conversation:
        conversation = Conversation(
            product_area=product_area,
            environment=environment,
            status="active",
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        ws_manager.broadcast_sync(
            event_type="case.updated",
            data={
                "conversation_id": conversation.id,
                "status": conversation.status,
                "product_area": conversation.product_area,
            },
            conversation_id=conversation.id,
        )
        return conversation

    @staticmethod
    def list_conversations(
        db: Session,
        status: Optional[str] = None,
        product_area: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Conversation], int]:
        q = db.query(Conversation)
        if status:
            q = q.filter(Conversation.status == status)
        if product_area:
            q = q.filter(Conversation.product_area == product_area)
        total = q.count()
        items = q.order_by(Conversation.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    @classmethod
    def submit_message(
        cls,
        db: Session,
        conversation_id: str,
        content: str,
        client_message_id: Optional[str] = None,
    ) -> MessageSubmitResponse:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise NotFoundException("Conversation", conversation_id)

        # 1. Idempotency Check: if client_message_id already exists, return existing exchange
        if client_message_id:
            existing_user_msg = (
                db.query(Message)
                .filter(
                    Message.conversation_id == conversation_id,
                    Message.client_message_id == client_message_id,
                )
                .first()
            )
            if existing_user_msg:
                # Find subsequent assistant response
                assistant_msg = (
                    db.query(Message)
                    .filter(
                        Message.conversation_id == conversation_id,
                        Message.role == "assistant",
                        Message.created_at >= existing_user_msg.created_at,
                    )
                    .order_by(Message.created_at.asc())
                    .first()
                )
                if assistant_msg:
                    return MessageSubmitResponse(
                        user_message=MessageResponse.model_validate(existing_user_msg),
                        assistant_message=MessageResponse.model_validate(assistant_msg),
                        citations=[],
                    )

        # 2. Sanitize and Prompt Injection Defense
        sanitized_content = sanitize_input(content)
        is_injection = detect_prompt_injection(sanitized_content)

        # 3. Persist User Message
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=sanitized_content,
            client_message_id=client_message_id,
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)

        # Broadcast user message created
        ws_manager.broadcast_sync(
            event_type="message.created",
            data={
                "message_id": user_message.id,
                "role": "user",
                "content": user_message.content,
            },
            conversation_id=conversation_id,
        )

        # 4. Handle Injection attempt safely
        if is_injection:
            refusal_text = (
                "I cannot follow instructions to override system guidelines or reveal internal prompts. "
                "How can I assist you with diagnosing your technical issue within support boundaries?"
            )
            assistant_message = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=refusal_text,
            )
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)
            return MessageSubmitResponse(
                user_message=MessageResponse.model_validate(user_message),
                assistant_message=MessageResponse.model_validate(assistant_message),
                citations=[],
            )

        # 5. Knowledge Retrieval Pipeline
        search_results = KnowledgeService.search(db, query=sanitized_content, top_k=3)
        citations = KnowledgeService.to_citations(search_results)

        knowledge_context = ""
        if search_results:
            knowledge_blocks = []
            for r in search_results:
                knowledge_blocks.append(
                    f"--- Source: {r.source} | Section: {r.section} ---\n{r.content}"
                )
            knowledge_context = "\n\nRetrieved Knowledge Base Documentation:\n" + "\n\n".join(knowledge_blocks)

        # 6. Retrieve conversation history
        prior_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

        formatted_messages = []
        for m in prior_messages:
            formatted_messages.append({"role": m.role, "content": m.content})

        system_prompt = CUSTOMER_SUPPORT_SYSTEM_PROMPT
        if knowledge_context:
            system_prompt += f"\n\n{knowledge_context}"

        # 7. Generate AI Assistant Response
        llm = get_llm_provider()
        ai_reply = llm.generate_chat_response(
            messages=formatted_messages,
            system_prompt=system_prompt,
        )

        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_reply,
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)

        # Broadcast assistant message
        ws_manager.broadcast_sync(
            event_type="message.created",
            data={
                "message_id": assistant_message.id,
                "role": "assistant",
                "content": assistant_message.content,
            },
            conversation_id=conversation_id,
        )

        # 8. Recompute structured case analysis
        analysis = None
        try:
            analysis_obj = ClassificationService.analyze_conversation(db, conversation_id)
            analysis = {
                "id": analysis_obj.id,
                "intent": analysis_obj.intent,
                "urgency": analysis_obj.urgency,
                "severity_score": analysis_obj.severity_score,
                "escalation_required": analysis_obj.escalation_required,
                "confirmed_facts": analysis_obj.confirmed_facts,
            }
        except Exception:
            pass

        # Suggest diagnostic tool if applicable
        diagnostic_suggested = None
        lower_content = sanitized_content.lower()
        if "401" in lower_content or "key rotation" in lower_content:
            diagnostic_suggested = "auth_401_key_rotation"
        elif "crm" in lower_content or "sync" in lower_content:
            diagnostic_suggested = "crm_sync_timeout"
        elif "outage" in lower_content or "500" in lower_content:
            diagnostic_suggested = "platform_outage_triage"

        return MessageSubmitResponse(
            user_message=MessageResponse.model_validate(user_message),
            assistant_message=MessageResponse.model_validate(assistant_message),
            citations=citations,
            analysis=analysis,
            diagnostic_suggested=diagnostic_suggested,
        )
