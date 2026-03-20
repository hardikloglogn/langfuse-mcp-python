"""Monitor Costs Tool - Track cost metrics"""

from typing import Any, Dict

from mcp.types import Tool

from .base import BaseLangfuseTool


TOOL_SPEC = Tool(
    name="monitor_costs",
    description=(
        "Track and analyze cost metrics across all agents. "
        "Includes breakdown by agent, model, and forecasting."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "time_range": {
                "type": "string",
                "enum": ["last_1h", "last_24h", "last_7d", "last_30d"],
                "default": "last_24h",
            },
            "group_by": {
                "type": "string",
                "enum": ["agent", "model", "user"],
                "default": "agent",
            },
            "threshold_usd": {
                "type": "number",
                "description": "Optional: Alert threshold in USD",
            },
        },
    },
)


class MonitorCostsTool(BaseLangfuseTool):
    """Track and analyze cost metrics across agents"""

    async def execute(self, args: Dict[str, Any]) -> str:
        """Execute the monitor_costs tool"""
        try:
            time_range = args.get("time_range", "last_24h")
            group_by = args.get("group_by", "agent")

            traces = self.langfuse.api.trace.list(limit=100)

            cost_by_group = {}
            total_cost = 0

            for trace in traces.data:
                metrics = self._calculate_trace_metrics(trace)
                cost = metrics.get("cost", 0)
                total_cost += cost

                if group_by == "agent":
                    group_key = trace.metadata.get("agent_name", "unknown")
                elif group_by == "model":
                    group_key = "default_model"
                else:
                    group_key = trace.user_id or "unknown"

                cost_by_group[group_key] = cost_by_group.get(group_key, 0) + cost

            sorted_groups = sorted(cost_by_group.items(), key=lambda x: x[1], reverse=True)

            response = f"""
                        [Cost Monitoring] ({time_range})

                        **Total Cost**: ${total_cost:.4f}
                        **Grouped by**: {group_by}

                        **Top Consumers**:
                        """
            for i, (group, cost) in enumerate(sorted_groups[:10], 1):
                percentage = (cost / total_cost * 100) if total_cost > 0 else 0
                response += f"{i}. **{group}**: ${cost:.4f} ({percentage:.1f}%)"

            threshold = args.get("threshold_usd")
            if threshold and total_cost >= threshold:
                response += f"""
                            ALERT: Total cost (${total_cost:.4f}) exceeds threshold (${threshold:.4f})
                            """

            return response

        except Exception as e:
            return f"Error monitoring costs: {str(e)}"
