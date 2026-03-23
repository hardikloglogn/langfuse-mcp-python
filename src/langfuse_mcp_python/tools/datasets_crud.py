"""
Datasets CRUD Tool - Complete Create/Read/Update/Delete operations
"""

from typing import Any, Dict
from mcp.types import Tool
from ..core.base_tool import BaseLangfuseTool

CREATE_DATASET_TOOL_SPEC = Tool(
    name="create_dataset",
    description="Create a new dataset for experiments and evaluations.",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Dataset name"},
            "description": {"type": "string", "description": "Dataset description"},
            "metadata": {"type": "object", "description": "Additional metadata"},
        },
        "required": ["name"],
    },
)

UPDATE_DATASET_TOOL_SPEC = Tool(
    name="update_dataset",
    description="Update dataset properties.",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Dataset name"},
            "description": {"type": "string", "description": "New description"},
            "metadata": {"type": "object", "description": "Updated metadata"},
        },
        "required": ["name"],
    },
)

DELETE_DATASET_TOOL_SPEC = Tool(
    name="delete_dataset",
    description="Delete a dataset and all its items.",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Dataset name to delete"},
        },
        "required": ["name"],
    },
)

CREATE_DATASET_ITEM_TOOL_SPEC = Tool(
    name="create_dataset_item",
    description="Add an item to a dataset.",
    inputSchema={
        "type": "object",
        "properties": {
            "dataset_name": {"type": "string", "description": "Dataset name"},
            "input": {"description": "Input data for this item"},
            "expected_output": {"description": "Expected output for evaluation"},
            "metadata": {"type": "object", "description": "Item metadata"},
        },
        "required": ["dataset_name", "input"],
    },
)

class CreateDatasetTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            dataset = await self._fetch_with_retry(
                self.langfuse.api.datasets.create,
                name=args["name"],
                description=args.get("description"),
                metadata=args.get("metadata"),
            )
            return f"[OK] Dataset created: {dataset.name}"
        except Exception as e:
            return f"Error creating dataset: {str(e)}"

class UpdateDatasetTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            dataset = await self._fetch_with_retry(
                self.langfuse.api.datasets.update,
                name=args["name"],
                description=args.get("description"),
                metadata=args.get("metadata"),
            )
            return f"[OK] Dataset updated: {dataset.name}"
        except Exception as e:
            return f"Error updating dataset: {str(e)}"

class DeleteDatasetTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            await self._fetch_with_retry(
                self.langfuse.api.datasets.delete,
                name=args["name"],
            )
            return f"[OK] Dataset deleted: {args['name']}"
        except Exception as e:
            return f"Error deleting dataset: {str(e)}"

class CreateDatasetItemTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            item = await self._fetch_with_retry(
                self.langfuse.api.dataset_items.create,
                dataset_name=args["dataset_name"],
                input=args["input"],
                expected_output=args.get("expected_output"),
                metadata=args.get("metadata"),
            )
            return f"[OK] Dataset item created\nDataset: {args['dataset_name']}\nItem ID: {item.id}"
        except Exception as e:
            return f"Error creating dataset item: {str(e)}"
