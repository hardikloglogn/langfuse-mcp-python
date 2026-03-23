"""
Datasets Tool - Manage Datasets and Experiments
Critical for evaluation and experimentation
"""

from typing import Any, Dict
from mcp.types import Tool
from ..core.base_tool import BaseLangfuseTool

DATASETS_TOOL_SPEC = Tool(
    name="get_datasets",
    description="Retrieve datasets and dataset items for experiments and evaluations.",
    inputSchema={
        "type": "object",
        "properties": {
            "dataset_name": {"type": "string"},
            "include_items": {"type": "boolean", "default": False},
            "include_runs": {"type": "boolean", "default": False},
        },
    },
)

class GetDatasetsTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            if args.get("dataset_name"):
                dataset = await self._fetch_with_retry(
                    self.langfuse.api.datasets.get,
                    dataset_name=args["dataset_name"],
                )
                response = f"[METRICS] **Dataset: {dataset.name}**\n\n"
                
                if args.get("include_items"):
                    items = await self._fetch_with_retry(
                        self.langfuse.api.dataset_items.list,
                        dataset_name=args["dataset_name"],
                    )
                    response += f"**Items:** {len(items.data)}\n"
                
            if args.get("include_runs"):
                runs = await self._fetch_with_retry(
                    self.langfuse.api.datasets.get_runs,
                    dataset_name=args["dataset_name"],
                )
                response += f"**Runs:** {len(runs.data)}\n"
                
                return response
            else:
                datasets = await self._fetch_with_retry(
                    self.langfuse.api.datasets.list,
                    page=1,
                    limit=50,
                )
                response = f"[METRICS] **Datasets** ({len(datasets.data)} found):\n\n"
                for i, ds in enumerate(datasets.data, 1):
                    response += f"{i}. {ds.name}\n"
                return response
        except Exception as e:
            return f"Error fetching datasets: {str(e)}"
