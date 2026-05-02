# 🔌 API Reference

Complete reference for every public function and class in AI Cortex.
All symbols are importable directly from the `aicortex` package.

## Quick Import Reference

```python
# The essentials — most users only need these
from aicortex import chat, models, families

# Model & server discovery
from aicortex import get_model_info, list_model_servers, get_server_info

# LangChain / OllamaLLM integration
from aicortex import get_llm_params, get_random_llm_params

# Advanced: build a raw request payload without sending it
from aicortex import build_api_request

# Streaming types
from aicortex import Stream, StreamEvent

# Tools sub-package
from aicortex import tools
```

## Core Functions

### `chat()`

The primary entry point for interacting with any Ollama-served language model.
Handles model validation, server selection, automatic failover across multiple
endpoints, and both synchronous and streaming response modes.

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
) -> str | Stream
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `prompt` | `str` | *(required)* | The input text to send to the model |
| `model` | `str` | `"gpt-oss:20b"` | Model identifier — must exist in the bundled registry. Use `models()` to list valid names |
| `stream` | `bool` | `False` | When `True`, returns a `Stream` object you can iterate over token-by-token. When `False`, blocks until the full response is ready and returns a `str` |
| `temperature` | `float` | `0.7` | Controls randomness. `0.0` = fully deterministic, `1.0` = highly creative. Use low values (`0.1`–`0.3`) for code and factual tasks; higher values (`0.7`–`1.0`) for creative writing |
| `max_tokens` | `int \| None` | `None` | Maximum number of tokens to generate. `None` lets the server decide. Maps to Ollama's `num_predict` option |
| `top_p` | `float` | `1.0` | Nucleus sampling: at each step, only the top tokens whose cumulative probability reaches `top_p` are considered. Lower values (e.g. `0.9`) reduce the vocabulary and can improve coherence |
| `stop` | `list[str] \| None` | `None` | One or more strings that cause generation to stop immediately when produced. Useful for structured output (e.g. `stop=["</answer>"]`) or preventing runaway responses |

**Returns**

- `str` — full response text when `stream=False`
- `Stream` — iterable event container when `stream=True`

**Raises**

| Exception | When |
|---|---|
| `ValueError` | The `model` name is not found in the registry |
| `RuntimeError` | No Ollama servers are available for the model, or all tried servers failed |

**Behaviour Notes**

- AI Cortex shuffles the list of known servers for the model and tries each one in random order. Only when every server fails does it raise `RuntimeError`. Transient network failures are silently retried.
- Passing `model=None` (internal API) selects a random model from the full registry.

**Examples**

```python
from aicortex import chat

# Minimal — uses default model
response = chat("What year did the Berlin Wall fall?")
print(response)

# Deterministic code generation
code = chat(
    "Write a Python function that checks if a number is prime.",
    model="llama3.2:3b",
    temperature=0.1,
    max_tokens=300,
)

# Creative writing with stop sequence
poem = chat(
    "Write a haiku about autumn:",
    model="mistral:7b",
    temperature=0.9,
    stop=["\n\n"],
)

# Streaming
stream = chat("Explain how GPT works.", stream=True)
for event in stream:
    if event.type == "token":
        print(event.content, end="", flush=True)
```

### `families()`

Returns the list of model families whose metadata is bundled with the package.
Family names are derived from the JSON filenames in `aicortex/models/`.

```python
def families() -> List[str]
```

**Returns** — `List[str]` : alphabetically sorted family names.

```python
from aicortex import families

print(families())
# ['deepseek', 'gemma', 'llama', 'mistral', 'qwen']
```

> **💡 Tip:** Family names are always lowercase and correspond 1-to-1 with files in `aicortex/models/` (e.g. `llama.json` → `"llama"`).

### `models()`

Lists all available model names, optionally filtered to a single family.

```python
def models(family: Optional[str] = None) -> List[str]
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `family` | `str \| None` | `None` | Family name to filter by (case-insensitive). Returns all models when `None` |

**Returns** — `List[str]` : model name strings (e.g. `"llama3.2:3b"`, `"mistral:7b"`).

```python
from aicortex import models

# Every model across all families
all_models = models()
print(f"{len(all_models)} models available")

# Models in a specific family
llama = models("llama")
mistral = models("Mistral")   # case-insensitive
unknown = models("unknown")   # returns [] — never raises
```

### `get_model_info()`

Returns the complete metadata record for a named model from the bundled JSON registry.
Useful for inspecting model size, quantization, server location, and performance data.

```python
def get_model_info(model: str) -> Dict[str, Any]
```

**Parameters**

| Name | Type | Description |
|---|---|---|
| `model` | `str` | Exact model name (e.g. `"llama3.2:3b"`). Must match `model_name` or `model` field in the registry |

**Returns** — `Dict[str, Any]` : the full metadata dict for that model.

**Raises** — `ValueError` if the model is not found.

**Example metadata fields**

| Field | Description |
|---|---|
| `model_name` | Canonical model identifier |
| `ip_port` | Ollama server URL where this model is hosted |
| `parameter_size` | Human-readable parameter count (e.g. `"3.2B"`) |
| `quantization_level` | Quantization format (e.g. `"Q4_K_M"`) |
| `family` | Model family (`"llama"`, `"mistral"`, …) |
| `format` | File format (e.g. `"gguf"`) |
| `ip_city_name_en` | City of the hosting server |
| `ip_country_name_en` | Country of the hosting server |
| `perf_tokens_per_second` | Measured inference speed |

```python
from aicortex import get_model_info

