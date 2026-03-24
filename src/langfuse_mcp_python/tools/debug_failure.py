"""Debug Failure Tool - Diagnose failed executions"""

from typing import Any, Dict

from mcp.types import Tool

from .base import BaseLangfuseTool


TOOL_SPEC = Tool(
    name="debug_agent_failure",
    description=(
        "Investigate and diagnose failed agent executions. "
        "Provides error details, context, and suggestions for resolution."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "trace_id": {
                "type": "string",
                "description": "Trace ID of the failed execution",
            },
            "include_context": {
                "type": "boolean",
                "default": True,
                "description": "Include execution context",
            },
            "include_similar_failures": {
                "type": "boolean",
                "default": True,
                "description": "Find similar failure patterns",
            },
        },
        "required": ["trace_id"],
    },
)


class DebugFailureTool(BaseLangfuseTool):
    """Investigate failed agent executions"""

    async def execute(self, args: Dict[str, Any]) -> str:
        """Execute the debug_agent_failure tool"""
        try:
            trace_id = args["trace_id"]

            trace = self.langfuse.api.trace.get(trace_id)

            if not trace:
                return f"Trace not found: {trace_id}"

            status = self._get_trace_status(trace)

            response = f"""
                        [Debug Agent Failure]

                        **Trace ID**: {trace.id}
                        **Agent**: {trace.metadata.get('agent_name', 'unknown')}
                        **Status**: {status}

                        """

            observations = self.langfuse.api.observations.get_many(trace_id=trace_id)

            error_observations = []
            for obs in observations.data:
                if obs.level == "ERROR" or (obs.status_message and "error" in obs.status_message.lower()):
                    error_observations.append(obs)

            if error_observations:
                response += f"""
                            **Failure Point**: Step {error_observations[0].name}

                            **Error Details**:
                            """
                for err_obs in error_observations[:3]:
                    response += f"- {err_obs.status_message or 'No error message'}"
            else:
                response += "No specific error observations found"

            if args.get("include_similar_failures", True):
                similar = []
                recent_traces = self.langfuse.api.trace.list(limit=100)

                for t in recent_traces.data:
                    if (
                        t.id != trace_id
                        and self._get_trace_status(t) == "error"
                        and t.metadata.get("agent_name") == trace.metadata.get("agent_name")
                    ):
                        similar.append(t)

                if similar:
                    response += f"""
                                **Similar Failures Found**: {len(similar)} in recent history
                                - Most recent: {similar[0].timestamp.isoformat()}
                                """

            return response

        except Exception as e:
            return f"Error debugging failure: {str(e)}"
