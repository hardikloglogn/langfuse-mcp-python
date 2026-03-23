"""
Enhanced Analyze Performance Tool
MAJOR FIX: Now uses Metrics API instead of broken manual calculation
"""

from typing import Any, Dict
from mcp.types import Tool
from ..core.base_tool import BaseLangfuseTool
from .metrics import build_metrics_query

ANALYZE_PERFORMANCE_TOOL_SPEC = Tool(
    name="analyze_performance",
    description="Analyze agent performance using Langfuse Metrics API for accurate aggregated data.",
    inputSchema={
        "type": "object",
        "properties": {
            "agent_name": {"type": "string"},
            "time_range": {
                "type": "object",
                "properties": {
                    "from": {"type": "string", "format": "date-time"},
                    "to": {"type": "string", "format": "date-time"},
                },
            },
            "group_by": {
                "type": "string",
                "enum": ["hour", "day", "model", "user"],
                "default": "day",
            },
        },
    },
)

class AnalyzePerformanceTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            # FIXED: Use Metrics API instead of manual calculation
            filters = []
            
            if args.get("agent_name"):
                filters.append({
                    "column": "trace_tags",
                    "operator": "contains",
                    "value": args["agent_name"],
                })
            
            metrics_query = {
                "view": "observations",
                "metrics": [
                    "trace_count",
                    "total_cost",
                    "latency_p50",
                    "latency_p95",
                    "latency_p99",
                    "total_tokens",
                ],
                "filters": filters,
            }
            
            if args.get("time_range"):
                metrics_query["time_range"] = args["time_range"]
            
            group_by_map = {
                "hour": "timestamp",
                "day": "timestamp",
                "model": "providedModelName",
                "user": "userId",
            }
            
            group_by = args.get("group_by", "day")
            if group_by in ["hour", "day"]:
                metrics_query["granularity"] = group_by
            else:
                metrics_query["group_by"] = [group_by_map[group_by]]
            
            query, _ = build_metrics_query(metrics_query)
            metrics = await self._fetch_with_retry(
                self.langfuse.get_metrics,
                query
            )
            
            response = f"[METRICS] **Performance Analysis**\n\n"
            
            if args.get("agent_name"):
                response += f"**Agent**: {args['agent_name']}\n"
            
            response += f"**Grouped by**: {group_by}\n\n"
            
            # Format based on response type
            if hasattr(metrics, 'data') and metrics.data:
                for item in metrics.data[:20]:
                    timestamp = item.get("timestamp") if isinstance(item, dict) else getattr(item, "timestamp", None)
                    if timestamp is not None:
                        response += f"**{timestamp}**\n"
                    else:
                        group_field = group_by_map.get(group_by, "model")
                        group_value = item.get(group_field) if isinstance(item, dict) else getattr(item, group_field, None)
                        if group_value is not None:
                            response += f"**{group_value}**\n"
                    
                    trace_count = item.get("trace_count", 0) if isinstance(item, dict) else getattr(item, "trace_count", 0)
                    total_cost = item.get("total_cost", 0) if isinstance(item, dict) else getattr(item, "total_cost", 0)
                    latency_p50 = item.get("latency_p50", 0) if isinstance(item, dict) else getattr(item, "latency_p50", 0)
                    latency_p95 = item.get("latency_p95", 0) if isinstance(item, dict) else getattr(item, "latency_p95", 0)
                    total_tokens = item.get("total_tokens", 0) if isinstance(item, dict) else getattr(item, "total_tokens", 0)
                    
                    response += f"  - Traces: {int(trace_count):,}\n"
                    response += f"  - Cost: ${float(total_cost):.4f}\n"
                    response += f"  - Latency P50: {float(latency_p50):.0f}ms\n"
                    response += f"  - Latency P95: {float(latency_p95):.0f}ms\n"
                    response += f"  - Tokens: {int(total_tokens):,}\n\n"
            
            return response
        except Exception as e:
            return f"Error analyzing performance: {str(e)}"
