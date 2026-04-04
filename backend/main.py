import asyncio
import json
from contextlib import asynccontextmanager
import re
from typing import AsyncGenerator, Annotated

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import HumanInTheLoopMiddleware
from typing import Optional, Dict, Any
from typing_extensions import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

memory = InMemorySaver()

from config import settings
from middleware.history import HistoryMiddleware
from middleware.logging import AgentLoggingMiddleware


# Define agent state schema with tool_history
import operator

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    tool_history: Annotated[list[str], operator.add]

# Initialize MCP Client
client = MultiServerMCPClient({
    "mock_server": {
        "transport": "streamable_http",
        "url": settings.mcp_server_url,
    }
})

agent = None
agent_init_lock = asyncio.Lock()


async def init_agent(force_refresh: bool = False):
    global agent

    if agent is not None and not force_refresh:
        return agent

    async with agent_init_lock:
        if agent is not None and not force_refresh:
            return agent

        tools = await client.get_tools()

        interrupt_on = {}
        for tool in tools:
            # Check MCP annotations for destructive tools.
            if tool.metadata.get("destructiveHint") is True:
                interrupt_on[tool.name] = {
                    "allowed_decisions": ["approve", "edit", "reject"]
                }

        hitl_middleware = HumanInTheLoopMiddleware(
            interrupt_on=interrupt_on,
            description_prefix="Tool execution pending approval"
        )

        agent = create_agent(
            llm,
            tools,
            state_schema=AgentState,
            middleware=[HistoryMiddleware(), AgentLoggingMiddleware(), hitl_middleware],
            checkpointer=memory,
        )
        return agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup MCP Client and connect
    await init_agent()
    yield

app = FastAPI(lifespan=lifespan)

# Add CORS Middleware to allow React frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For simplicity; configure to standard frontend URL in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: Optional[str] = None
    thread_id: str
    resume: Optional[Dict[str, Any]] = None

llm = init_chat_model(
    model=settings.model,
    model_provider="openai",
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.api_key,
    max_retries=10,
    timeout=120,
)

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    global agent
    
    # Use the same agent instance initialized in lifespan
    if agent is None:
        raise RuntimeError("Agent not initialized. Check app startup.")
    
    current_agent = agent

    async def generate_response() -> AsyncGenerator[str, None]:
        from langchain_core.messages import AIMessageChunk, ToolMessage, AIMessage
        from langgraph.types import Command

        if req.resume:
            initial_input = Command(resume=req.resume)
        else:
            initial_input = {"messages": [{"role": "user", "content": req.message}]}
        print(f'current thread : {req.thread_id}')
        config = {"configurable": {"thread_id": req.thread_id}}
        
        full_message = None
        interrupted = False
        
        async for chunk in current_agent.astream(
            initial_input,
            config=config,
            stream_mode=["messages", "updates"],
            version="v2"
        ):
            if chunk["type"] == "messages":
                token, metadata = chunk["data"]
                if isinstance(token, AIMessageChunk):
                    # Stream tokens
                    if isinstance(token.content, str) and token.content:
                        yield json.dumps({"type": "token", "content": token.content}) + "\n"
                    elif isinstance(token.content, list):
                        for block in token.content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                yield json.dumps({"type": "token", "content": block.get("text", "")}) + "\n"
                    
                    full_message = token if full_message is None else full_message + token
                    if hasattr(token, "chunk_position") and token.chunk_position == "last":
                        if full_message.tool_calls:
                            for tc in full_message.tool_calls:
                                print( json.dumps({"type": "tool_start", "name": tc["name"], "input": tc.get("args", {})}) + "\n")
                                yield json.dumps({"type": "tool_start", "name": tc["name"], "input": tc.get("args", {})}) + "\n"
                        full_message = None

            elif chunk["type"] == "updates":
                if "__interrupt__" in chunk["data"]:
                    interrupt_info = chunk["data"]["__interrupt__"][0].value
                    
                    tool_name = "unknown"
                    if isinstance(interrupt_info, dict) and "action_requests" in interrupt_info:
                        reqs = interrupt_info.get("action_requests", [])
                        if reqs:
                            tool_name = reqs[0].get("name", "unknown")
                    else:
                        # Fallback for string or generic objects
                        tool_name = str(interrupt_info)
                        
                    yield json.dumps({"type": "interrupt", "tool_name": tool_name}) + "\n"
                    interrupted = True
                    break
                    
                for source, update in chunk["data"].items():
                    if update is not None and isinstance(update, dict) and "messages" in update:
                        msg = update["messages"][-1]
                        if isinstance(msg, ToolMessage):
                            content = msg.content
                            yield json.dumps({"type": "tool_end", "name": msg.name, "output": content}) + "\n"

        # If not interrupted (final answer), fetch and yield tool history from state
        if not interrupted:
            try:
                state_snapshot = current_agent.get_state(config)
                if state_snapshot:
                    state_values = state_snapshot.values if hasattr(state_snapshot, 'values') else state_snapshot
                    if isinstance(state_values, dict):
                        print(f"[DEBUG] Full state keys: {list(state_values.keys())}")
                        tool_history = state_values.get("tool_history", [])
                        if tool_history:
                            print(f"Yielding tool history for thread {req.thread_id}: {tool_history}")
                            yield json.dumps({"type": "history", "tools": tool_history}) + "\n"
                        else:
                            print(f"Tool history is empty for thread {req.thread_id}")
                    else:
                        print(f"State is not a dict: {type(state_values)}")
            except Exception as e:
                print(f"Error fetching tool history: {e}")
                import traceback
                traceback.print_exc()

    return StreamingResponse(generate_response(), media_type="application/x-ndjson")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)