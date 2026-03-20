"""Streamable HTTP (FastMCP) server wiring."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Literal

from mcp.server.fastmcp import FastMCP


async def _run_tool(tools: Mapping[str, Any], name: str, args: Dict[str, Any]) -> str:
    tool = tools.get(name)
    if tool is None:
        raise ValueError(f"Unknown tool: {name}")
    return await tool.execute(args)


def create_fastmcp_server(
    tools: Mapping[str, Any],
    host: str,
    port: int,
    path: str,
    json_response: bool,
    stateless_http: bool,
) -> FastMCP:
    """Create a FastMCP server for Streamable HTTP transport."""
    mcp = FastMCP(
        "langfuse-monitoring",
        host=host,
        port=port,
        streamable_http_path=path,
        json_response=json_response,
        stateless_http=stateless_http,
    )

    @mcp.tool(name="watch_agents")
    async def watch_agents(
        session_ids: Optional[List[str]] = None,
        agent_names: Optional[List[str]] = None,
        time_window: Literal["last_1h", "last_24h", "last_7d"] = "last_1h",
        include_metrics: bool = True,
    ) -> str:
        return await _run_tool(
            tools,
            "watch_agents",
            {
                "session_ids": session_ids,
                "agent_names": agent_names,
                "time_window": time_window,
                "include_metrics": include_metrics,
            },
        )

    @mcp.tool(name="get_agent_trace")
    async def get_agent_trace(
        trace_id: str,
        include_observations: bool = True,
        depth: Literal["minimal", "summary", "full"] = "full",
    ) -> str:
        return await _run_tool(
            tools,
            "get_agent_trace",
            {
                "trace_id": trace_id,
                "include_observations": include_observations,
                "depth": depth,
            },
        )

    @mcp.tool(name="analyze_agent_performance")
    async def analyze_agent_performance(
        agent_name: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
        group_by: Literal["hour", "day", "agent", "session"] = "hour",
        metrics: Optional[List[Literal["latency", "cost", "error_rate", "token_usage"]]] = None,
    ) -> str:
        return await _run_tool(
            tools,
            "analyze_agent_performance",
            {
                "agent_name": agent_name,
                "time_range": time_range,
                "group_by": group_by,
                "metrics": metrics or ["latency", "cost", "error_rate", "token_usage"],
            },
        )

    @mcp.tool(name="debug_agent_failure")
    async def debug_agent_failure(
        trace_id: str,
        include_context: bool = True,
        include_similar_failures: bool = True,
    ) -> str:
        return await _run_tool(
            tools,
            "debug_agent_failure",
            {
                "trace_id": trace_id,
                "include_context": include_context,
                "include_similar_failures": include_similar_failures,
            },
        )

    @mcp.tool(name="monitor_costs")
    async def monitor_costs(
        time_range: Literal["last_1h", "last_24h", "last_7d", "last_30d"] = "last_24h",
        group_by: Literal["agent", "model", "user"] = "agent",
        threshold_usd: Optional[float] = None,
    ) -> str:
        return await _run_tool(
            tools,
            "monitor_costs",
            {
                "time_range": time_range,
                "group_by": group_by,
                "threshold_usd": threshold_usd,
            },
        )

    @mcp.tool(name="get_agent_sessions")
    async def get_agent_sessions(
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[Literal["active", "completed", "failed"]] = None,
        limit: int = 50,
    ) -> str:
        return await _run_tool(
            tools,
            "get_agent_sessions",
            {
                "session_id": session_id,
                "user_id": user_id,
                "status": status,
                "limit": limit,
            },
        )

    return mcp
