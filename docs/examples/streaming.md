# ⚡ Streaming Examples

> **Annotated examples for real-time token streaming** — terminal output, progress display,
> word-by-word collection, error handling, and integration patterns for web and CLI apps.

See the [Streaming Guide](../streaming.md) for the full `Stream` and `StreamEvent` reference.

## The Essential Pattern

```python
from aicortex import chat

stream = chat("Explain how neural networks learn.", stream=True)

for event in stream:
    if event.type == "token":
        print(event.content, end="", flush=True)

print()  # newline after the stream ends
```

> **Always pass `flush=True`** — Python buffers stdout by default.
> Without it, tokens accumulate silently and print all at once when the
> stream ends, which defeats the entire point of streaming.

## Handling All Event Types

A stream emits four event types. Production code should handle all of them:

```python
from aicortex import chat
from aicortex.chat import EventType

stream = chat("Write a haiku about fog.", stream=True)

for event in stream:
    if event.type == EventType.START:
        print("[generation started]")

    elif event.type == EventType.TOKEN:
        print(event.content, end="", flush=True)

    elif event.type == EventType.END:
        print("\n[generation complete]")

    elif event.type == EventType.ERROR:
        print(f"\n[error: {event.content}]")
```

| Event type | When it fires | `content` field |
|---|---|---|
| `START` | Once, immediately when generation begins | `None` |
| `TOKEN` | Once per generated token | The token text |
| `END` | Once, when generation completes successfully | `None` |
| `ERROR` | If the server fails mid-stream | Error description |

## Collecting the Full Text

If you need to iterate events for side effects (display, logging) AND keep the
full response as a string, use `Stream.text()` after iterating:

```python
from aicortex import chat

stream = chat("What are the planets of the solar system?", stream=True)

# Print tokens as they arrive
for event in stream:
    if event.type == "token":
        print(event.content, end="", flush=True)
print()

# Get the complete text after the stream finishes
full_response = stream.text()
print(f"\n[Total characters: {len(full_response)}]")
```

`Stream.text()` concatenates all `TOKEN` event content in order. It works
correctly even before the stream finishes (gives partial text up to that point).

## Word-by-Word Display

For a typewriter effect that respects word boundaries instead of raw tokens:

```python
import time
from aicortex import chat

stream = chat("Describe a forest at dawn.", stream=True)

buffer = ""
for event in stream:
    if event.type == "token":
        buffer += event.content
        # Flush complete words (split on spaces)
        words = buffer.split(" ")
        for word in words[:-1]:
            print(word, end=" ", flush=True)
            time.sleep(0.04)  # pacing — adjust to taste
        buffer = words[-1]  # keep the partial word

# Flush remainder
if buffer:
    print(buffer, flush=True)
print()
```

## Streaming with a Spinner

For long-running generations, show a spinner while waiting for the first token:

```python
import sys
import threading
import itertools
from aicortex import chat

def spinning_stream(prompt: str, model: str = "llama3.2:3b") -> str:
    spinner = itertools.cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
    first_token_received = threading.Event()

    def spin():
        while not first_token_received.is_set():
            sys.stdout.write(f"\r{next(spinner)} Thinking...")
            sys.stdout.flush()
            threading.Event().wait(0.1)
        sys.stdout.write("\r" + " " * 20 + "\r")  # clear spinner line
        sys.stdout.flush()

    spin_thread = threading.Thread(target=spin, daemon=True)
    spin_thread.start()

    stream = chat(prompt, model=model, stream=True)
    result = []

    for event in stream:
        if event.type == "token":
            if not first_token_received.is_set():
                first_token_received.set()
            print(event.content, end="", flush=True)
            result.append(event.content)

    spin_thread.join()
    print()
    return "".join(result)


response = spinning_stream("Explain the Riemann hypothesis.")
print(f"\n[{len(response)} chars]")
```

## Streaming in a CLI Chat Loop

Combine streaming with a REPL for a responsive terminal chat:

```python
from aicortex import chat
from aicortex.chat import EventType

print("AI Cortex Chat  (Ctrl+C to quit)\n")

while True:
    try:
        user_input = input("You: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
        break

    if not user_input:
        continue

    print("Assistant: ", end="", flush=True)

    try:
        stream = chat(user_input, model="llama3.2:3b", stream=True)
        for event in stream:
            if event.type == EventType.TOKEN:
                print(event.content, end="", flush=True)
            elif event.type == EventType.ERROR:
                print(f"[error: {event.content}]", end="")
    except Exception as e:
        print(f"[{e}]", end="")

    print("\n")
```

## Streaming to a File

```python
from aicortex import chat

output_path = "response.txt"

with open(output_path, "w") as f:
    stream = chat(
        "Write a 500-word essay on open-source software.",
        model="mistral:7b",
        stream=True,
    )
    for event in stream:
        if event.type == "token":
            f.write(event.content)
            f.flush()  # ensure tokens hit disk as they arrive

print(f"Saved to {output_path}")
```

## Streaming Error Handling

```python
from aicortex import chat
from aicortex.chat import EventType
from aicortex.exceptions import ModelNotFoundError, ServerError

def resilient_stream(prompt: str) -> str:
    """Stream a response, falling back to a default model on error."""
    models_to_try = ["llama3.2:3b", "mistral:7b", "gemma:2b"]

    for model in models_to_try:
        try:
            stream = chat(prompt, model=model, stream=True)
            tokens = []
            errored = False

            for event in stream:
                if event.type == EventType.TOKEN:
                    print(event.content, end="", flush=True)
                    tokens.append(event.content)
                elif event.type == EventType.ERROR:
                    print(f"\n[stream error on {model}, trying next...]")
                    errored = True
                    break

            if not errored:
                print()
                return "".join(tokens)

        except (ModelNotFoundError, ServerError) as e:
            print(f"[{model} unavailable: {e}, trying next...]")
            continue

    return "[all models failed]"


result = resilient_stream("Summarize the history of the internet.")
```

## Async Streaming (asyncio)

AI Cortex's current `chat()` is synchronous. To use it in an async context
without blocking the event loop, run it in a thread pool:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from aicortex import chat
from aicortex.chat import EventType

executor = ThreadPoolExecutor(max_workers=4)

async def async_stream(prompt: str, model: str = "llama3.2:3b") -> str:
    """Run a streaming chat in a thread pool, yield tokens via asyncio queue."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    def _stream_worker():
        stream = chat(prompt, model=model, stream=True)
        for event in stream:
            if event.type == EventType.TOKEN:
                loop.call_soon_threadsafe(queue.put_nowait, event.content)
        loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

    loop.run_in_executor(executor, _stream_worker)

    tokens = []
    while True:
        token = await queue.get()
        if token is None:
            break
        print(token, end="", flush=True)
        tokens.append(token)

    print()
    return "".join(tokens)


async def main():
    response = await async_stream("What is asyncio?")
    print(f"\n[{len(response)} chars received]")

asyncio.run(main())
```

> **Note** — a native `async def chat()` API is planned for a future release.
> The thread pool pattern above is the correct bridge in the meantime.

## See Also

- [Streaming Guide](../streaming.md) — `StreamEvent` anatomy and all event types
- [API Reference — chat()](../api.md#chat) — full parameter documentation
- [Chat Examples](chat.md) — non-streaming patterns
