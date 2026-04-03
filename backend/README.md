# Backend: FastAPI & LangChain Agent

This project provides a FastAPI backend that orchestrates an agent using [LangChain](https://github.com/langchain-ai/langchain) and [LangGraph](https://github.com/langchain-ai/langgraph). It integrates with an MCP server to provide the agent with custom tools.

## Tech Stack

- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Orchestration**: [LangGraph](https://python.langchain.com/docs/langgraph)
- **Agent Framework**: [LangChain](https://python.langchain.com/docs/get_started/introduction)
- **Tool Integration**: [MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- **Dependency Management**: [uv](https://github.com/astral-sh/uv)

## Configuration

The backend requires an `.env` file with the following variables:

```env
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
# Other configuration
```

## Running the Server

Using `uv` (recommended):

```bash
uv run uvicorn main:app --reload
```

## Features

- **Streaming Responses**: Asynchronous token-by-token streaming from the LLM.
- **Tool Calling**: Automated tool selection and execution by the agent.
- **MCP Client**: Seamless connection to external MCP servers to expand agent capabilities.
- **Human-In-The-Loop**: Middleware to intercept and approve sensitive tool calls (under development).
