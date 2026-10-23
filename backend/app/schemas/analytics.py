"""
Analytics Schemas
"""
from typing import List, Optional
from pydantic import BaseModel


class AnalyticsOverviewResponse(BaseModel):
    active_conversations: int
    total_conversations: int
    open_tickets: int
    escalated_cases: int
    average_severity_score: float
    resolution_rate_pct: float


class IncidentTrendItem(BaseModel):
    date: str
    count: int
    high_severity_count: int


class IncidentTrendResponse(BaseModel):
    trends: List[IncidentTrendItem]


class ResolutionMetricsResponse(BaseModel):
    average_steps_to_resolution: float
    auto_resolved_pct: float
    escalated_pct: float
    avg_resolution_time_minutes: float
