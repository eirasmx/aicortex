# OpenAI-Compatible Server Example

from aicortex.tools import run_server

def start_server():
    """Start the AI Cortex server with custom configuration."""
    print("Starting AI Cortex server...")
    print("OpenAI-compatible API will be available at http://localhost:8000")
    print("Use with OpenAI client:")
    print('  client = openai.OpenAI(base_url="http://localhost:8000/v1", api_key="dummy")')

    # Start server with custom settings
    run_server(
        host="127.0.0.1",
        port=8000,
        default_model="llama3.2:3b",
        reload=True  # Auto-reload on code changes
    )

if __name__ == "__main__":
    start_server()