"""
Analytics API Endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    IncidentTrendResponse,
    ResolutionMetricsResponse,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_overview_metrics(db: Session = Depends(get_db)):
    """Retrieve high-level incident, ticket, and conversation overview metrics."""
    return AnalyticsService.get_overview(db)


@router.get("/incidents", response_model=IncidentTrendResponse)
def get_incident_trends(db: Session = Depends(get_db)):
    """Retrieve 7-day incident frequency and severity trends."""
    return AnalyticsService.get_incident_trends(db)


@router.get("/resolution", response_model=ResolutionMetricsResponse)
def get_resolution_metrics(db: Session = Depends(get_db)):
    """Retrieve troubleshooting resolution and escalation efficiency metrics."""
    return AnalyticsService.get_resolution_metrics(db)
