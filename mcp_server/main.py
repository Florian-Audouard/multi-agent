from fastmcp import FastMCP
import uvicorn


# Create FastMCP server
mcp = FastMCP("mock_server")

@mcp.tool(annotations={"destructiveHint": True})
def get_weather(location: str) -> str:
    """Mock weather tool that returns the weather for a given location."""
    return f"The weather in {location} is 72F and sunny."

@mcp.tool()
def get_stock_price(ticker: str) -> str:
    """Mock stock price tool."""
    return f"The current price of {ticker} is $150.00."

app = mcp.http_app()

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
