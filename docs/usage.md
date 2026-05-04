# 📖 Basic Usage

This guide covers every parameter of the `chat()` function, common usage patterns,
error handling, and the model/server discovery API.

## Importing AI Cortex

```python
# Core chat function — this is all most users need
from aicortex import chat

# Multi-turn sessions
from aicortex import Session

# Smart server routing
from aicortex import best_server, clear_server_cache

# Model discovery
from aicortex import families, models, get_model_info, search_models

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
    session: Session | str | None = None,
    system: str | None = None,
    response_format: Literal["text", "json"] = "text",
    schema: dict | None = None,
    routing: Literal["random", "fastest", "nearest"] = "random",
) -> str | dict | Stream:
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
| `session` | `Session \| str \| None` | `None` | Enable multi-turn memory. Pass a `Session` object or raw session id string |
| `system` | `str \| None` | `None` | System prompt forwarded to the model for this call only |
| `response_format` | `Literal["text", "json"]` | `"text"` | Return a parsed `dict` instead of `str` when `"json"` |
| `schema` | `dict \| None` | `None` | JSON Schema to validate the parsed response against (requires `jsonschema`) |
| `routing` | `Literal["random", "fastest", "nearest"]` | `"random"` | Server selection strategy for this call |

### Return Values

- **`stream=False`, `response_format="text"`** → returns `str` — the full generated response text
- **`stream=False`, `response_format="json"`** → returns `dict` — the parsed JSON response
- **`stream=True`** → returns `Stream` — an iterable of `StreamEvent` objects (sync or async)

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

## Multi-Turn Sessions

`chat()` is stateless by default — every call is a cold start. The `Session` class
adds multi-turn memory backed by an in-process store, with no external dependencies.

### Creating a Session

```python
from aicortex import chat, Session

# Auto-generate a session id
session = Session()
print(session.id)  # e.g. "a3f1c2d4"

# Resume an existing session by id
session = Session(id="a3f1c2d4")

# Session with unknown id raises immediately
session = Session(id="unknown")  # KeyError: No session with id 'unknown' found...
```

### Chatting with a Session

Pass the `Session` object (or its raw id string) to `chat()`. History is appended
automatically after every successful response:

```python
from aicortex import chat, Session

session = Session()

r1 = chat("My name is Alice.", session=session)
r2 = chat("What's my name?", session=session)
print(r2)  # → "Your name is Alice."

# Raw id string works too
r3 = chat("And what did I say first?", session=session.id)
```

### Inspecting and Managing History

```python
# Read-only view of accumulated turns
print(session.history)
# [
#   {"role": "user",      "content": "My name is Alice."},
#   {"role": "assistant", "content": "Nice to meet you, Alice!"},
#   ...
# ]

# Clear history — keeps the session id registered
session.reset()

# Remove the session entirely — instance is invalid after this
session.delete()
```

> **Note:** History is in-process only and is lost on process restart. For persistence,
> serialize `session.history` to disk or a database between runs and replay it manually.

---

## Async Support

`chat()` detects whether it is running inside an event loop and switches mode automatically.
No configuration required — the same function works in both sync and async contexts.

### Using `chat()` in FastAPI

```python
from fastapi import FastAPI
from aicortex import chat, Session

app = FastAPI()

@app.post("/ask")
async def ask(prompt: str, session_id: str | None = None):
    session = Session(id=session_id) if session_id else Session()
    # await is not needed — chat() returns a coroutine automatically
    # when called from inside a running event loop
    response = await chat(prompt, model="llama3.2:3b", session=session)
    return {"response": response, "session_id": session.id}
```

### Async Streaming

```python
import asyncio
from aicortex import chat

async def stream_response():
    stream = await chat("Tell me a short story.", model="mistral:7b", stream=True)
    async for event in stream:
        if event.type == "token":
            print(event.content, end="", flush=True)

asyncio.run(stream_response())
```

---

## Structured Output (JSON Mode)

Use `response_format="json"` to get a parsed `dict` back instead of a raw string.
AI Cortex injects a JSON instruction into the system prompt and validates the response.

### Basic JSON Response

```python
from aicortex import chat

result = chat(
    "Return the capital and population of France as JSON.",
    model="llama3.2:3b",
    response_format="json",
)
print(result)        # {"capital": "Paris", "population": 68000000}
print(type(result))  # <class 'dict'>
```

### Schema Validation

Pass a JSON Schema dict to `schema=` to validate the response structure.
Raises `jsonschema.ValidationError` on mismatch:

```python
from aicortex import chat

schema = {
    "type": "object",
    "properties": {
        "capital":    {"type": "string"},
        "population": {"type": "integer"},
    },
    "required": ["capital", "population"],
}

