# 🖥️ Server Mode

AI Cortex can run as a local **OpenAI-compatible HTTP proxy**, letting you connect any OpenAI client — the Python SDK, curl, LangChain, or any third-party tool — to free community Ollama models with zero code changes.

## 📦 Installation

Server mode requires FastAPI and Uvicorn. Install them with the `server` extra:

```bash
pip install aicortex-core[server]
```

## 🚀 Starting the Server

### Python

```python
from aicortex.tools import run_server

# Quickstart — defaults to 127.0.0.1:8000
run_server()

# Custom configuration
run_server(
    host="0.0.0.0",           # Expose on all interfaces
    port=8080,                 # Custom port
    default_model="llama3.2:3b",  # Override default model
    reload=False,              # Disable auto-reload in production
)
```

### Command line

```bash
python -m aicortex.tools.server
```

### Environment variables

You can configure the server without touching Python:

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_MODEL` | `gpt-oss:20b` | Default model when none is specified |
| `HOST` | `127.0.0.1` | Server bind address |
| `PORT` | `8000` | Server port |

```bash
DEFAULT_MODEL=mistral:7b PORT=8080 python -m aicortex.tools.server
```

## 🔌 API Endpoints

### `GET /` — Server info

Returns service metadata and a map of available endpoints.

```json
{
  "service": "AI Cortex OpenAI-Compatible Proxy",
  "version": "1.0.3",
  "default_model": "gpt-oss:20b",
  "endpoints": {
    "models":           "/models",
    "openai_models":    "/v1/models",
    "chat_completions": "/v1/chat/completions",
    "health":           "/health"
  }
}
```

### `GET /health` — Health check

Lightweight liveness probe — returns instantly, no model I/O.

```json
{
  "status": "ok",
  "timestamp": 1746187200.123
}
```

### `GET /config` — Runtime configuration

Inspect what the running server is configured with.

```json
{
  "default_model":    "gpt-oss:20b",
  "host":             "127.0.0.1",
  "port":             8000,
  "available_models": ["llama3.2:3b", "mistral:7b"],
  "model_count":      2
}
```

### `GET /models` — AI Cortex model list

Returns available models in AI Cortex's native format.

```json
{
  "models":        ["llama3.2:3b", "mistral:7b"],
  "default_model": "gpt-oss:20b",
  "total_models":  2
}
```

### `GET /v1/models` — OpenAI-compatible model list

Matches the OpenAI `/v1/models` response schema exactly.

```json
{
  "object": "list",
  "data": [
    {
      "id":       "llama3.2:3b",
      "object":   "model",
      "created":  1640995200,
      "owned_by": "aicortex"
    },
    {
      "id":       "mistral:7b",
      "object":   "model",
      "created":  1640995200,
      "owned_by": "aicortex"
    }
  ]
}
```

### `POST /v1/chat/completions` — Chat completions

The primary endpoint. Accepts the full OpenAI chat completions request body.

**Request:**

```json
{
  "model":       "llama3.2:3b",
  "messages": [
    {"role": "system",    "content": "You are a helpful assistant."},
    {"role": "user",      "content": "Explain quantum entanglement simply."}
  ],
  "stream":      false,
  "temperature": 0.7,
  "max_tokens":  200
}
```

**Response (non-streaming):**

```json
{
  "id":      "chatcmpl-abc123",
  "object":  "chat.completion",
  "created": 1746187200,
  "model":   "llama3.2:3b",
  "choices": [
    {
      "index":   0,
      "message": {
        "role":    "assistant",
        "content": "Quantum entanglement is when two particles become linked..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens":     24,
    "completion_tokens": 61,
    "total_tokens":      85
  }
}
```

**Response (streaming, `"stream": true`):**

The server returns [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) in OpenAI's streaming format. Each event carries a partial delta:

```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"delta":{"content":"Quantum"},"index":0}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"delta":{"content":" entanglement"},"index":0}]}

data: [DONE]
```

## 💡 Client Examples

### curl — non-streaming

```bash
curl -s -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }' | python3 -m json.tool
```

### curl — streaming

```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Count to five."}],
    "stream": true
  }'
```

### OpenAI Python SDK — drop-in replacement

Change only `base_url` and `api_key`. Everything else is identical to normal OpenAI usage:

```python
from openai import OpenAI

client = OpenAI(
    api_key="none",                      # Required by the SDK, not validated
    base_url="http://localhost:8000/v1", # Point to AI Cortex
)

response = client.chat.completions.create(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "What is the Fibonacci sequence?"}],
    temperature=0.5,
    max_tokens=150,
)

print(response.choices[0].message.content)
```

### OpenAI Python SDK — streaming

```python
from openai import OpenAI

client = OpenAI(api_key="none", base_url="http://localhost:8000/v1")

with client.chat.completions.stream(
    model="mistral:7b",
    messages=[{"role": "user", "content": "Write a short poem about the ocean."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### LangChain

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="llama3.2:3b",
    openai_api_key="none",
    openai_api_base="http://localhost:8000/v1",
    temperature=0.7,
)

response = llm.invoke("Explain the CAP theorem.")
print(response.content)
```

## ❌ Error Handling

The server returns standard HTTP status codes with descriptive JSON bodies.

| Status | Meaning |
|---|---|
| `400` | Bad request — missing or invalid parameters |
| `500` | Internal error — model unavailable or server-side failure |

**Example error response:**

```json
{
  "detail": "Model 'gpt-4' not found. Available models: ['llama3.2:3b', 'mistral:7b']"
}
```

## 🏭 Production Deployment

### Expose on the network

```python
run_server(host="0.0.0.0", port=8000, reload=False)
```

### systemd service

```ini
[Unit]
Description=AI Cortex OpenAI-Compatible Proxy
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/aicortex
ExecStart=/opt/aicortex/.venv/bin/python -m aicortex.tools.server
Restart=on-failure
RestartSec=5
Environment=DEFAULT_MODEL=llama3.2:3b
Environment=PORT=8000

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aicortex
sudo systemctl start aicortex
```

### nginx reverse proxy

```nginx
server {
    listen 80;
    server_name ai.example.com;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_buffering    off;       # Required for SSE streaming
        proxy_read_timeout 300s;
    }
}
```

> **Important:** Set `proxy_buffering off` — without it, SSE streaming responses will be buffered and appear to hang.

### Health check integration

The `/health` endpoint is designed for load balancers and uptime monitors:

```bash
# Returns exit code 0 if healthy, 1 if not
curl -sf http://localhost:8000/health > /dev/null && echo "UP" || echo "DOWN"
```
