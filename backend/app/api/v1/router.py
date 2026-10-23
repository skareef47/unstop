"""
API v1 Main Router Aggregator
"""
from fastapi import APIRouter
from app.api.v1.conversations import router as conversations_router
from app.api.v1.diagnostics import router as diagnostics_router
from app.api.v1.action_plans import router as action_plans_router
from app.api.v1.tickets import router as tickets_router
from app.api.v1.cases import router as cases_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.ws import router as ws_router

api_router = APIRouter()

api_router.include_router(conversations_router)
api_router.include_router(diagnostics_router)
api_router.include_router(action_plans_router)
api_router.include_router(tickets_router)
api_router.include_router(cases_router)
api_router.include_router(knowledge_router)
api_router.include_router(analytics_router)
api_router.include_router(ws_router)
