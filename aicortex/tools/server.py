"""OpenAI-compatible proxy server for AI Cortex.

This module exposes :func:`run_server`, which starts a FastAPI application
that speaks the OpenAI Chat Completions API while routing requests through
the AI Cortex / Ollama backend.  Any OpenAI client library or tool that can
point its ``base_url`` at a local server will work without modification.

Install the optional dependencies before using::

    pip install aicortex-core[server]

Quickstart::

    from aicortex.tools import run_server

    run_server(host="127.0.0.1", port=8000, default_model="llama3.2:3b")

Then from another process::

    # curl
    curl -X POST http://localhost:8000/v1/chat/completions \\
      -H "Content-Type: application/json" \\
      -d '{"model": "llama3.2:3b", "messages": [{"role": "user", "content": "Hello!"}]}'

    # openai-python SDK
    from openai import OpenAI
    client = OpenAI(api_key="none", base_url="http://localhost:8000/v1")
    response = client.chat.completions.create(
        model="llama3.2:3b",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    print(response.choices[0].message.content)

Available endpoints:

=================================  ===============================================
``GET  /``                         Service info and endpoint directory.
``GET  /health``                   Health check; returns ``{"status": "ok"}``.
``GET  /config``                   Running configuration and model count.
``GET  /models``                   Simple model list (AI Cortex format).
``GET  /v1/models``                OpenAI-compatible model list.
``POST /v1/chat/completions``      Chat completions (streaming and non-streaming).
=================================  ===============================================
"""

from __future__ import annotations

import json
import uuid
import time
import os
from typing import Optional, List, Dict, Any, Iterator

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse, JSONResponse
    from pydantic import BaseModel, Field
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    HTTPException = None
    StreamingResponse = None
    JSONResponse = None
    BaseModel = None
    Field = None
    uvicorn = None

from aicortex.chat import chat
from aicortex.api import _OllamaAPI

_client = _OllamaAPI()


class Config:
    """Immutable server configuration container.

    Holds the three values that control how the proxy server starts up.
    An instance is created by :func:`run_server` and passed to
    :func:`create_app`.

    Attributes:
        DEFAULT_MODEL: The model used when the client does not specify one
            in the request body.
        HOST: Bind address for the Uvicorn server.
        PORT: TCP port for the Uvicorn server.
    """

    DEFAULT_MODEL: str
    HOST: str
    PORT: int

    def __init__(self, default_model: str = "gpt-oss:20b", host: str = "127.0.0.1", port: int = 8000):
        """Create a configuration instance.

        Args:
            default_model: Fallback model name when none is provided in a
                request.  Defaults to ``"gpt-oss:20b"``.
            host: IP address to bind to.  Defaults to ``"127.0.0.1"``
                (loopback only).
            port: Port to listen on.  Defaults to ``8000``.
        """
        self.DEFAULT_MODEL = default_model
        self.HOST = host
        self.PORT = port


if FASTAPI_AVAILABLE:
    class Message(BaseModel):
        """A single chat message with a role and text content."""
        role: str
        content: str

    class ChatCompletionRequest(BaseModel):
        """Request body for ``POST /v1/chat/completions``."""
        model: Optional[str] = Field(None, description="Model to use. If not provided, default model will be used.")
        messages: List[Message]
        stream: Optional[bool] = False
        temperature: Optional[float] = 0.7
        max_tokens: Optional[int] = None
        top_p: Optional[float] = 1.0

    class ModelInfo(BaseModel):
        """OpenAI-compatible model descriptor returned by ``GET /v1/models``."""
        id: str
        object: str = "model"
        created: int
        owned_by: str = "aicortex"

    class ModelsListResponse(BaseModel):
        """OpenAI-compatible response wrapper for the model list."""
        object: str = "list"
        data: List[ModelInfo]

    class ModelResponse(BaseModel):
        """Simple model list response returned by ``GET /models``."""
        models: List[str]
        default_model: str
        total_models: int
else:
    # Dummy classes to prevent NameError when FastAPI is not installed
    Message = None
    ChatCompletionRequest = None
    ModelInfo = None
    ModelsListResponse = None
    ModelResponse = None


