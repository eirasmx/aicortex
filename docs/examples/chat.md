# 💬 Chat Examples

> **Annotated examples for the `chat()` function** — from the simplest one-liner to
> multi-turn conversations, parameter tuning, error handling, and model selection patterns.

See the [API Reference](../api.md) for the full `chat()` signature and parameter table.

## The Minimal Case

```python
from aicortex import chat

response = chat("What is the capital of France?")
print(response)
# → "The capital of France is Paris."
```

`chat()` returns a plain `str`. No configuration required — it selects a model and
server automatically from the bundled registry.

## Specifying a Model

```python
from aicortex import chat

# Use a small, fast model for simple tasks
response = chat("Summarize this in one sentence: ...", model="llama3.2:3b")

# Use a larger model for complex reasoning
response = chat("Prove that √2 is irrational.", model="llama3.1:70b")

# Use a code-focused model
response = chat("Write a binary search in Rust.", model="deepseek-coder:6.7b")
```

Model identifiers follow the `family:size` convention. Use `models()` to list
everything available:

```python
from aicortex import models

print(models())           # all models across all families
print(models("mistral"))  # only mistral family models
```

## Tuning the Response

```python
from aicortex import chat

# Deterministic — good for factual Q&A, classification, structured output
precise = chat(
    "Extract the date from: 'The meeting is on March 12th, 2025.'",
    model="llama3.2:3b",
    temperature=0.0,
)

# Creative — good for brainstorming, writing, ideation
creative = chat(
    "Give me five unusual names for a space-themed coffee shop.",
    model="mistral:7b",
    temperature=1.2,
    top_p=0.95,
)

# Length-constrained — when you need a short answer
brief = chat(
    "What is photosynthesis?",
    model="llama3.2:3b",
    max_tokens=80,
)
```

| Parameter | What it controls |
|---|---|
| `temperature` | Randomness — 0.0 is deterministic, 1.0+ is creative |
| `top_p` | Token sampling breadth — lower values narrow the vocabulary |
| `max_tokens` | Hard cap on response length |
| `stop` | List of strings that end generation early |

## Stop Sequences

Stop sequences tell the model to end generation when it produces a specific string.
Useful when you need structured output without the model going off-script:

```python
response = chat(
    "List three programming languages. Format: 1. Name\n2. Name\n3. Name",
    model="llama3.2:3b",
    stop=["4."],  # stop before a fourth item appears
)
```

## Multi-Turn Conversation with `Session`

`chat()` is stateless by default. Use the `Session` class to maintain multi-turn
memory automatically — no manual history management required:

```python
from aicortex import chat, Session

session = Session()

r1 = chat("My name is Alice and I'm learning Python.", session=session)
print(r1)

r2 = chat("What's my name?", session=session)
print(r2)  # → "Your name is Alice."

r3 = chat("What did I say I was learning?", session=session)
print(r3)  # → "You said you were learning Python."
```

### Resuming a Session

Sessions are identified by a string id. Save the id to resume a conversation later
within the same process:

```python
from aicortex import chat, Session

# Start a session and note the id
session = Session()
session_id = session.id
chat("My favourite language is Rust.", session=session)

# ... later in the same process ...
resumed = Session(id=session_id)
response = chat("What's my favourite language?", session=resumed)
print(response)  # → "Your favourite language is Rust."
```

### Passing a Raw Id String

```python
response = chat("Remind me what we discussed.", session=session_id)
```

### Inspecting and Resetting History

```python
print(session.history)  # list of {"role": ..., "content": ...} dicts
session.reset()         # clears history, keeps id registered
session.delete()        # removes session entirely
```

> **💡 Token budget tip** — history grows with every turn. Check
> `get_model_info(model)["context_length"]` and trim old turns when approaching the limit.

## System Prompt

Use `system=` to give the model a role or behavioural instruction for a single call.
It is not stored in session history:

```python
from aicortex import chat

response = chat(
    "Explain what a linked list is.",
    model="llama3.2:3b",
    system="You are a patient teacher who uses simple real-world analogies.",
)
print(response)

# Works alongside sessions — system applies to this call only
from aicortex import Session
session = Session()
chat("My name is Bob.", session=session)
response = chat(
    "Who am I?",
    session=session,
    system="Answer like a pirate.",
)
print(response)  # → "Arrr, ye be Bob, matey!"
```

## Error Handling

```python
from aicortex import chat
from aicortex.exceptions import ModelNotFoundError, ServerError

def safe_chat(prompt: str, model: str = "llama3.2:3b") -> str | None:
    try:
        return chat(prompt, model=model)
    except ModelNotFoundError as e:
        print(f"Model not available: {e}")
        print("Try: from aicortex import models; print(models())")
        return None
    except ServerError as e:
        print(f"No server reachable: {e}")
        print("Is Ollama running? Try: ollama serve")
        return None

response = safe_chat("Hello!", model="llama3.2:3b")
if response:
    print(response)
```

## Exploring Available Models Before Chatting

```python
from aicortex import families, models, get_model_info, chat

# 1. List families
print("Families:", families())
# → ['llama', 'mistral', 'deepseek', 'qwen', 'gemma']

# 2. Pick a family and list its models
llama_models = models("llama")
print("Llama models:", llama_models)

# 3. Inspect a model before using it
info = get_model_info("llama3.2:3b")
print(f"  Size: {info['size']}")
print(f"  Context: {info['context_length']} tokens")
print(f"  Parameters: {info['parameters']}")

# 4. Chat with it
response = chat("Explain transformers in ML.", model="llama3.2:3b")
print(response)
```

## Batch Processing

For processing many prompts, call `chat()` in a loop. For high throughput,
use a `ThreadPoolExecutor` since each call blocks on network I/O:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from aicortex import chat

prompts = [
    "Summarize: The quick brown fox...",
    "Translate to French: Good morning",
    "What is 17 * 23?",
    "List three Python best practices.",
]

def process(prompt: str) -> tuple[str, str]:
    return prompt, chat(prompt, model="llama3.2:3b", temperature=0.0)

with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(process, p): p for p in prompts}
    for future in as_completed(futures):
        prompt, response = future.result()
        print(f"Q: {prompt[:40]}...")
        print(f"A: {response[:80]}...\n")
```

> **Note** — each `chat()` call occupies one Ollama inference slot.
> Running more workers than your GPU can handle in parallel will queue
> at the server, not speed things up. Match `max_workers` to your hardware.

## See Also

- [Streaming Examples](streaming.md) — print tokens as they arrive
- [API Reference — chat()](../api.md#chat) — full parameter documentation
- [Usage Guide](../usage.md) — practical patterns and parameter deep-dive
