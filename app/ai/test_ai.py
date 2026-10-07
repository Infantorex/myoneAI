"""Interactive CLI test utility for the AI Conversation Engine.

Enables multi-turn conversational testing with Tamil, English, and mixed Tanglish.
"""

import argparse
import asyncio
import sys

# Configure UTF-8 for Windows terminals
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

from app.ai.errors import AIError
from app.ai.manager import ConversationManager
from app.ai.provider import get_ai_provider
from app.core.config import get_settings


async def run_ai_cli(provider_name: str = None, model: str = None) -> None:
    """Run interactive terminal chat loop."""
    settings = get_settings()
    selected_provider_name = provider_name or settings.ai_provider

    try:
        provider = get_ai_provider(selected_provider_name)
        if model:
            provider.model = model
        manager = ConversationManager(provider=provider)
    except Exception as exc:
        print(f"[FAIL] Could not initialize AI provider '{selected_provider_name}': {exc}")
        return

    print("=" * 60)
    print("         myoneAI — AI Conversation Test (Phase 4)")
    print("=" * 60)
    print(f"Provider : {selected_provider_name}")
    print(f"Model    : {getattr(provider, 'model', 'default')}")
    print("Type your message in Tamil, Tanglish, or English.")
    print("Type 'exit' or 'quit' to end session.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("You:\n> ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("\nSession ended. Exiting...")
                break

            print("\nJARVIS:")
            reply = await manager.respond(user_input)
            print(f"> {reply}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nSession interrupted. Exiting...")
            break
        except AIError as ai_err:
            print(f"\n[AI Error]: {ai_err}\n")
        except Exception as exc:
            print(f"\n[Error]: {exc}\n")


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="test_ai",
        description="myoneAI — AI Conversation Test Utility",
    )
    parser.add_argument(
        "--provider",
        "-p",
        type=str,
        default=None,
        help="AI provider override (gemini, openai, mock)",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Model name override (e.g. gemini-1.5-flash)",
    )

    args = parser.parse_args()
    asyncio.run(run_ai_cli(provider_name=args.provider, model=args.model))


if __name__ == "__main__":
    main()