info = get_model_info("llama3.2:3b")
print(f"Size:          {info['parameter_size']}")
print(f"Quantization:  {info['quantization_level']}")
print(f"Server:        {info['ip_port']}")
print(f"Location:      {info.get('ip_city_name_en')}, {info.get('ip_country_name_en')}")
```

### `list_model_servers()`

Returns every known Ollama server that hosts a specific model, with location
and performance metadata for each.

```python
def list_model_servers(model: str) -> List[Dict[str, Any]]
```

**Parameters**

| Name | Type | Description |
|---|---|---|
| `model` | `str` | Model name to look up |

**Returns** — `List[Dict]` where each dict has:

```python
{
    "url": "http://1.2.3.4:11434",
    "location": {
        "city":      "Frankfurt",
        "country":   "Germany",
        "continent": "Europe",
    },
    "organization": "Hetzner Online GmbH",
    "performance": {
        "tokens_per_second": 42.3,
        "last_tested":       "2025-04-01T12:00:00Z",
    },
}
```

```python
from aicortex import list_model_servers

servers = list_model_servers("llama3.2:3b")
print(f"{len(servers)} server(s) found")

for s in servers:
    tps = s["performance"]["tokens_per_second"]
    loc = f"{s['location']['city']}, {s['location']['country']}"
    print(f"  {s['url']}  |  {loc}  |  {tps} tok/s")
```

### `get_server_info()`

Returns metadata for a single Ollama server hosting a given model.
If `server_url` is omitted, returns the **first** server in the list.

```python
def get_server_info(
    model: str,
    server_url: Optional[str] = None,
) -> Dict[str, Any]
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `str` | *(required)* | Model name |
| `server_url` | `str \| None` | `None` | If provided, returns info for that specific URL. Raises `ValueError` if not found |

**Raises**

- `ValueError` — model has no known servers, or `server_url` was specified but not found.

```python
from aicortex import get_server_info

# First available server
server = get_server_info("llama3.2:3b")
print(server["url"])

# Specific server
server = get_server_info("llama3.2:3b", server_url="http://1.2.3.4:11434")
```

### `build_api_request()`

Constructs the raw Ollama JSON payload for a chat request **without sending it**.
Use this when you need to inspect, log, or manually submit the request.

```python
def build_api_request(
    model: str,
    prompt: str,
    **kwargs: Any,
) -> Dict[str, Any]
```

**Parameters**

| Name | Type | Description |
|---|---|---|
| `model` | `str` | Model name — validated against the registry |
| `prompt` | `str` | Input prompt text |
| `**kwargs` | `Any` | Any of: `temperature`, `top_p`, `stop`, `num_predict`, `repeat_penalty`, `seed`, `tfs_z`, `mirostat`, `messages`, `system`, `tools`, `tool_choice`, `session_id`, `memory`, `metadata` |

**Returns** — `Dict[str, Any]` : Ollama-compatible request payload.

**Raises** — `ValueError` if the model is not in the registry.

```python
from aicortex import build_api_request

payload = build_api_request(
    model="llama3.2:3b",
    prompt="What is 2 + 2?",
    temperature=0.0,
    seed=42,
    num_predict=20,
)
# {
#   'model': 'llama3.2:3b',
#   'prompt': 'What is 2 + 2?',
#   'options': {
#     'temperature': 0.0,
#     'top_p': 0.9,
#     'stop': [],
#     'num_predict': 20,
#     'seed': 42
#   }
# }
```

### `get_llm_params()`

Returns a `{"model": ..., "base_url": ...}` dict for a specific model,
selecting a random live server. Designed for direct use with LangChain's `OllamaLLM`.

```python
def get_llm_params(model: Optional[str] = None) -> Dict[str, str]
```

**Parameters**

| Name | Type | Default | Description |
|---|---|---|---|
| `model` | `str \| None` | `None` | Model name. When `None`, picks a random model from the full registry |

**Returns** — `Dict[str, str]` with keys `"model"` and `"base_url"`.

**Raises**

- `ValueError` — specified model not found in registry.
- `RuntimeError` — no models available, or no servers for the model.

```python
from aicortex import get_llm_params
from langchain_ollama import OllamaLLM

params = get_llm_params("mistral:7b")
# {'model': 'mistral:7b', 'base_url': 'http://...'}

llm = OllamaLLM(**params)
print(llm.invoke("Summarise the Turing test in one sentence."))
```

### `get_random_llm_params()`

