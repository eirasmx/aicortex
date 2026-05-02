# ⚡ Streaming

AI Cortex supports real-time token streaming — get model output as it's generated,
token by token, rather than waiting for the entire response to complete.
This is essential for chatbots, live dashboards, writing assistants, and any
interface where perceived latency matters.

## How Streaming Works

When you call `chat(..., stream=True)`, AI Cortex:

1. Opens a streaming connection to an Ollama server
2. Emits a `StreamEvent(type="start")` immediately
3. Yields one `StreamEvent(type="token")` per generated token as it arrives
4. Emits a `StreamEvent(type="end")` when generation completes
5. Emits `StreamEvent(type="error")` and moves to the next server if one fails

All events are collected into a `Stream` object, which you iterate over.

## The Essential Pattern

```python
from aicortex import chat

stream = chat("Explain how black holes form.", stream=True)

for event in stream:
    if event.type == "token":
        print(event.content, end="", flush=True)

print()  # newline after the response
```

> **💡 Always pass `flush=True`** when printing tokens.
> Without it, Python's output buffering may hold tokens back and
> they'll all appear at once — defeating the purpose of streaming.

## StreamEvent Reference

Every item yielded during iteration is a `StreamEvent` dataclass:

```python
@dataclass
class StreamEvent:
    type:        str          # Event kind — see table below
    content:     str | None   # Token text (token events only)
    index:       int | None   # Token sequence number (0-based)
    tool_name:   str | None   # Set on tool_call events
    tool_args:   dict | None  # Set on tool_call events
    tool_result: Any          # Set on tool_result events
    meta:        dict | None  # Server-side metadata
    timestamp:   float | None # Unix timestamp (seconds)
```

### Event Type Reference

| `type` | Fires | `content` | Typical use |
|---|---|---|---|
| `"start"` | Once, before any tokens | `""` | Show a loading spinner, log start time |
| `"token"` | Once per token generated | The token text | Print to UI, append to buffer |
| `"end"` | Once, after all tokens | `""` | Hide spinner, enable copy button |
| `"error"` | On server/network failure | Error message | Show error UI, log for debugging |
| `"tool_call"` | Model invokes a tool | Tool info | Forward to tool executor |
| `"tool_result"` | Tool execution completes | Result data | Feed result back to model |
| `"meta"` | Server metadata | Varies | Diagnostics, stats |

> **⚠️ Check `event.type` before reading `event.content`.**
> On `"start"` and `"end"` events, `content` is `""` not `None`.
> On `"error"` events, `content` contains the error message string.

## Working with the `Stream` Object

The return value of `chat(..., stream=True)` is a `Stream` instance —
not a raw generator. This means you can iterate it **and** inspect its
collected events afterwards.

### Iterating

```python
stream = chat("Name the planets in order.", stream=True)

for event in stream:
    if event.type == "token":
        print(event.content, end="", flush=True)
```

### Getting the Full Text

`stream.text()` concatenates all `"token"` event contents in order:

```python
stream = chat("What is the Turing test?", stream=True)

# Option A — iterate and collect manually
parts = []
for event in stream:
    if event.type == "token":
        parts.append(event.content or "")
full = "".join(parts)

# Option B — use the built-in helper (equivalent)
stream2 = chat("What is the Turing test?", stream=True)
full = stream2.text()
```

### Inspecting Collected Events

After iteration, `stream.events` holds all events that were emitted.
This is useful for analytics, debugging, and replaying output:

```python
stream = chat("Write a limerick about Python.", stream=True)
for event in stream: pass  # consume all events

# Count tokens generated
tokens = [e for e in stream.events if e.type == "token"]
print(f"Generated {len(tokens)} tokens")

# Measure time-to-first-token
start_evt  = next(e for e in stream.events if e.type == "start")
first_tok  = next(e for e in stream.events if e.type == "token")
ttft = first_tok.timestamp - start_evt.timestamp
print(f"Time to first token: {ttft*1000:.1f} ms")

# Measure total generation time
end_evt = next(e for e in stream.events if e.type == "end")
total = end_evt.timestamp - start_evt.timestamp
print(f"Total generation time: {total:.2f}s")
print(f"Average speed: {len(tokens)/total:.1f} tok/s")
```

## Handling All Event Types

A robust handler that processes every event type:

```python
from aicortex import chat

def stream_with_full_handling(prompt: str, model: str = "llama3.2:3b"):
    stream = chat(prompt, model=model, stream=True)
    response_parts = []

    for event in stream:
        if event.type == "start":
            print("🟢 Generating...\n")

        elif event.type == "token":
            text = event.content or ""
            print(text, end="", flush=True)
            response_parts.append(text)

        elif event.type == "end":
            full = "".join(response_parts)
            print(f"\n\n✅ Done — {len(full)} chars, {len(response_parts)} tokens")

        elif event.type == "error":
            print(f"\n⚠️  Server error: {event.content}")
            print("    AI Cortex will retry on the next available server.")

        elif event.type == "meta":
            # Optional: log server-side metadata
            pass

    return "".join(response_parts)

result = stream_with_full_handling("Tell me a fun fact about octopuses.")
```

## Progress Tracking

