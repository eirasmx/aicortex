# ⚡ Quick Start

Get your first AI response in under 5 minutes.

## Step 1 — Install

```bash
pip install aicortex-core
```

## Step 2 — Your First Chat

```python
from aicortex import chat

response = chat("What is quantum computing?")
print(response)
```

**That's it.** No API key. No config file. No server setup required.

AI Cortex automatically selects a model and routes your request to an available Ollama server from its bundled endpoint registry.

## Step 3 — Pick a Model

AI Cortex comes pre-loaded with metadata for hundreds of models across five families.
You can specify exactly which one you want:

```python
from aicortex import chat, families, models

# See what model families are available
print(families())
# → ['llama', 'mistral', 'gemma', 'deepseek', 'qwen']

# List all models in a family
print(models("mistral"))
# → ['mistral:7b', 'mistral:instruct', ...]

# Chat with a specific model
response = chat(
    "Explain transformer architecture in plain English.",
    model="mistral:7b",
    temperature=0.6,
    max_tokens=300,
)
print(response)
```

## Step 4 — Stream Responses in Real Time

Streaming gives you token-by-token output as the model generates — perfect for chatbots and interactive UIs:

```python
from aicortex import chat

stream = chat("Write a short poem about the ocean.", stream=True)

for event in stream:
    if event.type == "start":
        print("🟢 Generating...\n")
    elif event.type == "token":
        print(event.content, end="", flush=True)
    elif event.type == "end":
        print("\n\n✅ Done!")
```

> **💡 Tip:** Use `stream.text()` to get the full concatenated response after iterating:
> ```python
> full_text = stream.text()
> ```

## Step 5 — Explore Model Metadata

```python
from aicortex import get_model_info, list_model_servers, get_server_info

# Full metadata for a model (size, family, quantization, etc.)
info = get_model_info("llama3.2:3b")
print(info)

# See all Ollama servers hosting a specific model
servers = list_model_servers("llama3.2:3b")
for s in servers:
    print(f"  {s['url']}  —  {s['location']['city']}, {s['location']['country']}")

# Get connection params for use with LangChain's OllamaLLM
from aicortex import get_llm_params
params = get_llm_params("llama3.2:3b")
print(params)  # {'model': 'llama3.2:3b', 'base_url': 'http://...'}
```

## Step 6 — Run the OpenAI-Compatible Server (Optional)

Turn AI Cortex into an OpenAI-compatible REST API with one call:

```bash
pip install aicortex-core[server]
```

```python
from aicortex.tools import run_server

run_server(host="127.0.0.1", port=8000, default_model="llama3.2:3b")
```

Then use it with `curl`, the `openai` Python SDK, or any OpenAI-compatible tool:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2:3b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Summary: What You Just Learned

| Task | How |
|---|---|
| Simple chat | `chat("your prompt")` |
| Specific model | `chat("...", model="mistral:7b")` |
| Streaming | `chat("...", stream=True)` |
| List models | `models()` / `models("llama")` |
| Model info | `get_model_info("model:tag")` |
| Server mode | `run_server(port=8000)` |

## Where to Go Next

- 📖 [Basic Usage](usage.md) — all parameters, error handling, and advanced patterns
- 🔀 [Streaming](streaming.md) — deep dive into `StreamEvent` types and real-time patterns
- 🤖 [Model Management](models.md) — how the model registry works
- 🖥️ [Server Mode](server.md) — full OpenAI-compatible proxy docs
- 🔧 [Tools](tools.md) — update the model database with live endpoint scanning