Equivalent to `get_llm_params(model=None)`. Picks a random model **and**
a random server — useful for distributing load or experimentation.

```python
def get_random_llm_params() -> Dict[str, str]
```

**Returns** — `Dict[str, str]` with keys `"model"` and `"base_url"`.

**Raises** — `RuntimeError` if no models or servers are available.

```python
from aicortex import get_random_llm_params
from langchain_ollama import OllamaLLM

# Every call may land on a different model and server
params = get_random_llm_params()
print(f"Using model: {params['model']} at {params['base_url']}")

llm = OllamaLLM(**params)
```

## Classes

### `StreamEvent`

A dataclass representing a single event emitted during a streaming response.
Every iteration of a `Stream` yields one `StreamEvent`.

```python
@dataclass
class StreamEvent:
    type:         EventType        # What kind of event this is
    content:      str | None       # Text payload (present on 'token' events)
    index:        int | None       # Sequential token index (0-based)
    tool_name:    str | None       # Name of the tool being called
    tool_args:    dict | None      # Arguments passed to the tool
    tool_result:  Any              # Return value from tool execution
    meta:         dict | None      # Arbitrary server-side metadata
    timestamp:    float | None     # Unix timestamp of event creation
```

**`EventType` values**

| Type | When it fires | `content` |
|---|---|---|
| `"start"` | Once, before any tokens — signals the stream has begun | `""` (empty) |
| `"token"` | Once per generated token — the core data event | The token text (may be a word, sub-word, or punctuation) |
| `"end"` | Once, after all tokens — signals clean completion | `""` (empty) |
| `"error"` | When a server or generation error occurs | Error message string |
| `"tool_call"` | When the model invokes a tool | Tool invocation info |
| `"tool_result"` | When a tool execution completes | Tool result value |
| `"meta"` | For server-side metadata or diagnostics | Varies |

> **⚠️ Important:** Always check `event.type == "token"` before reading `event.content`.
> On `"start"` and `"end"` events, `content` is an empty string, not `None`.

```python
from aicortex import chat, StreamEvent

stream = chat("Name three planets.", stream=True)

for event in stream:
    if event.type == "start":
        print(f"[{event.timestamp:.2f}] Stream started")

    elif event.type == "token":
        print(event.content, end="", flush=True)
        # event.index tells you which token number this is

    elif event.type == "end":
        print(f"\n[{event.timestamp:.2f}] Stream complete")

    elif event.type == "error":
        print(f"\n⚠️  Error: {event.content}")
```

### `Stream`

A container returned by `chat(..., stream=True)`.
Collects `StreamEvent` objects as they arrive and exposes them as an iterable.
After iteration, all events remain accessible via `stream.events`.

```python
class Stream:
    events: list[StreamEvent]   # All collected events

    def __iter__(self) -> Iterator[StreamEvent]: ...
    def add(self, event: StreamEvent) -> None: ...
    def text(self) -> str: ...
```

**Methods**

#### `__iter__()` — Iterate over events

```python
stream = chat("Hello", stream=True)
for event in stream:
    ...
```

#### `add(event)` — Append an event

Used internally by the streaming engine. You can also use it to build
`Stream` objects manually for testing:

```python
from aicortex import Stream, StreamEvent

s = Stream()
s.add(StreamEvent(type="token", content="Hello", index=0))
s.add(StreamEvent(type="token", content=" world", index=1))
print(s.text())  # "Hello world"
```

#### `text()` — Extract full response text

Concatenates the `content` of every `"token"` event in order.
Non-token events (start, end, error, meta) are excluded.

```python
stream = chat("What is Python?", stream=True)

# Consume the stream silently, then get the full text
full_response = stream.text()
print(full_response)

# Or iterate AND retain the text
for event in stream:
    if event.type == "token":
        print(event.content, end="", flush=True)

print(f"\n\n{len(stream.text())} characters generated.")
```

> **💡 Note:** `stream.events` persists after iteration. You can inspect the
> full event log, count tokens, extract timestamps, or replay events.

```python
stream = chat("Brief answer please.", stream=True)
for event in stream: pass  # consume

token_events = [e for e in stream.events if e.type == "token"]
print(f"Generated {len(token_events)} tokens")
print(f"First token at t={token_events[0].timestamp:.3f}")
print(f"Last  token at t={token_events[-1].timestamp:.3f}")
```

## Tools Sub-Package

See the dedicated **[Tools Reference](tools.md)** for full documentation of:

- `tools.find_valid_endpoints()` — ping-test all known Ollama IP endpoints
- `tools.fetch_models()` — pull model lists from validated URLs
- `tools.resolve_models()` — merge fetched data with IP metadata
- `tools.apply_valid_models()` — write resolved data into family JSON files
- `tools.run_server()` — launch the OpenAI-compatible FastAPI proxy

Quick import:

```python
from aicortex.tools import (
    find_valid_endpoints,
    fetch_models,
    resolve_models,
    apply_valid_models,
    run_server,
)
```
