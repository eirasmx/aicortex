# Tools Usage Example

from pathlib import Path
from aicortex.tools import (
    find_valid_endpoints,
    fetch_models,
    resolve_models,
    apply_valid_models
)

def update_models_workflow():
    """Complete workflow to update model database."""
    models_dir = Path("aicortex/models")

    print("Step 1: Finding valid endpoints...")
    valid_urls = find_valid_endpoints(models_dir)
    print(f"Found {len(valid_urls)} valid endpoints")

    # Save URLs to file
    urls_file = Path("valid_endpoints.txt")
    with open(urls_file, "w") as f:
        f.write("\n".join(valid_urls))

    print("Step 2: Fetching current models...")
    fetched_file = Path("fetched_models.json")
    fetch_models(urls_file, fetched_file)
    print("Models fetched successfully")

    print("Step 3: Resolving model data...")
    resolved_file = Path("resolved_models.json")
    resolve_models(fetched_file, models_dir, resolved_file)
    print("Models resolved successfully")

    print("Step 4: Applying to package...")
    created_files = apply_valid_models(resolved_file, models_dir, backup=True)
    print(f"Created {len(created_files)} model files")

    # Cleanup
    urls_file.unlink(missing_ok=True)
    fetched_file.unlink(missing_ok=True)
    resolved_file.unlink(missing_ok=True)

    print("Model update complete!")

if __name__ == "__main__":
    update_models_workflow()