result = chat(
    "Return the capital and population of Germany as JSON.",
    model="llama3.2:3b",
    response_format="json",
    schema=schema,
)
print(result["capital"])     # "Berlin"
print(result["population"])  # 84000000
```

> **Note:** `schema` requires the `jsonschema` package (`pip install jsonschema`).
> Combining `response_format="json"` with `stream=True` raises `ValueError` immediately.

---

## System Prompt

Use the `system=` parameter to pass a system prompt for the current call.
It is forwarded directly to the model and is never stored in session history.

```python
from aicortex import chat

response = chat(
    "Explain recursion.",
    model="llama3.2:3b",
    system="You are a patient teacher who explains concepts using simple analogies.",
)
```

> **Note:** Passing both `system=` and `persona=` raises `ValueError`. Use one or the other.

---

## Smart Routing

Control which server handles a request using the `routing=` parameter.

| Strategy | Behaviour |
|---|---|
| `"random"` *(default)* | Shuffles the server pool; proven-fast servers float to the top over time |
| `"fastest"` | Picks the server with the highest live tokens-per-second |
| `"nearest"` | Picks the geographically closest server using bundled metadata |

```python
from aicortex import chat

# Always use the fastest available server
response = chat("Summarise this document.", model="mistral:7b", routing="fastest")

# Prefer a low-latency nearby server
response = chat("Quick reply please.", model="llama3.2:3b", routing="nearest")
```

### `best_server()` — Query the Winning Server Directly

```python
from aicortex import best_server

server = best_server("llama3.2:3b", strategy="fastest")
print(server["url"])               # http://1.2.3.4:11434
print(server["tokens_per_second"]) # 94.3

server = best_server("mistral:7b", strategy="nearest")
print(server["location"]["country"])  # "DE"
```

Results are cached per `(model, strategy)` key for 5 minutes. Call
`clear_server_cache()` to flush the cache manually:

```python
from aicortex import clear_server_cache

clear_server_cache()  # flushes bad-server, good-server, and best_server caches
```

---

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


---

## CLI — `aicortex` Command

AI Cortex ships a command-line interface accessible via `aicortex` (after install)
or `python -m aicortex`.

### `aicortex chat`

Send a prompt and print the response.

```bash
# Basic chat
aicortex chat "Explain neural networks in one sentence."

# Choose a model
aicortex chat "Hello!" --model gemma3:4b

# Stream tokens as they arrive
aicortex chat "Write a short poem." --stream

# Set a system prompt
aicortex chat "What is my name?" --system "You are a helpful assistant named Aria."

# Use fastest server routing
aicortex chat "Hello" --routing fastest --timeout 10

# Multi-turn session (session must be created in Python first via Session())
aicortex chat "What did I just tell you?" --session my-session-id
```

**All flags:**

| Flag | Default | Description |
|---|---|---|
| `--model`, `-m` | `llama3.2:3b` | Model to use |
| `--stream`, `-s` | off | Stream tokens incrementally |
| `--temperature`, `-t` | `0.7` | Sampling temperature |
| `--system` | — | System prompt (raw string) |
| `--session` | — | Session id for multi-turn memory |
| `--routing` | `random` | `random`, `fastest`, or `nearest` |
| `--timeout` | `30.0` | Seconds before server timeout |

---

### `aicortex models`

List available model families and their models.

```bash
# List all families with model counts
aicortex models

# List models in a specific family
aicortex models --family gemma

# Search across all families by name substring
aicortex models --search 70b
aicortex models --search llama --family llama
```

---

### `aicortex servers`

List all known Ollama servers hosting a specific model.

```bash
aicortex servers llama3.2:3b
aicortex servers mistral:7b
```

Output includes URL, city, country, and tokens-per-second for each server.

---

## `search_models()` — Cross-Family Model Search

Find models by name substring across all families, with optional filters for
family, generation, and parameter size.

```python
from aicortex import search_models

# Search by name substring — returns all models containing "70b"
results = search_models("70b")
print(results)  # ['llama3.1:70b', 'qwen2.5:72b', ...]

# Scope to one family
results = search_models("llama", family="llama")

# Filter by parameter size range
results = search_models("llama", min_params="8b", max_params="70b")

# Filter by generation (requires pipeline update — Section 6.1.2)
results = search_models("gemma", family="gemma", generation=3)
# → ['gemma3:27b', 'gemma3:12b', 'gemma3:4b', 'gemma3:1b']
```

**Parameters:**

| Param | Type | Description |
|---|---|---|
| `query` | `str` | Case-insensitive substring to match against model names |
| `family` | `str \| None` | Scope to one family; `None` searches all |
| `generation` | `int \| None` | Filter by generation (e.g. `3` for gemma3) |
| `min_params` | `str \| None` | Minimum size e.g. `"7b"` — smaller models excluded |
| `max_params` | `str \| None` | Maximum size e.g. `"70b"` — larger models excluded |

Results are sorted by parameter size descending. Returns `[]` if nothing matches.