def generate_sse_chunks(model: str, content_generator: Iterator[str], request_id: str) -> Iterator[str]:
    """Convert a token iterator into OpenAI-compatible Server-Sent Events.

    Yields three kinds of SSE frames in order:

    1. A **role chunk** with ``delta: {"role": "assistant"}`` and no content.
    2. One **content chunk** per token with ``delta: {"content": token}``.
    3. A **final chunk** with ``finish_reason: "stop"`` and an empty delta,
       followed by the ``data: [DONE]`` sentinel.

    All chunks share the same ``id``, ``created`` timestamp, and ``model``
    name for consistent client parsing.

    Args:
        model: The model name included in every SSE chunk.
        content_generator: An iterator yielding token strings in order.
        request_id: A unique identifier string (e.g. ``"chatcmpl-abc123"``)
            included in every chunk.

    Yields:
        SSE-formatted strings suitable for a ``text/event-stream`` response.
    """
    created = int(time.time())

    role_chunk = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(role_chunk)}\n\n"

    for text_piece in content_generator:
        content_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": text_piece}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(content_chunk)}\n\n"

    final_chunk = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    yield "data: [DONE]\n\n"


def generate_non_stream_response(model: str, full_response: str, request_id: str) -> dict:
    """Build a complete OpenAI-compatible non-streaming chat completion response.

    Constructs a ``chat.completion`` object that mirrors the OpenAI API
    response format.  Token usage is approximated by word count (Ollama does
    not return accurate token counts for all models).

    Args:
        model: The model name included in the response object.
        full_response: The complete generated text string.
        request_id: A unique identifier string for the completion object.

    Returns:
        A JSON-serialisable dict matching the ``ChatCompletion`` schema.
    """
    created = int(time.time())
    return {
        "id": request_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": full_response},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": len(full_response.split()),
            "total_tokens": len(full_response.split()),
        },
    }


