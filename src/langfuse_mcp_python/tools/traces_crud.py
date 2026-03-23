"""
Traces CRUD Tool - Complete Create/Read/Update/Delete operations
"""

from typing import Any, Dict
from mcp.types import Tool
from ..core.base_tool import BaseLangfuseTool

# GET already exists in get_trace.py, adding UPDATE and DELETE

UPDATE_TRACE_TOOL_SPEC = Tool(
    name="update_trace",
    description="Update trace metadata, tags, or other properties.",
    inputSchema={
        "type": "object",
        "properties": {
            "trace_id": {"type": "string", "description": "Trace ID to update"},
            "name": {"type": "string", "description": "Update trace name"},
            "user_id": {"type": "string", "description": "Update user ID"},
            "session_id": {"type": "string", "description": "Update session ID"},
            "metadata": {"type": "object", "description": "Update metadata (merges with existing)"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Update tags"},
            "public": {"type": "boolean", "description": "Make trace public/private"},
            "release": {"type": "string", "description": "Release/version identifier"},
        },
        "required": ["trace_id"],
    },
)

DELETE_TRACE_TOOL_SPEC = Tool(
    name="delete_trace",
    description="Delete a trace and all its associated observations.",
    inputSchema={
        "type": "object",
        "properties": {
            "trace_id": {"type": "string", "description": "Trace ID to delete"},
        },
        "required": ["trace_id"],
    },
)

class UpdateTraceTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            trace_id = args.pop("trace_id")
            
            # Build update payload
            update_data = {}
            if args.get("name"):
                update_data["name"] = args["name"]
            if args.get("user_id"):
                update_data["user_id"] = args["user_id"]
            if args.get("session_id"):
                update_data["session_id"] = args["session_id"]
            if args.get("metadata"):
                update_data["metadata"] = args["metadata"]
            if args.get("tags"):
                update_data["tags"] = args["tags"]
            if "public" in args:
                update_data["public"] = args["public"]
            if args.get("release"):
                update_data["release"] = args["release"]
            
            # Update trace
            trace = await self._fetch_with_retry(
                self.langfuse.api.trace.update,
                trace_id=trace_id,
                **update_data
            )
            
            # Invalidate cache for this trace
            cache_key = self.cache.make_key("trace", trace_id)
            self.cache.invalidate(cache_key)
            
            return f"[OK] Trace updated successfully\nID: {trace.id}\nName: {trace.name}"
        except Exception as e:
            return f"Error updating trace: {str(e)}"

class DeleteTraceTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            trace_id = args["trace_id"]
            
            # Delete trace
            result = await self._fetch_with_retry(
                self.langfuse.api.trace.delete,
                trace_id=trace_id
            )
            
            # Invalidate cache
            self.cache.invalidate("trace")
            
            return f"[OK] Trace deleted successfully\nID: {trace_id}"
        except Exception as e:
            return f"Error deleting trace: {str(e)}"
