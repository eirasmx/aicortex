# 📖 Basic Usage

This guide covers every parameter of the `chat()` function, common usage patterns,
error handling, and the model/server discovery API.

## Importing AI Cortex

```python
# Core chat function — this is all most users need
from aicortex import chat

# Model discovery
from aicortex import families, models, get_model_info

# Server discovery
from aicortex import list_model_servers, get_server_info

# LangChain / OllamaLLM integration helpers
from aicortex import get_llm_params, get_random_llm_params

# Low-level request builder (advanced)
from aicortex import build_api_request
```

## The `chat()` Function

`chat()` is the main entry point. It handles model resolution, server selection,
automatic failover, and both synchronous and streaming modes.

### Signature

```python
def chat(
    prompt: str,
    *,
    model: str = "gpt-oss:20b",
    stream: bool = False,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    top_p: float = 1.0,
    stop: list[str] | None = None,
) -> str | Stream:
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `prompt` | `str` | *(required)* | The input text sent to the model |
| `model` | `str` | `"gpt-oss:20b"` | Model name (must exist in the registry) |
| `stream` | `bool` | `False` | Return a `Stream` object instead of a string |
| `temperature` | `float` | `0.7` | Creativity/randomness. `0.0` = deterministic, `1.0+` = more creative |
| `max_tokens` | `int \| None` | `None` | Maximum tokens to generate. `None` uses server default |
| `top_p` | `float` | `1.0` | Nucleus sampling cutoff. Lower values restrict vocabulary |
| `stop` | `list[str] \| None` | `None` | Stop generating when any of these strings are produced |

### Return Values

- **`stream=False`** → returns `str` — the full generated response text
- **`stream=True`** → returns `Stream` — an iterable of `StreamEvent` objects

## Usage Patterns

### Simple Synchronous Chat

```python
from aicortex import chat

response = chat("Summarise the French Revolution in three bullet points.")
print(response)
```

### Choosing a Model

```python
response = chat(
    "Write a Python decorator that logs function calls.",
    model="llama3.2:3b",
)
print(response)
```

> **💡 Tip:** Use `models()` to see what's available, or `models("llama")` to filter by family.

### Controlling Output Quality

```python
# More deterministic — good for factual Q&A, code
response = chat(
    "What is the boiling point of water at sea level?",
    model="mistral:7b",
    temperature=0.1,
    top_p=0.9,
)

# More creative — good for brainstorming, fiction
response = chat(
    "Give me 5 unusual names for a sci-fi spaceship.",
    temperature=0.95,
    top_p=1.0,
)
```

### Limiting Response Length

```python
# Get a short answer
response = chat(
    "Explain Docker in one sentence.",
    max_tokens=60,
)

# Longer, detailed response
response = chat(
    "Explain Docker with examples.",
    max_tokens=800,
)
```

### Stop Sequences

Stop sequences tell the model to halt generation when it produces a specific string.
Useful for structured output or preventing runaway responses:

```python
# Stop after the third list item
response = chat(
    "List programming languages (one per line):",
    stop=["4.", "\n\n"],
)

# Stop at end of a code block
response = chat(
    "Write a Python hello world function:",
    stop=["```"],
)
```

### Streaming

See the full [Streaming Guide](streaming.md) for all event types and patterns.
Here's the essential pattern:

```python
from aicortex import chat

stream = chat("Tell me a short story about a robot.", stream=True)

full_text = ""
for event in stream:
    if event.type == "token":
        print(event.content, end="", flush=True)
        full_text += event.content or ""

print(f"\n\n— {len(full_text)} characters generated —")
```

## Model Discovery API

### `families()` — List All Model Families

Returns the list of model families bundled with the package (derived from JSON filenames):

```python
from aicortex import families

print(families())
# ['deepseek', 'gemma', 'llama', 'mistral', 'qwen']
```

### `models(family=None)` — List Models

```python
from aicortex import models

# All available models (all families)
all_models = models()
print(f"{len(all_models)} models available")

# Filter by family (case-insensitive)
llama_models = models("llama")
mistral_models = models("mistral")
```

### `get_model_info(model)` — Full Model Metadata

Returns the complete metadata record for a model from the bundled JSON files:

```python
from aicortex import get_model_info

info = get_model_info("llama3.2:3b")
# {
#   'model_name': 'llama3.2:3b',
#   'ip_port': 'http://...',
#   'parameter_size': '3.2B',
#   'quantization_level': 'Q4_K_M',
#   'family': 'llama',
#   'format': 'gguf',
#   ...
# }
print(info['parameter_size'])
print(info['quantization_level'])
```

## Server Discovery API

### `list_model_servers(model)` — All Servers for a Model

```python
from aicortex import list_model_servers

servers = list_model_servers("llama3.2:3b")
for server in servers:
    print(f"  URL: {server['url']}")
    print(f"  Location: {server['location']['city']}, {server['location']['country']}")
    print(f"  Speed: {server['performance']['tokens_per_second']} tok/s")
    print()
```

### `get_server_info(model, server_url=None)` — Single Server Details

```python
from aicortex import get_server_info

# Get the first available server for a model
server = get_server_info("llama3.2:3b")
print(server['url'])

# Get info for a specific server URL
server = get_server_info("llama3.2:3b", server_url="http://1.2.3.4:11434")
```

## LangChain Integration

AI Cortex provides helpers that return the exact parameter dict expected by
LangChain's `OllamaLLM`:

```python
from langchain_ollama import OllamaLLM
from aicortex import get_llm_params, get_random_llm_params

# Specific model — picks a random live server automatically
params = get_llm_params("mistral:7b")
# → {'model': 'mistral:7b', 'base_url': 'http://...'}

llm = OllamaLLM(**params)
print(llm.invoke("What is LangChain?"))

# Fully random model and server — great for load distribution
params = get_random_llm_params()
llm = OllamaLLM(**params)
```

## Building Raw API Requests

`build_api_request()` constructs the Ollama JSON payload without sending it.
Useful for debugging, logging, or when you need to call Ollama directly:

```python
from aicortex import build_api_request

payload = build_api_request(
    model="llama3.2:3b",
    prompt="Hello, world!",
    temperature=0.5,
    num_predict=100,
    seed=42,
)
print(payload)
# {
#   'model': 'llama3.2:3b',
#   'prompt': 'Hello, world!',
#   'options': {
#     'temperature': 0.5,
#     'top_p': 0.9,
#     'stop': [],
#     'num_predict': 100,
#     'seed': 42
#   }
# }
```

## Error Handling

AI Cortex raises standard Python exceptions with descriptive messages:

```python
from aicortex import chat, get_model_info

# ValueError — model not found in registry
try:
    info = get_model_info("nonexistent:model")
except ValueError as e:
    print(f"Model not found: {e}")

# RuntimeError — all servers failed or none available
try:
    response = chat("Hello", model="llama3.2:3b")
except RuntimeError as e:
    print(f"Server error: {e}")

# RuntimeError — no models in registry at all
try:
    from aicortex import get_random_llm_params
    params = get_random_llm_params()
except RuntimeError as e:
    print(f"No models available: {e}")
```

> **⚠️ Automatic Failover:** When `chat()` is called, AI Cortex shuffles the list of servers
> for the requested model and tries each one in turn. Only if *all* servers fail does it raise
> `RuntimeError`. In practice, transient network errors are silently retried.

## Next Steps

- 🔀 [Streaming in depth](streaming.md) — all `StreamEvent` types, async patterns, UI integration
- 🤖 [Model Management](models.md) — how the JSON registry works, updating model data
- 🖥️ [Server Mode](server.md) — expose AI Cortex as an OpenAI-compatible REST API
