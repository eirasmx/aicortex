# 🖥️ Server Examples

> **Annotated examples for the OpenAI-compatible server** — startup, configuration,
> curl verification, drop-in OpenAI SDK usage, and reverse proxy setup.

See the [Server Guide](../server.md) for the full endpoint reference and configuration options.

## Starting the Server

### One-liner (CLI)

```bash
aicortex-server
```

The server starts on `http://localhost:8000` with default settings and prints a startup banner:

```
🧠 AI Cortex Server
   OpenAI-compatible API at http://localhost:8000/v1
   Default model: llama3.2:3b
   Press Ctrl+C to stop
```

### Custom Host and Port

```bash
aicortex-server --host 0.0.0.0 --port 11435 --model mistral:7b
```

| Flag | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | Interface to bind — use `0.0.0.0` to accept external connections |
| `--port` | `8000` | TCP port |
| `--model` | `llama3.2:3b` | Default model when none is specified in a request |
| `--reload` | off | Auto-restart on code changes — development only |

### From Python

```python
from aicortex.tools import run_server

run_server(
    host="127.0.0.1",
    port=8000,
    default_model="llama3.2:3b",
)
```

## Verifying the Server with curl

### Health Check

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok", "version": "1.0.3"}
```

### List Models

```bash
curl http://localhost:8000/v1/models | python3 -m json.tool
```

```json
{
  "object": "list",
  "data": [
    {"id": "llama3.2:3b",  "object": "model", "owned_by": "ollama"},
    {"id": "mistral:7b",   "object": "model", "owned_by": "ollama"},
    {"id": "deepseek:6.7b","object": "model", "owned_by": "ollama"}
  ]
}
```

### Chat Completion (Non-Streaming)

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [
      {"role": "user", "content": "What is 2 + 2?"}
    ]
  }' | python3 -m json.tool
```

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "model": "llama3.2:3b",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "2 + 2 equals 4."},
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 8,
    "total_tokens": 20
  }
}
```

### Chat Completion (Streaming)

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Count to five."}],
    "stream": true
  }'
```

The response is a stream of `data: {...}` lines in Server-Sent Events format,
matching the OpenAI streaming protocol exactly.

## Using the OpenAI Python SDK

AI Cortex's server is a drop-in replacement for the OpenAI API. Point the SDK
at `http://localhost:8000/v1` and pass any non-empty string as the API key:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-used",  # required by the SDK but ignored by AI Cortex
)

# Non-streaming
response = client.chat.completions.create(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "Explain gravity briefly."}],
)
print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model="mistral:7b",
    messages=[{"role": "user", "content": "Tell me a joke."}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
print()
```

### Multi-Turn with the OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-used")
history = [{"role": "system", "content": "You are a concise assistant."}]

while True:
    user_input = input("You: ").strip()
    if not user_input:
        break

    history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="llama3.2:3b",
        messages=history,
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    print(f"Assistant: {reply}\n")
```

## Using LangChain

```python
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-used",
    model="llama3.2:3b",
    temperature=0.7,
)

messages = [
    SystemMessage(content="You are a helpful coding assistant."),
    HumanMessage(content="What's the difference between a list and a tuple in Python?"),
]

response = llm.invoke(messages)
print(response.content)
```

## Using LiteLLM

[LiteLLM](https://github.com/BerriAI/litellm) can route to any OpenAI-compatible endpoint:

```python
import litellm

response = litellm.completion(
    model="openai/llama3.2:3b",    # "openai/" prefix routes to custom base_url
    messages=[{"role": "user", "content": "Hello!"}],
    api_base="http://localhost:8000/v1",
    api_key="not-used",
)
print(response.choices[0].message.content)
```

## Production Setup with a Reverse Proxy

For production deployments, run a reverse proxy in front of the AI Cortex server
to add TLS, authentication, and rate limiting.

### nginx Configuration

```nginx
# /etc/nginx/sites-available/aicortex
server {
    listen 443 ssl;
    server_name ai.example.com;

    ssl_certificate     /etc/letsencrypt/live/ai.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.example.com/privkey.pem;

    # Basic authentication
    auth_basic           "AI Cortex API";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location /v1/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_buffering    off;          # required for streaming SSE
        proxy_read_timeout 300s;         # allow long generations
    }
}
```

> **`proxy_buffering off` is required for streaming** — without it, nginx buffers
> the SSE response and clients see no tokens until the response completes.

### Starting as a systemd Service

```ini
# /etc/systemd/system/aicortex.service
[Unit]
Description=AI Cortex Server
After=network.target

[Service]
Type=simple
User=aicortex
ExecStart=/usr/local/bin/aicortex-server --host 127.0.0.1 --port 8000 --model llama3.2:3b
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable aicortex
sudo systemctl start aicortex
sudo systemctl status aicortex
```

## See Also

- [Server Guide](../server.md) — full endpoint reference and all configuration options
- [Chat Examples](chat.md) — using AI Cortex directly without the server
- [Streaming Examples](streaming.md) — streaming via the Python library
