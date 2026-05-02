# Model Management Example

from aicortex import families, models, get_model_info

def explore_models():
    """Explore available models and their information."""
    print("Available families:")
    for family in families():
        print(f"  - {family}")

    print("\nAll models:")
    for model in models():
        print(f"  - {model}")

    print("\nLlama models:")
    for model in models("llama"):
        print(f"  - {model}")

    # Get detailed info for a specific model
    try:
        info = get_model_info("llama3.2:3b")
        print(f"\nModel info for llama3.2:3b:")
        for key, value in info.items():
            print(f"  {key}: {value}")
    except ValueError as e:
        print(f"Model info error: {e}")

if __name__ == "__main__":
    explore_models()