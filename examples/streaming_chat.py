# Streaming Chat Example

from aicortex import chat

def stream_example():
    """Demonstrate streaming chat responses."""
    stream = chat("Tell me a story about AI", stream=True)

    print("Streaming response:")
    for event in stream:
        if event.type == "token":
            print(event.content, end="", flush=True)
        elif event.type == "end":
            print("\n\nDone!")
        elif event.type == "error":
            print(f"\nError: {event.content}")

if __name__ == "__main__":
    stream_example()