from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    api_key: str = "your-openrouter-key"
    mcp_server_url: str = "http://localhost:8001/mcp/sse"
    model: str = "anthropic/claude-3-5-sonnet"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', case_sensitive=False)

settings = Settings()