def create_app(config: Config) -> Any:
    """Construct and configure the FastAPI application instance.

    Registers all route handlers and wires them to the given *config*.  This
    function is called internally by :func:`run_server`; you can also call it
    directly if you need to mount the app within a larger ASGI application.

    Args:
        config: A :class:`Config` instance specifying the default model, host,
            and port.

    Returns:
        A configured :class:`fastapi.FastAPI` application object.

    Raises:
        NameError: If FastAPI is not installed (``FASTAPI_AVAILABLE`` is
            ``False``).  Use :func:`run_server` to get a clean
            :exc:`ImportError` with install instructions.
    """
    app = FastAPI(
        title="AI Cortex OpenAI-Compatible Proxy",
        description=f"Default model: {config.DEFAULT_MODEL}",
        version="1.0.2",
    )

    @app.get("/")
    async def root():
        """Return service info and a directory of available endpoints."""
        return {
            "service": "AI Cortex OpenAI-Compatible Proxy",
            "version": "1.0.2",
            "default_model": config.DEFAULT_MODEL,
            "endpoints": {
                "models": "/models",
                "openai_models": "/v1/models",
                "chat_completions": "/v1/chat/completions",
                "health": "/health",
            },
        }

    @app.get("/models")
    async def list_models_simple():
        """Return a simple list of all available models (AI Cortex format)."""
        try:
            available_models = _client.list_models()
            return ModelResponse(
                models=available_models,
                default_model=config.DEFAULT_MODEL,
                total_models=len(available_models),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch models: {str(e)}")

    @app.get("/v1/models")
    async def list_models_openai():
        """Return the model list in OpenAI ``GET /v1/models`` format."""
        try:
            available_models = _client.list_models()
            created = int(time.time())
            model_list = [
                ModelInfo(id=model_id, created=created, owned_by="aicortex")
                for model_id in available_models
            ]
            return ModelsListResponse(data=model_list)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        """Handle chat completion requests (streaming and non-streaming).

        Accepts the standard OpenAI ``POST /v1/chat/completions`` body.
        Extracts the last ``user`` message as the prompt, validates the
        requested model against the local catalogue, and returns either a
        ``StreamingResponse`` (SSE) or a ``JSONResponse`` depending on
        ``request.stream``.
        """
        request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        model_name = request.model if request.model else config.DEFAULT_MODEL

        try:
            available_models = _client.list_models()
            if model_name not in available_models:
                raise HTTPException(
                    status_code=400,
                    detail=f"Model '{model_name}' not found. Available models: {available_models}",
                )
        except Exception as e:
            print(f"Warning: Could not validate model: {e}")

        user_messages = [m.content for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")
        prompt = user_messages[-1]

        try:
            if request.stream:
                def stream_wrapper():
                    response = chat(
                        prompt,
                        model=model_name,
                        stream=True,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        top_p=request.top_p,
                    )
                    return generate_sse_chunks(
                        model=model_name,
                        content_generator=(event.content for event in response if event.type == "token"),
                        request_id=request_id,
                    )

                return StreamingResponse(
                    stream_wrapper(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                    },
                )
            else:
                response = chat(
                    prompt,
                    model=model_name,
                    stream=False,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    top_p=request.top_p,
                )
                return JSONResponse(
                    content=generate_non_stream_response(
                        model=model_name,
                        full_response=response,
                        request_id=request_id,
                    )
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    async def health_check():
        """Return a simple health status and server timestamp."""
        return {"status": "ok", "timestamp": time.time()}

    @app.get("/config")
    async def get_config():
        """Return the current server configuration and available model count."""
        try:
            available_models = _client.list_models()
        except Exception:
            available_models = []

        return {
            "default_model": config.DEFAULT_MODEL,
            "host": config.HOST,
            "port": config.PORT,
            "available_models": available_models,
            "model_count": len(available_models),
        }

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 8000,
    default_model: str = "gpt-oss:20b",
    reload: bool = True,
) -> None:
    """Start the AI Cortex OpenAI-compatible proxy server.

    Builds a :class:`Config` instance, calls :func:`create_app`, prints a
    startup banner, and hands control to Uvicorn.  The function blocks until
    the server is stopped.

    Args:
        host: Network interface to bind to.  Use ``"0.0.0.0"`` to accept
            connections from any interface (useful inside Docker or VMs).
            Defaults to ``"127.0.0.1"`` (loopback only).
        port: TCP port to listen on.  Defaults to ``8000``.
        default_model: Model name used when a client request omits the
            ``model`` field.  Must be present in the local model catalogue.
            Defaults to ``"gpt-oss:20b"``.
        reload: Enable Uvicorn auto-reload on source changes.  Useful during
            development; set to ``False`` in production.  Defaults to
            ``True``.

    Raises:
        ImportError: If ``fastapi``, ``uvicorn``, or ``pydantic`` are not
            installed.  Install them with::

                pip install aicortex-core[server]

    Example::

        from aicortex.tools import run_server

        # Development server — reloads on code changes
        run_server(host="127.0.0.1", port=8000, default_model="llama3.2:3b")

        # Production — all interfaces, no reload
        run_server(host="0.0.0.0", port=80, default_model="mistral:7b", reload=False)
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI server requires additional dependencies. "
            "Install with: pip install fastapi uvicorn pydantic"
        )

    config = Config(default_model=default_model, host=host, port=port)
    app = create_app(config)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     AI Cortex OpenAI-Compatible Proxy Server                ║
╠══════════════════════════════════════════════════════════════╣
║  Default Model: {config.DEFAULT_MODEL:<42} ║
║  Server URL:    http://{config.HOST}:{config.PORT:<32} ║
╠══════════════════════════════════════════════════════════════╣
║  Endpoints:                                                 ║
║    • GET  /models              - List all available models  ║
║    • GET  /v1/models           - OpenAI format models       ║
║    • POST /v1/chat/completions - Chat completions           ║
║    • GET  /health              - Health check               ║
║    • GET  /config              - Server configuration       ║
╚══════════════════════════════════════════════════════════════╝
    """.strip())

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        reload=reload,
    )


if __name__ == "__main__":
    run_server()
