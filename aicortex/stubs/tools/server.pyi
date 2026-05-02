from typing import Any

class Config:
    """Server configuration."""
    DEFAULT_MODEL: str
    HOST: str
    PORT: int

    def __init__(self, default_model: str = "gpt-oss:20b", host: str = "127.0.0.1", port: int = 8000) -> None:
        ...

def generate_sse_chunks(model: str, content_generator, request_id: str) -> Any:
    """Convert stream to OpenAI-compatible SSE format."""
    ...

def generate_non_stream_response(model: str, full_response: str, request_id: str) -> dict:
    """Generate standard OpenAI non-streaming response."""
    ...

def create_app(config: Config) -> Any:
    """Create and configure the FastAPI application."""
    ...

def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    default_model: str = "gpt-oss:20b",
    reload: bool = True,
) -> None:
    """Run the AI Cortex OpenAI-compatible proxy server.

    Args:
        host: Host to bind the server to.
        port: Port to bind the server to.
        default_model: Default model to use when not specified.
        reload: Whether to enable auto-reload for development.

    Raises:
        ImportError: If required dependencies (fastapi, uvicorn, pydantic) are not installed.
    """
    ...