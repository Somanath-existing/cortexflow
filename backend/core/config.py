from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://cortexflow:cortexflow_dev@localhost:5432/cortexflow"
    neo4j_url: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "cortexflow_dev"
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"
    groq_fast_model: str = "qwen/qwen3.8-27b"

    # MCP Server URLs
    mcp_database_url: str = "http://localhost:8001"
    mcp_knowledge_url: str = "http://localhost:8002"
    mcp_analytics_url: str = "http://localhost:8003"

    # AgentGuard
    agent_budget_tokens: int = 50000

    class Config:
        env_file = ".env"


settings = Settings()
