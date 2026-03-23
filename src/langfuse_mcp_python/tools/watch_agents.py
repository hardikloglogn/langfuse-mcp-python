"""
Enhanced Watch Agents Tool
FIXED: Server-side filtering, proper metrics, retry logic
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from mcp.types import Tool
from ..core.base_tool import BaseLangfuseTool

WATCH_AGENTS_TOOL_SPEC = Tool(
    name="watch_agents",
    description="Monitor active agents in real-time with performance metrics.",
    inputSchema={
        "type": "object",
        "properties": {
            "session_ids": {
                "type": "array",
                "items": {"type": "string"},
            },
            "agent_names": {
                "type": "array",
                "items": {"type": "string"},
            },
            "time_window": {
                "type": "string",
                "enum": ["last_1h", "last_24h", "last_7d"],
                "default": "last_1h",
            },
            "user_id": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "limit": {"type": "integer", "default": 10},
        },
    },
)

class WatchAgentsTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            time_window = args.get("time_window", "last_1h")
            hours_map = {"last_1h": 1, "last_24h": 24, "last_7d": 168}
            hours = hours_map.get(time_window, 1)
            
            # Calculate time range
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours)
            
            # FIXED: Use server-side filtering instead of client-side
            fetch_args = {
                "from_timestamp": start_time,
                "to_timestamp": end_time,
                "limit": args.get("limit", 10),
            }
            
            if args.get("user_id"):
                fetch_args["user_id"] = args["user_id"]
            
            if args.get("tags"):
                fetch_args["tags"] = args["tags"]
            
            # Fetch traces with server-side filtering
            traces_response = await self._fetch_with_retry(
                self.langfuse.api.trace.list,
                **fetch_args
            )
            
            # Client-side filter for session_ids and agent_names (not supported server-side)
            traces = traces_response.data
            
            if args.get("session_ids"):
                traces = [t for t in traces if t.session_id in args["session_ids"]]
            
            if args.get("agent_names"):
                agent_names = set(args["agent_names"])
                traces = [
                    t for t in traces
                    if t.metadata and t.metadata.get("agent_name") in agent_names
                ]
            
            if not traces:
                return f"No active agents found in {time_window}"
            
            response = f"[SEARCH] **Active Agent Monitoring** ({time_window})\n\n"
            response += f"**Total Traces**: {len(traces)}\n"
            response += f"**Showing**: Top {min(len(traces), args.get('limit', 10))}\n\n"
            
            for i, trace in enumerate(traces[:args.get("limit", 10)], 1):
                # FIXED: Use proper metrics calculation
                metrics = self._calculate_trace_metrics(trace)
                
                response += f"{i}. **{trace.metadata.get('agent_name', 'unknown')}** "
                response += f"(Trace: {trace.id[:12]}...)\n"
                response += f"   - Status: {self._get_trace_status(trace)}\n"
                response += f"   - Started: {self._format_datetime(trace.timestamp)}\n"
                response += f"   - Duration: {self._format_duration(metrics['latency_ms'])}\n"
                response += f"   - Cost: {self._format_cost(metrics['cost'])}\n"
                response += f"   - Tokens: {self._format_tokens(metrics['tokens'])}\n"
                
                if trace.session_id:
                    response += f"   - Session: {trace.session_id[:12]}...\n"
                
                response += "\n"
            
            return response
        except Exception as e:
            self.logger.error("Error watching agents", error=str(e))
            return f"Error watching agents: {str(e)}"
