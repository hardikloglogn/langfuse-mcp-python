"""Analyze Performance Tool - Aggregate performance metrics"""

from typing import Any, Dict

from mcp.types import Tool

from .base import BaseLangfuseTool


TOOL_SPEC = Tool(
    name="analyze_agent_performance",
    description=(
        "Analyze and aggregate performance metrics across multiple agent runs. "
        "Provides insights into latency, cost, error rates, and token usage."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Optional: Specific agent to analyze",
            },
            "time_range": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "format": "date-time"},
                    "end": {"type": "string", "format": "date-time"},
                },
                "description": "Time range for analysis",
            },
            "group_by": {
                "type": "string",
                "enum": ["hour", "day", "agent", "session"],
                "default": "hour",
                "description": "How to group results",
            },
            "metrics": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["latency", "cost", "error_rate", "token_usage"],
                },
                "default": ["latency", "cost", "error_rate", "token_usage"],
            },
        },
    },
)


class AnalyzePerformanceTool(BaseLangfuseTool):
    """Analyze agent performance metrics"""

    async def execute(self, args: Dict[str, Any]) -> str:
        """Execute the analyze_agent_performance tool"""
        try:
            agent_name = args.get("agent_name")
            group_by = args.get("group_by", "hour")
            time_range = args.get("time_range") or {}
            range_start = self._parse_datetime(time_range.get("start"))
            range_end = self._parse_datetime(time_range.get("end"))
            range_start_naive = self._coerce_to_naive_utc(range_start) if range_start else None
            range_end_naive = self._coerce_to_naive_utc(range_end) if range_end else None

            traces = self.langfuse.api.trace.list(limit=100)

            if agent_name:
                traces.data = [
                    t for t in traces.data
                    if t.metadata.get("agent_name") == agent_name
                ]

            if range_start_naive or range_end_naive:
                filtered = []
                for t in traces.data:
                    ts = self._coerce_to_naive_utc(t.timestamp)
                    if range_start_naive and ts < range_start_naive:
                        continue
                    if range_end_naive and ts > range_end_naive:
                        continue
                    filtered.append(t)
                traces.data = filtered

            if not traces.data:
                return "No traces found for analysis"

            total_traces = len(traces.data)
            total_cost = 0
            total_tokens = 0
            latencies = []
            errors = 0
            group_stats: Dict[str, Dict[str, Any]] = {}

            for trace in traces.data:
                metrics = self._calculate_trace_metrics(trace)
                total_cost += metrics.get("cost", 0)
                total_tokens += metrics.get("tokens", 0)
                latencies.append(metrics.get("latency_ms", 0))

                if self._get_trace_status(trace) == "error":
                    errors += 1

                group_key = self._get_group_key(trace, group_by)
                group_entry = group_stats.setdefault(
                    group_key,
                    {"count": 0, "cost": 0.0, "tokens": 0, "latencies": [], "errors": 0},
                )
                group_entry["count"] += 1
                group_entry["cost"] += metrics.get("cost", 0)
                group_entry["tokens"] += metrics.get("tokens", 0)
                group_entry["latencies"].append(metrics.get("latency_ms", 0))
                if self._get_trace_status(trace) == "error":
                    group_entry["errors"] += 1

            avg_latency = sum(latencies) / len(latencies) if latencies else 0
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
            error_rate = errors / total_traces if total_traces > 0 else 0

            time_label = self._format_time_range_label(
                range_start_naive,
                range_end_naive,
                total_traces,
            )

            response = f"""
                        [Performance Analysis]

                        **Agent**: {agent_name or "All Agents"}
                        **Total Runs**: {total_traces}
                        **Time Period**: {time_label}

                        **Metrics Summary**:
                        - Avg Latency: {avg_latency:.0f}ms
                        - P95 Latency: {p95_latency:.0f}ms
                        - Total Cost: ${total_cost:.4f}
                        - Total Tokens: {total_tokens:,}
                        - Error Rate: {error_rate*100:.2f}%
                        - Success Rate: {(1-error_rate)*100:.2f}%

                        **Cost Breakdown**:
                        - Avg per run: ${total_cost/total_traces:.4f}
                        - Projected daily: ${total_cost * 24:.2f} (if sustained)

                        **Grouped by**: {group_by}
                        **Top Groups**:
                        """

            if group_stats:
                sorted_groups = sorted(
                    group_stats.items(),
                    key=lambda x: x[1]["count"],
                    reverse=True,
                )
                for i, (key, data) in enumerate(sorted_groups[:10], 1):
                    avg_lat = (sum(data["latencies"]) / data["count"]) if data["count"] else 0
                    err_rate = (data["errors"] / data["count"] * 100) if data["count"] else 0
                    response += (
                        f"{i}. **{key}**: {data['count']} runs, "
                        f"avg latency {avg_lat:.0f}ms, "
                        f"tokens {data['tokens']:,}, "
                        f"cost ${data['cost']:.4f}, "
                        f"error rate {err_rate:.2f}%"
                    )

            return response

        except Exception as e:
            return f"Error analyzing performance: {str(e)}"
