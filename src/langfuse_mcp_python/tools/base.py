"""Shared helpers for Langfuse-backed tools"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


class BaseLangfuseTool:
    """Common helpers for Langfuse tools"""

    def __init__(self, langfuse_client):
        self.langfuse = langfuse_client

    def _get_trace_status(self, trace) -> str:
        """Determine trace status"""
        if hasattr(trace, "level") and trace.level == "ERROR":
            return "error"
        return "completed"

    def _calculate_trace_metrics(self, trace) -> Dict[str, Any]:
        """Calculate metrics for a trace"""
        return {
            "latency_ms": 0,
            "tokens": 0,
            "cost": 0,
            "observation_count": 0,
        }

    def _calculate_observation_duration(self, obs) -> float:
        """Calculate observation duration"""
        if obs.start_time and obs.end_time:
            delta = obs.end_time - obs.start_time
            return delta.total_seconds() * 1000
        return 0.0

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 datetime strings safely"""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _coerce_to_naive_utc(self, dt: datetime) -> datetime:
        """Normalize datetimes for safe comparisons"""
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    def _get_group_key(self, trace, group_by: str) -> str:
        """Compute group key for aggregation"""
        ts = self._coerce_to_naive_utc(trace.timestamp)
        if group_by == "day":
            return ts.date().isoformat()
        if group_by == "hour":
            return ts.replace(minute=0, second=0, microsecond=0).isoformat()
        if group_by == "agent":
            return trace.metadata.get("agent_name", "unknown")
        return trace.session_id or "no-session"

    def _format_time_range_label(
        self,
        start: Optional[datetime],
        end: Optional[datetime],
        count: int,
    ) -> str:
        """Format the time range label for reporting"""
        if not start and not end:
            return f"Last {count} traces"
        start_label = start.isoformat() if start else "beginning"
        end_label = end.isoformat() if end else "now"
        return f"{start_label} to {end_label}"
