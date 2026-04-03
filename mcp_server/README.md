# MCP Server: FastMCP Custom Tools

This Model Context Protocol (MCP) server provides custom tools for use by any LLM-powered agent.

## Tech Stack

- **MCP Library**: [FastMCP](https://github.com/jlowin/fastmcp)
- **Runtime**: [uv](https://github.com/astral-sh/uv)

## Running the Server

Using `uv` (recommended):

```bash
uv run python main.py
```

## Tools Provided

The server currently exposes the following tools:

- `get_user_info`: Fetch mock user info.
- `search_knowledge_base`: Dummy search across knowledge base.

## Features

- **Standard MCP Compliance**: Compatible with MCP-capable clients like Claude and other agent frameworks.
- **Easy Extension**: Built with FastMCP for a simple decorator-based tool definition.
