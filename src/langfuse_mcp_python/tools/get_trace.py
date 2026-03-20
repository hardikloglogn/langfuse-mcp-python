"""Get Trace Tool - Detailed trace inspection"""

from typing import Any, Dict

from mcp.types import Tool

from .base import BaseLangfuseTool


TOOL_SPEC = Tool(
    name="get_agent_trace",
    description=(
        "Retrieve detailed execution trace for a specific agent run. "
        "Includes all observations, LLM calls, tool executions, and metadata."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "trace_id": {
                "type": "string",
                "description": "The trace ID to retrieve",
            },
            "include_observations": {
                "type": "boolean",
                "default": True,
                "description": "Include detailed observations",
            },
            "depth": {
                "type": "string",
                "enum": ["minimal", "summary", "full"],
                "default": "full",
                "description": "Level of detail to include",
            },
        },
        "required": ["trace_id"],
    },
)


class GetTraceTool(BaseLangfuseTool):
    """Retrieve detailed trace information"""

    async def execute(self, args: Dict[str, Any]) -> str:
        """Execute the get_agent_trace tool"""
        try:
            trace_id = args["trace_id"]
            depth = args.get("depth", "full")

            trace = self.langfuse.api.trace.get(trace_id)

            if not trace:
                return f"Trace not found: {trace_id}"

            response = f"""
                        [Agent Trace Details]

                        **Trace ID**: {trace.id}
                        **Agent**: {trace.metadata.get('agent_name', 'unknown')}
                        **Session**: {trace.session_id or 'N/A'}
                        **User**: {trace.user_id or 'N/A'}
                        **Started**: {trace.timestamp.isoformat()}
                        **Status**: {self._get_trace_status(trace)}

                        """

            if depth in ["summary", "full"]:
                metrics = self._calculate_trace_metrics(trace)
                response += f"""
                            **Performance Metrics**:
                            - Duration: {metrics.get('latency_ms', 0):.0f}ms
                            - Tokens: {metrics.get('tokens', 0)}
                            - Cost: ${metrics.get('cost', 0):.4f}
                            - Observations: {metrics.get('observation_count', 0)}

                            """

            if depth == "full" and args.get("include_observations", True):
                observations = self.langfuse.api.observations.get_many(trace_id=trace_id)

                response += f"""
                            **Execution Steps** ({len(observations.data)} observations):

                            """
                for i, obs in enumerate(observations.data[:20], 1):
                    response += f"""
                                {i}. **{obs.name}** ({obs.type})
                                - Start: {obs.start_time.isoformat() if obs.start_time else 'N/A'}
                                - Duration: {self._calculate_observation_duration(obs)}ms
                                """
                    if obs.type == "GENERATION":
                        response += f"   - Model: {obs.model or 'N/A'}"
                        response += f"   - Tokens: {obs.usage.total if obs.usage else 0}"

            return response

        except Exception as e:
            return f"Error fetching trace: {str(e)}"
