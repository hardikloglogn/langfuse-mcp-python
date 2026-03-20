"""MCP Tools for Multi-Agent monitoring"""

from .watch_agents import TOOL_SPEC as WATCH_AGENTS_SPEC, WatchAgentsTool
from .get_trace import TOOL_SPEC as GET_TRACE_SPEC, GetTraceTool
from .analyze_performance import TOOL_SPEC as ANALYZE_PERFORMANCE_SPEC, AnalyzePerformanceTool
from .debug_failure import TOOL_SPEC as DEBUG_FAILURE_SPEC, DebugFailureTool
from .monitor_costs import TOOL_SPEC as MONITOR_COSTS_SPEC, MonitorCostsTool
from .get_sessions import TOOL_SPEC as GET_SESSIONS_SPEC, GetSessionsTool

TOOL_SPECS = [
    WATCH_AGENTS_SPEC,
    GET_TRACE_SPEC,
    ANALYZE_PERFORMANCE_SPEC,
    DEBUG_FAILURE_SPEC,
    MONITOR_COSTS_SPEC,
    GET_SESSIONS_SPEC,
]

__all__ = [
    "TOOL_SPECS",
    "WatchAgentsTool",
    "GetTraceTool",
    "AnalyzePerformanceTool",
    "DebugFailureTool",
    "MonitorCostsTool",
    "GetSessionsTool",
]
