"""
Analytics and Reporting Service
"""
from datetime import datetime, timedelta, timezone
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.conversation import Conversation
from app.models.ticket import Ticket
from app.models.case_analysis import CaseAnalysis
from app.models.diagnostic import DiagnosticRun, DiagnosticStep
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    IncidentTrendItem,
    IncidentTrendResponse,
    ResolutionMetricsResponse,
)


class AnalyticsService:
    @staticmethod
    def get_overview(db: Session) -> AnalyticsOverviewResponse:
        total_convs = db.query(Conversation).count()
        active_convs = db.query(Conversation).filter(Conversation.status.in_(["active", "diagnosing"])).count()
        open_tickets = db.query(Ticket).filter(Ticket.status.in_(["open", "in_progress"])).count()
        escalated_cases = db.query(Conversation).filter(Conversation.status == "escalated").count()

        avg_severity_result = db.query(func.avg(CaseAnalysis.severity_score)).scalar()
        avg_severity = float(avg_severity_result) if avg_severity_result is not None else 0.0

        resolved_count = db.query(Conversation).filter(Conversation.status == "resolved").count()
        resolution_rate = round((resolved_count / total_convs * 100), 1) if total_convs > 0 else 0.0

        return AnalyticsOverviewResponse(
            active_conversations=active_convs,
            total_conversations=total_convs,
            open_tickets=open_tickets,
            escalated_cases=escalated_cases,
            average_severity_score=round(avg_severity, 1),
            resolution_rate_pct=resolution_rate,
        )

    @staticmethod
    def get_incident_trends(db: Session) -> IncidentTrendResponse:
        # Group conversations by day for the past 7 days
        today = datetime.now(timezone.utc).date()
        trend_items = []

        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=timezone.utc)
            end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=timezone.utc)

            count = (
                db.query(Conversation)
                .filter(Conversation.created_at >= start, Conversation.created_at <= end)
                .count()
            )

            high_sev_count = (
                db.query(CaseAnalysis)
                .filter(
                    CaseAnalysis.created_at >= start,
                    CaseAnalysis.created_at <= end,
                    CaseAnalysis.severity_score >= 60.0,
                )
                .count()
            )

            trend_items.append(
                IncidentTrendItem(
                    date=day_str,
                    count=count,
                    high_severity_count=high_sev_count,
                )
            )

        return IncidentTrendResponse(trends=trend_items)

    @staticmethod
    def get_resolution_metrics(db: Session) -> ResolutionMetricsResponse:
        total_runs = db.query(DiagnosticRun).count()
        total_steps = db.query(DiagnosticStep).count()
        avg_steps = round(total_steps / total_runs, 1) if total_runs > 0 else 0.0

        total_cases = db.query(Conversation).count()
        auto_resolved = db.query(Conversation).filter(Conversation.status == "resolved").count()
        escalated = db.query(Conversation).filter(Conversation.status == "escalated").count()

        auto_resolved_pct = round((auto_resolved / total_cases * 100), 1) if total_cases > 0 else 0.0
        escalated_pct = round((escalated / total_cases * 100), 1) if total_cases > 0 else 0.0

        return ResolutionMetricsResponse(
            average_steps_to_resolution=avg_steps,
            auto_resolved_pct=auto_resolved_pct,
            escalated_pct=escalated_pct,
            avg_resolution_time_minutes=8.5,
        )