Track how many tokens have been generated in real time:

```python
from aicortex import chat

stream = chat("Explain the history of the internet.", stream=True)
token_count = 0

for event in stream:
    if event.type == "token":
        token_count += 1
        print(event.content, end="", flush=True)
        if token_count % 50 == 0:
            print(f"\n  [{token_count} tokens so far...]", flush=True)

print(f"\n\nFinal count: {token_count} tokens")
```

## Streaming to a File

Write the response directly to disk as it streams — no need to hold
the entire response in memory:

```python
from aicortex import chat

with open("output.txt", "w", encoding="utf-8") as f:
    stream = chat("Write a 500-word essay on climate change.", stream=True)

    for event in stream:
        if event.type == "token" and event.content:
            f.write(event.content)
            f.flush()  # Write each token immediately — no buffering

print("Essay saved to output.txt")
```

## Error Handling

### Graceful Error Recovery

```python
from aicortex import chat

def safe_stream(prompt: str) -> str:
    try:
        stream = chat(prompt, model="llama3.2:3b", stream=True)
        parts = []

        for event in stream:
            if event.type == "token":
                print(event.content, end="", flush=True)
                parts.append(event.content or "")
            elif event.type == "error":
                # An individual server failed — AI Cortex moves to next server.
                # Log it, but don't break: the stream may recover.
                print(f"\n[Warning: {event.content}]", flush=True)

        return "".join(parts)

    except RuntimeError as e:
        # All servers exhausted — nothing left to try
        print(f"\n❌ All servers failed: {e}")
        return ""

result = safe_stream("What is machine learning?")
```

### Testing Connectivity Before Streaming

```python
from aicortex import models, list_model_servers, chat

MODEL = "llama3.2:3b"

# Check model exists
if MODEL not in models():
    print(f"Model '{MODEL}' not found. Available: {models()[:5]}")
else:
    servers = list_model_servers(MODEL)
    print(f"Found {len(servers)} server(s) for {MODEL}")

    # Now stream safely
    stream = chat("Hello!", model=MODEL, stream=True)
    print(stream.text())
```

## Integration Patterns

### WebSocket Server (FastAPI)

Stream AI responses directly to a browser client:

```python
from fastapi import FastAPI, WebSocket
from aicortex import chat

app = FastAPI()

@app.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    async for message in websocket.iter_text():
        # Run streaming in a thread to avoid blocking the event loop
        import asyncio
        loop = asyncio.get_event_loop()

        stream = await loop.run_in_executor(
            None, lambda: chat(message, stream=True)
        )
        for event in stream:
            if event.type == "token" and event.content:
                await websocket.send_text(event.content)
            elif event.type == "end":
                await websocket.send_text("[DONE]")
```

### CLI Typewriter Effect

```python
import time
from aicortex import chat

def typewriter(prompt: str, delay: float = 0.01):
    """Print streaming output with a subtle typewriter delay."""
    stream = chat(prompt, stream=True)
    for event in stream:
        if event.type == "token" and event.content:
            for char in event.content:
                print(char, end="", flush=True)
                time.sleep(delay)
    print()

typewriter("Write a one-paragraph description of the Milky Way.")
```

### Tkinter GUI (Non-Blocking)

```python
import tkinter as tk
import threading
from aicortex import chat

def stream_to_textbox(prompt: str, text_widget: tk.Text):
    """Stream AI output into a Tkinter Text widget from a background thread."""
    def run():
        stream = chat(prompt, stream=True)
        for event in stream:
            if event.type == "token" and event.content:
                # Schedule the UI update on the main thread
                text_widget.after(0, lambda t=event.content: (
                    text_widget.insert(tk.END, t),
                    text_widget.see(tk.END),
                ))
    threading.Thread(target=run, daemon=True).start()

# Usage
root = tk.Tk()
box = tk.Text(root, wrap=tk.WORD)
box.pack(expand=True, fill=tk.BOTH)
stream_to_textbox("Explain recursion with a simple analogy.", box)
root.mainloop()
```

## Best Practices

| ✅ Do | ❌ Avoid |
|---|---|
| Always use `flush=True` when printing tokens | Printing tokens without flush — they buffer silently |
| Check `event.type == "token"` before reading `event.content` | Reading `content` on `"start"` or `"end"` events without type check |
| Handle `"error"` events — don't assume clean completion | Ignoring error events and getting incomplete output |
| Use `stream.text()` for simple full-response collection | Re-implementing text collection manually when `.text()` exists |
| Run streaming in a background thread for GUI apps | Calling `chat(stream=True)` on the main thread in a GUI |

## Troubleshooting

**Tokens appear all at once instead of streaming**
→ Make sure you're passing `flush=True` to `print()`, or flushing your output buffer manually.

**Stream produces no tokens**
→ Check that the model name is valid (`models()`), and that at least one Ollama server is reachable (`list_model_servers(model)`).

**Output contains garbled characters**
→ Force UTF-8 output encoding:
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

**`RuntimeError: All servers failed`**
→ Every known Ollama server for that model was unreachable. Try a different model, run Ollama locally (`ollama serve`), or refresh the model database with the [Tools pipeline](tools.md).
