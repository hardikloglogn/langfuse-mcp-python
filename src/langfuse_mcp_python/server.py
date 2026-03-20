"""
 Multi-Agent Monitoring MCP Server
===========================================

A Model Context Protocol (MCP) server for monitoring multi-agent systems
using Langfuse observability platform.

Author: Your Name
Version: 1.0.0
"""

import os
import asyncio
import argparse
from typing import Any, Dict, List, Sequence, Optional
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import (
    TOOL_SPECS,
    AnalyzePerformanceTool,
    DebugFailureTool,
    GetSessionsTool,
    GetTraceTool,
    MonitorCostsTool,
    WatchAgentsTool,
)
from .fastmcp_server import create_fastmcp_server

# Langfuse imports
from langfuse import Langfuse

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env from current directory or parent directories
env_path = Path(__file__).parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Try to find .env in current working directory


@dataclass
class AgentMetrics:
    """Agent performance metrics"""
    trace_id: str
    agent_name: str
    duration_ms: float
    token_usage: int
    cost_usd: float
    status: str
    timestamp: datetime


class LangfuseMonitoringServer:
    """MCP Server for agent monitoring via Langfuse"""
    
    def __init__(self):
        self.server = Server("langfuse-monitoring")
        self.langfuse = None
        self._setup_langfuse()
        self.tools = {
            "watch_agents": WatchAgentsTool(self.langfuse),
            "get_agent_trace": GetTraceTool(self.langfuse),
            "analyze_agent_performance": AnalyzePerformanceTool(self.langfuse),
            "debug_agent_failure": DebugFailureTool(self.langfuse),
            "monitor_costs": MonitorCostsTool(self.langfuse),
            "get_agent_sessions": GetSessionsTool(self.langfuse),
        }
        self._register_tools()
    
    def _setup_langfuse(self):
        """Initialize Langfuse client"""
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
        
        if not public_key or not secret_key:
            raise ValueError(
                "Missing Langfuse credentials. Set LANGFUSE_PUBLIC_KEY and "
                "LANGFUSE_SECRET_KEY environment variables."
            )
        
        self.langfuse = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host
        )
        
        print(f"Connected to Langfuse at {host}")
    
    def _register_tools(self):
        """Register all MCP tools"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available monitoring tools"""
            return TOOL_SPECS
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[TextContent]:
            """Execute MCP tool"""
            tool = self.tools.get(name)
            if not tool:
                raise ValueError(f"Unknown tool: {name}")
            result = await tool.execute(arguments)
            return [TextContent(type="text", text=result)]

    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )

def _coerce_bool(value: Optional[str], default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main():
    """Entry point"""
    parser = argparse.ArgumentParser(description="Langfuse Monitoring MCP Server")
    parser.add_argument(
        "--transport",
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        choices=["stdio", "streamable-http", "http", "sse"],
        help="Transport to use (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST"),
        help="Host to bind for HTTP transports (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="Port to bind for HTTP transports (default: 8000)",
    )
    parser.add_argument(
        "--path",
        default=os.getenv("MCP_PATH", "/mcp"),
        help="HTTP path for Streamable HTTP transport (default: /mcp)",
    )
    parser.add_argument(
        "--json-response",
        action="store_true",
        default=_coerce_bool(os.getenv("MCP_JSON_RESPONSE"), False),
        help="Force JSON-only responses for HTTP transport",
    )
    parser.add_argument(
        "--no-json-response",
        action="store_false",
        dest="json_response",
        help="Disable JSON-only response mode",
    )
    parser.add_argument(
        "--stateless-http",
        action="store_true",
        default=_coerce_bool(os.getenv("MCP_STATELESS_HTTP"), False),
        help="Run Streamable HTTP in stateless mode",
    )
    parser.add_argument(
        "--stateful-http",
        action="store_false",
        dest="stateless_http",
        help="Run Streamable HTTP with sessions (stateful)",
    )

    args = parser.parse_args()
    transport = "streamable-http" if args.transport == "http" else args.transport

    print("Starting Multi-Agent Monitoring MCP Server...")
    server = LangfuseMonitoringServer()

    if transport == "stdio":
        asyncio.run(server.run())
        return

    if transport not in {"streamable-http", "sse"}:
        raise ValueError(f"Unsupported transport: {transport}")

    host = args.host or "127.0.0.1"
    port = args.port or 8000
    path = args.path or "/mcp"
    if not path.startswith("/"):
        path = f"/{path}"

    print(f"Streamable HTTP endpoint: http://{host}:{port}{path}")
    http_server = create_fastmcp_server(
        tools=server.tools,
        host=host,
        port=port,
        path=path,
        json_response=args.json_response,
        stateless_http=args.stateless_http,
    )
    http_server.run(
        transport=transport,
    )


if __name__ == "__main__":
    main()
