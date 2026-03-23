"""
Comments CRUD - Update/Delete operations (GET/POST already in comments.py)
"""

from typing import Any, Dict
from mcp.types import Tool
from ..core.base_tool import BaseLangfuseTool

UPDATE_COMMENT_TOOL_SPEC = Tool(
    name="update_comment",
    description="Update an existing comment.",
    inputSchema={
        "type": "object",
        "properties": {
            "comment_id": {"type": "string", "description": "Comment ID to update"},
            "content": {"type": "string", "description": "New comment content"},
        },
        "required": ["comment_id", "content"],
    },
)

DELETE_COMMENT_TOOL_SPEC = Tool(
    name="delete_comment",
    description="Delete a comment.",
    inputSchema={
        "type": "object",
        "properties": {
            "comment_id": {"type": "string", "description": "Comment ID to delete"},
        },
        "required": ["comment_id"],
    },
)

class UpdateCommentTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            comment = await self._fetch_with_retry(
                self.langfuse.api.comments.update,
                comment_id=args["comment_id"],
                content=args["content"],
            )
            return f"[OK] Comment updated\nID: {comment.id}"
        except Exception as e:
            return f"Error updating comment: {str(e)}"

class DeleteCommentTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            await self._fetch_with_retry(
                self.langfuse.api.comments.delete,
                comment_id=args["comment_id"],
            )
            return f"[OK] Comment deleted: {args['comment_id']}"
        except Exception as e:
            return f"Error deleting comment: {str(e)}"
