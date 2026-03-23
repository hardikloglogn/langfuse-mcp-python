"""
Prompts Tool - Manage and Version Prompts
Critical for prompt management and A/B testing
"""

import urllib.parse
from typing import Any, Dict
from mcp.types import Tool
from ..core.base_tool import BaseLangfuseTool

PROMPTS_TOOL_SPEC = Tool(
    name="get_prompts",
    description=(
        "Retrieve and manage prompts from Langfuse. "
        "Track prompt versions, compare performance, and link prompts to traces."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Specific prompt name to retrieve (use '*' to list all)",
            },
            "version": {
                "type": "integer",
                "description": "Specific version number (use with name)",
            },
            "label": {
                "type": "string",
                "description": "Label filter (e.g., 'production', 'latest')",
            },
            "tag": {
                "type": "string",
                "description": "Tag filter",
            },
            "resolve": {
                "type": "boolean",
                "description": "Resolve prompt dependencies (default true in API)",
            },
            "limit": {
                "type": "integer",
                "default": 50,
            },
        },
    },
)

class GetPromptsTool(BaseLangfuseTool):
    async def execute(self, args: Dict[str, Any]) -> str:
        try:
            name = args.get("name")
            if name and name not in ("*", "all"):
                prompt_name = name
                if "/" in prompt_name:
                    prompt_name = urllib.parse.quote(prompt_name, safe="")
                # Get specific prompt
                prompt = await self._fetch_with_retry(
                    self.langfuse.api.prompts.get,
                    prompt_name=prompt_name,
                    version=args.get("version"),
                    label=args.get("label"),
                    resolve=args.get("resolve"),
                )
                return self._format_single_prompt(prompt)
            else:
                # List prompts
                prompts = await self._fetch_with_retry(
                    self.langfuse.api.prompts.list,
                    page=1,
                    limit=args.get("limit", 50),
                    name=None,
                    label=args.get("label"),
                    tag=args.get("tag"),
                )
                return self._format_prompts_list(prompts.data)
        except Exception as e:
            return f"Error fetching prompts: {str(e)}"
    
    def _format_single_prompt(self, prompt) -> str:
        response = f"[NOTE] **Prompt: {prompt.name}**\n\n"
        response += f"  - Version: {prompt.version}\n"
        if hasattr(prompt, 'label') and prompt.label:
            response += f"  - Label: {prompt.label}\n"
        response += f"  - Type: {prompt.type}\n"
        if hasattr(prompt, 'prompt') and prompt.prompt:
            response += f"\n**Content:**\n{prompt.prompt}\n"
        return response
    
    def _format_prompts_list(self, prompts) -> str:
        response = f"[NOTE] **Prompts** ({len(prompts)} found):\n\n"
        for i, prompt in enumerate(prompts[:20], 1):
            response += f"{i}. **{prompt.name}**\n"
            if hasattr(prompt, "type") and prompt.type:
                response += f"   - Type: {prompt.type}\n"
            if hasattr(prompt, "versions") and prompt.versions:
                latest = max(prompt.versions) if prompt.versions else "N/A"
                response += f"   - Versions: {len(prompt.versions)} (latest v{latest})\n"
            if hasattr(prompt, "labels") and prompt.labels:
                response += f"   - Labels: {', '.join(prompt.labels)}\n"
            if hasattr(prompt, "tags") and prompt.tags:
                response += f"   - Tags: {', '.join(prompt.tags)}\n"
        return response
