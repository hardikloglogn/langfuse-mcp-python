"""
Prompts CRUD Tool - Complete Create/Read/Update/Delete operations
GET already exists in prompts.py
"""

from typing import Any, Dict
from mcp.types import Tool
from langfuse.api import (
    CreateChatPromptRequest,
    CreateChatPromptType,
    CreateTextPromptRequest,
)
from ..core.base_tool import BaseLangfuseTool

CREATE_PROMPT_TOOL_SPEC = Tool(
    name="create_prompt",
    description="Create a new prompt or new version of existing prompt.",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Prompt name"},
            "prompt": {
                "description": "Prompt content (string for text, object for chat)",
            },
            "type": {
                "type": "string",
                "enum": ["text", "chat"],
                "default": "text",
                "description": "Prompt type"
            },
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Labels like 'production', 'latest'"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for organization"
            },
            "config": {
                "type": "object",
                "description": "Model configuration (temperature, max_tokens, etc.)"
            },
        },
        "required": ["name", "prompt"],
    },
)

DELETE_PROMPT_TOOL_SPEC = Tool(
    name="delete_prompt",
    description="Delete a specific prompt version or all versions.",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Prompt name"},
            "version": {
                "type": "integer",
                "description": "Specific version to delete (omit to delete all versions)"
            },
        },
        "required": ["name"],
    },
)

class CreatePromptTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            # Langfuse SDK v2 uses CreatePromptRequest structure
            prompt_data = {
                "name": args["name"],
                "prompt": args["prompt"],
                "type": args.get("type", "text"),
            }
            
            if args.get("labels"):
                prompt_data["labels"] = args["labels"]
            
            if args.get("tags"):
                prompt_data["tags"] = args["tags"]
            
            if args.get("config"):
                prompt_data["config"] = args["config"]
            
            # Build request object based on prompt type
            if prompt_data["type"] == "chat":
                if not isinstance(prompt_data["prompt"], list):
                    return "Error creating prompt: for type 'chat', prompt must be a list of messages"
                request = CreateChatPromptRequest(
                    name=prompt_data["name"],
                    prompt=prompt_data["prompt"],
                    labels=prompt_data.get("labels", []),
                    tags=prompt_data.get("tags"),
                    config=prompt_data.get("config", {}),
                    type=CreateChatPromptType.CHAT,
                )
            else:
                if not isinstance(prompt_data["prompt"], str):
                    return "Error creating prompt: for type 'text', prompt must be a string"
                request = CreateTextPromptRequest(
                    name=prompt_data["name"],
                    prompt=prompt_data["prompt"],
                    labels=prompt_data.get("labels", []),
                    tags=prompt_data.get("tags"),
                    config=prompt_data.get("config", {}),
                )
            
            prompt = await self._fetch_with_retry(
                lambda: self.langfuse.api.prompts.create(request=request)
            )
            
            return f"""✅ Prompt created successfully
Name: {prompt.name if hasattr(prompt, 'name') else args['name']}
Version: {prompt.version if hasattr(prompt, 'version') else 'N/A'}
Type: {prompt.type if hasattr(prompt, 'type') else args.get('type', 'text')}
Labels: {', '.join(prompt.labels) if hasattr(prompt, 'labels') and prompt.labels else 'None'}
"""
        except Exception as e:
            self.logger.error("Error creating prompt", error=str(e))
            return f"Error creating prompt: {str(e)}"

class DeletePromptTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            await self._fetch_with_retry(
                self.langfuse.api.prompts.delete,
                prompt_name=args["name"],
                version=args.get("version"),
            )
            
            msg = f"Prompt '{args['name']}'"
            if args.get("version"):
                msg += f" version {args['version']}"
            else:
                msg += " (all versions)"
            
            return f"✅ {msg} deleted successfully"
        except Exception as e:
            return f"Error deleting prompt: {str(e)}"
