"""
Models Tool - Get Model Configurations and Pricing
Critical for accurate cost calculation
"""

from typing import Any, Dict
from mcp.types import Tool
from ..core.base_tool import BaseLangfuseTool

MODELS_TOOL_SPEC = Tool(
    name="get_models",
    description="Retrieve model configurations and pricing information.",
    inputSchema={
        "type": "object",
        "properties": {
            "model_id": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
        },
    },
)

class GetModelsTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            if args.get("model_id"):
                model = await self._fetch_with_retry(
                    self.langfuse.api.models.get,
                    id=args["model_id"],
                )
                return self._format_model(model)
            else:
                models = await self._fetch_with_retry(
                    self.langfuse.api.models.list,
                    page=1,
                    limit=args.get("limit", 50),
                )
                return self._format_models_list(models.data)
        except Exception as e:
            return f"Error fetching models: {str(e)}"
    
    def _format_model(self, model) -> str:
        response = f"[AGENT] **Model: {model.model_name}**\n\n"
        if hasattr(model, 'input_price'):
            response += f"  - Input Price: ${model.input_price}/1M tokens\n"
        if hasattr(model, 'output_price'):
            response += f"  - Output Price: ${model.output_price}/1M tokens\n"
        return response
    
    def _format_models_list(self, models) -> str:
        response = f"[AGENT] **Models** ({len(models)} found):\n\n"
        for model in models[:30]:
            response += f"  - {model.model_name}\n"
        return response
