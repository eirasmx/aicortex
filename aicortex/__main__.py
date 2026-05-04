"""CLI entry point for AI Cortex.

Invoked via:

    python -m aicortex <subcommand> [options]
    aicortex <subcommand> [options]          # if console_script is registered

Subcommands
-----------
chat <prompt>       Send a prompt and print the response.
models              List available models, optionally filtered by family.
servers <model>     List all known servers for a given model.

Examples
--------
    aicortex chat "Explain neural networks in one sentence."
    aicortex chat "What is 2+2?" --model llama3.2:3b --stream
    aicortex chat "Hello" --system "You are a pirate."
    aicortex chat "Hi" --session my-session-id
    aicortex chat "Hi" --routing fastest
    aicortex models
    aicortex models --family gemma
    aicortex models --search "70b"
    aicortex servers llama3.2:3b
"""

from __future__ import annotations

import argparse
import sys


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def _cmd_chat(args: argparse.Namespace) -> None:
    """Handle `aicortex chat <prompt> [flags]`."""
    from aicortex import chat, Session

    # Build optional kwargs
    kwargs: dict = {
        "model": args.model,
        "stream": args.stream,
        "temperature": args.temperature,
        "routing": args.routing,
        "timeout": args.timeout,
    }

    if args.system:
        kwargs["system"] = args.system

    if args.session:
        # Validate session exists — chat() raises KeyError with a clear message if not
        kwargs["session"] = args.session

    try:
        result = chat(args.prompt, **kwargs)
    except KeyError as e:
        print(f"[aicortex] Session error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[aicortex] Argument error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"[aicortex] Server error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.stream:
        # Stream mode — print tokens incrementally as they arrive
        for event in result:
            if event.type == "token" and event.content:
                print(event.content, end="", flush=True)
        print()  # newline after stream ends
    else:
        print(result)


def _cmd_models(args: argparse.Namespace) -> None:
    """Handle `aicortex models [--family <name>] [--search <query>]`."""
    from aicortex import models, search_models, families

    if args.search:
        # search_models across all families with optional family scope
        results = search_models(
            args.search,
            family=args.family if args.family else None,
        )
        if not results:
            print(f"No models found matching '{args.search}'.")
            return
        print(f"Models matching '{args.search}':")
        for name in results:
            print(f"  {name}")
        return

    if args.family:
        result = models(args.family)
        if not result:
            available = ", ".join(families())
            print(
                f"No models found for family '{args.family}'. "
                f"Available families: {available}",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"Models in family '{args.family}':")
        for name in result:
            print(f"  {name}")
    else:
        # No filter — list all families and their counts
        all_families = families()
        if not all_families:
            print("No model families found.")
            return
        print("Available model families:\n")
        for fam in sorted(all_families):
            fam_models = models(fam)
            print(f"  {fam:<16} {len(fam_models)} models")
        print(f"\nTotal families: {len(all_families)}")
        print("Run `aicortex models --family <name>` to list models in a family.")
        print("Run `aicortex models --search <query>` to search across all families.")


def _cmd_servers(args: argparse.Namespace) -> None:
    """Handle `aicortex servers <model>`."""
    from aicortex import list_model_servers

    try:
        servers = list_model_servers(args.model)
    except Exception as e:
        print(f"[aicortex] Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not servers:
        print(f"No servers found for model '{args.model}'.")
        return

    print(f"Servers for '{args.model}' ({len(servers)} found):\n")
    # Column header
    print(f"  {'URL':<40} {'City':<18} {'Country':<18} {'TPS'}")
    print(f"  {'-'*40} {'-'*18} {'-'*18} {'-'*8}")

    for s in servers:
        url = s.get("url", "")
        loc = s.get("location", {})
        city = (loc.get("city") or "—")[:17]
        country = (loc.get("country") or "—")[:17]
        perf = s.get("performance", {})
        tps = perf.get("tokens_per_second")
        tps_str = f"{tps:.1f}" if tps is not None else "—"
        print(f"  {url:<40} {city:<18} {country:<18} {tps_str}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aicortex",
        description="🧠 AI Cortex — Free LLM access via community Ollama servers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  aicortex chat \"Explain AI in one sentence.\"\n"
            "  aicortex chat \"Hello\" --model llama3.2:3b --stream\n"
            "  aicortex chat \"Hi\" --routing fastest --timeout 10\n"
            "  aicortex chat \"Hi\" --session my-session\n"
            "  aicortex models\n"
            "  aicortex models --family gemma\n"
            "  aicortex models --search 70b\n"
            "  aicortex servers llama3.2:3b\n"
        ),
    )

    sub = parser.add_subparsers(dest="subcommand", metavar="<subcommand>")
    sub.required = True

    # ── chat ──────────────────────────────────────────────────────────────────
    chat_p = sub.add_parser(
        "chat",
        help="Send a prompt to a model.",
        description="Send a prompt to an Ollama model and print the response.",
    )
    chat_p.add_argument("prompt", help="The prompt to send to the model.")
    chat_p.add_argument(
        "--model", "-m",
        default="llama3.2:3b",
        metavar="MODEL",
        help="Model name (default: llama3.2:3b).",
    )
    chat_p.add_argument(
        "--stream", "-s",
        action="store_true",
        help="Stream tokens as they are generated.",
    )
    chat_p.add_argument(
        "--temperature", "-t",
        type=float,
        default=0.7,
        metavar="FLOAT",
        help="Sampling temperature 0.0–1.0 (default: 0.7).",
    )
    chat_p.add_argument(
        "--system",
        metavar="PROMPT",
        help="System prompt for this call (raw string, no file loading).",
    )
    chat_p.add_argument(
        "--session",
        metavar="ID",
        help=(
            "Session id for multi-turn memory. "
            "The session must already exist (created via Session() in Python). "
            "Raises an error if the id is not found."
        ),
    )
    chat_p.add_argument(
        "--routing",
        choices=["random", "fastest", "nearest"],
        default="random",
        help="Server selection strategy (default: random).",
    )
    chat_p.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="Seconds before abandoning a server attempt (default: 30.0).",
    )
    chat_p.set_defaults(func=_cmd_chat)

    # ── models ────────────────────────────────────────────────────────────────
    models_p = sub.add_parser(
        "models",
        help="List available models.",
        description=(
            "List all available model families and their models. "
            "Use --family to scope to one family, or --search to find models by name."
        ),
    )
    models_p.add_argument(
        "--family", "-f",
        metavar="FAMILY",
        help="Filter to a specific model family (e.g. gemma, llama, mistral).",
    )
    models_p.add_argument(
        "--search", "-s",
        metavar="QUERY",
        help="Search model names across all families (case-insensitive substring).",
    )
    models_p.set_defaults(func=_cmd_models)

    # ── servers ───────────────────────────────────────────────────────────────
    servers_p = sub.add_parser(
        "servers",
        help="List all servers hosting a model.",
        description="Show all known Ollama servers that host a specific model.",
    )
    servers_p.add_argument("model", help="Exact model name (e.g. llama3.2:3b).")
    servers_p.set_defaults(func=_cmd_servers)

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Main CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
