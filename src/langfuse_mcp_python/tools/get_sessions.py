"""Get Sessions Tool - List agent sessions"""

from typing import Any, Dict

from mcp.types import Tool

from .base import BaseLangfuseTool


TOOL_SPEC = Tool(
    name="get_agent_sessions",
    description=(
        "List and retrieve multi-turn agent sessions. "
        "Useful for tracking conversational agents."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "Optional: Specific session ID",
            },
            "user_id": {
                "type": "string",
                "description": "Optional: Filter by user ID",
            },
            "status": {
                "type": "string",
                "enum": ["active", "completed", "failed"],
                "description": "Filter by session status",
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "minimum": 1,
                "maximum": 200,
            },
        },
    },
)


class GetSessionsTool(BaseLangfuseTool):
    """List and retrieve multi-turn agent sessions"""

    async def execute(self, args: Dict[str, Any]) -> str:
        """Execute the get_agent_sessions tool"""
        try:
            session_id = args.get("session_id")
            user_id = args.get("user_id")
            limit = args.get("limit", 50)

            traces = self.langfuse.api.trace.list(
                limit=limit,
                session_id=session_id,
                user_id=user_id,
            )

            sessions = {}
            for trace in traces.data:
                sid = trace.session_id or "no-session"
                if sid not in sessions:
                    sessions[sid] = []
                sessions[sid].append(trace)

            response = f"""
                        [Agent Sessions]

                        **Total Sessions**: {len(sessions)}
                        **Total Traces**: {len(traces.data)}

                        """
            for i, (sid, session_traces) in enumerate(list(sessions.items())[:10], 1):
                first_trace = session_traces[0]
                last_trace = session_traces[-1]

                response += f"""
                            **{i}. Session {sid[:12]}...**
                            - Agent: {first_trace.metadata.get('agent_name', 'unknown')}
                            - User: {first_trace.user_id or 'N/A'}
                            - Turns: {len(session_traces)}
                            - Started: {first_trace.timestamp.isoformat()}
                            - Last Activity: {last_trace.timestamp.isoformat()}

                            """

            return response

        except Exception as e:
            return f"Error fetching sessions: {str(e)}"
