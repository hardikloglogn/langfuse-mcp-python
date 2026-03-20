"""Watch Agents Tool - Real-time agent monitoring"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from mcp.types import Tool

from .base import BaseLangfuseTool


TOOL_SPEC = Tool(
    name="watch_agents",
    description=(
        "Monitor all active agents in real-time. "
        "Returns current status, performance metrics, and execution details."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "session_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: Filter by specific session IDs",
            },
            "agent_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: Filter by agent names",
            },
            "time_window": {
                "type": "string",
                "enum": ["last_1h", "last_24h", "last_7d"],
                "default": "last_1h",
                "description": "Time window for monitoring",
            },
            "include_metrics": {
                "type": "boolean",
                "default": True,
                "description": "Include performance metrics",
            },
        },
    },
)


class WatchAgentsTool(BaseLangfuseTool):
    """Monitor active LangGraph agents in real-time"""

    async def execute(self, args: Dict[str, Any]) -> str:
        """Execute the watch_agents tool"""
        try:
            time_window = args.get("time_window", "last_1h")
            session_ids = args.get("session_ids")
            agent_names = args.get("agent_names")

            hours_map = {"last_1h": 1, "last_24h": 24, "last_7d": 168}
            hours = hours_map.get(time_window, 1)
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            start_time_naive = self._coerce_to_naive_utc(start_time)

            traces = self.langfuse.api.trace.list(limit=100, page=1)

            filtered_traces = []
            for trace in traces.data:
                trace_time = self._coerce_to_naive_utc(trace.timestamp)
                if trace_time < start_time_naive:
                    continue
                if session_ids and trace.session_id not in session_ids:
                    continue
                if agent_names:
                    agent_name = trace.metadata.get("agent_name", "")
                    if agent_name not in agent_names:
                        continue
                filtered_traces.append(trace)

            agents_info = []
            for trace in filtered_traces[:10]:
                agent_info = {
                    "trace_id": trace.id,
                    "agent_name": trace.metadata.get("agent_name", "unknown"),
                    "session_id": trace.session_id,
                    "status": self._get_trace_status(trace),
                    "start_time": trace.timestamp.isoformat(),
                    "metadata": trace.metadata,
                }
                if args.get("include_metrics", True):
                    agent_info["metrics"] = self._calculate_trace_metrics(trace)
                agents_info.append(agent_info)

            response = f"""
                        [Active Agent Monitoring] ({time_window})

                        **Total Traces Found**: {len(filtered_traces)}
                        **Showing**: Top {len(agents_info)} traces

                        """
            for i, agent in enumerate(agents_info, 1):
                response += f"""
                            **{i}. {agent['agent_name']}** (Trace: {agent['trace_id'][:12]}...)
                            - Status: {agent['status']}
                            - Session: {agent.get('session_id', 'N/A')}
                            - Started: {agent['start_time']}
                            """
                if "metrics" in agent:
                    m = agent["metrics"]
                    response += f"""   - Latency: {m.get('latency_ms', 0):.0f}ms
                                - Tokens: {m.get('tokens', 0)}
                                - Cost: ${m.get('cost', 0):.4f}
                                """

            return response

        except Exception as e:
            return f"Error monitoring agents: {str(e)}"
