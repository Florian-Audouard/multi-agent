from typing import Any, Awaitable, Callable

from langchain.agents.middleware import AgentMiddleware
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command


class HistoryMiddleware(AgentMiddleware):
    """Track tool usage cleanly and statelessly via LangGraph state."""

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        tool_name = request.tool_call.get("name", "unknown_tool")
        
        # Execute the tool via the next middleware/handler
        result = handler(request)
        
        # The result might be a Command if another middleware returned it, but usually it's ToolMessage.
        # Ensure we wrap the final result into a Command that appends to tool_history.
        if isinstance(result, Command):
            update = result.update or {}
            update["tool_history"] = [tool_name]
            return Command(
                update=update,
                resume=result.resume,
                goto=result.goto
            )
            
        return Command(
            update={
                "tool_history": [tool_name],
                "messages": [result]
            }
        )

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        tool_name = request.tool_call.get("name", "unknown_tool")
        
        # Execute the tool
        result = await handler(request)
        
        if isinstance(result, Command):
            update = result.update or {}
            update["tool_history"] = [tool_name]
            return Command(
                update=update,
                resume=result.resume,
                goto=result.goto
            )

        return Command(
            update={
                "tool_history": [tool_name],
                "messages": [result]
            }
        )