# contracts/events/reports.py
"""
Async Job / Report Event Schemas

Schemas for events fired when a long-running, user-initiated job finishes
(a generated report, a data export, etc.). The `data` payload carries the
identifiers needed to deep link the user straight to the result.
"""

from contracts.event_types import EventType
from contracts.event_registry import register_event_model
from pydantic import BaseModel
from typing import Optional


@register_event_model(EventType.WEEKLY_REPORT_READY)
class WeeklyReportReadyData(BaseModel):
    report_id: str
    period: Optional[str] = None


@register_event_model(EventType.EXPORT_READY)
class ExportReadyData(BaseModel):
    export_id: str
    download_url: Optional[str] = None
    format: Optional[str] = None
