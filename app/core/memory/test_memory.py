"""CLI Test and Management Utility for Controlled AI Memory System (Phase 7)."""

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

from app.core.memory.manager import MemoryManager, memory_manager
from app.core.memory.privacy import SensitiveDataMemoryError


async def run_interactive_cli(manager: MemoryManager) -> None:
    """Interactive command-line interface for memory operations."""
    print("=" * 45)
    print("        myoneAI — AI Memory Test")
    print("=" * 45)

    while True:
        print("\n1. Add memory")
        print("2. Search memory")
        print("3. List all memories")
        print("4. Delete memory")
        print("5. Clear all memories")
        print("6. Test natural memory command")
        print("7. Exit\n")

        try:
            choice = input("Select an option (1-7): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting memory test.")
            break

        if choice == "1":
            cat = input("Category (preference/project/personal_context/instruction): ").strip() or "preference"
            key = input("Key (e.g. main_project, language_preference): ").strip()
            val = input("Value: ").strip()
            if not key or not val:
                print("[ERROR] Key and value cannot be empty.")
                continue
            try:
                item = await manager.remember(category=cat, key=key, value=val)
                print(f"[SUCCESS] Saved: {item.to_display_str()}")
            except SensitiveDataMemoryError as s_err:
                print(f"[PRIVACY REJECTION] {s_err}")

        elif choice == "2":
            q = input("Search query: ").strip()
            results = await manager.search(q)
            print(f"\nFound {len(results)} matches:")
            for r in results:
                print(f"  {r.to_display_str()} (Category: {r.category})")

        elif choice == "3":
            items = await manager.list_all()
            print(f"\nStored Memories ({len(items)} items):")
            for item in items:
                print(f"  {item.to_display_str()} [ID: {item.id[:8]}... | Cat: {item.category}]")

        elif choice == "4":
            key = input("Enter key or ID to delete: ").strip()
            deleted = await manager.delete(key=key)
            if not deleted:
                deleted = await manager.delete(item_id=key)
            print(f"[{'SUCCESS' if deleted else 'NOT FOUND'}] Deleted memory for '{key}'.")

        elif choice == "5":
            confirm = input("Are you sure you want to delete all memories? (yes/no): ").strip().lower()
            if confirm in ("yes", "y"):
                count = await manager.clear(confirmed=True)
                print(f"[SUCCESS] Cleared {count} memories.")
            else:
                print("[CANCELLED] Clear aborted.")

        elif choice == "6":
            cmd = input("Say something to JARVIS (e.g. 'Remember that my project is Vibrawave'): ").strip()
            resp = await manager.process_memory_command(cmd)
            if resp:
                print(f"\nJARVIS Memory Engine: {resp}")
            else:
                print("\n[INFO] Prompt not recognized as a direct memory command. (Would be passed to AI)")

        elif choice == "7":
            print("\nExiting memory test. Goodbye.")
            break
        else:
            print("Invalid selection. Please enter 1-7.")


async def run_demo_test(manager: MemoryManager) -> bool:
    """Run automated demo test verifying all memory operations."""
    print("=" * 50)
    print("myoneAI Memory Automated Verification (Phase 7)")
    print("=" * 50)

    # 1. Add preference
    print("\n1. Storing Language Preference: Tamil...")
    item1 = await manager.remember(category="preference", key="language_preference", value="Tamil")
    print(f"   Saved: {item1.to_prompt_str()}")

    # 2. Add project
    print("\n2. Storing Project Information: Vibrawave...")
    item2 = await manager.remember(category="project", key="main_project", value="Vibrawave")
    print(f"   Saved: {item2.to_prompt_str()}")

    # 3. Search
    print("\n3. Searching for 'project'...")
    results = await manager.search("project")
    assert len(results) >= 1
    print(f"   Match: {results[0].to_display_str()}")

    # 4. Context retrieval
    print("\n4. Building Context Prompt for query: 'What should I do on my project?'...")
    ctx = manager.get_context_for_prompt("What should I do on my project?")
    print(f"   Generated AI Prompt Context:\n{ctx}")
    assert "Vibrawave" in ctx

    # 5. Natural command parsing
    print("\n5. Testing Natural Language Memory Command: 'Remember that I prefer short answers'...")
    reply = await manager.process_memory_command("Remember that I prefer short answers")
    print(f"   Reply: {reply}")

    # 6. Privacy rejection
    print("\n6. Testing Sensitive Credential Rejection: 'my api_key is sk-12345678901234567890'...")
    try:
        await manager.remember(category="credential", key="api_key", value="sk-1234567890123456789012")
        print("   [FAIL] Privacy filter did not reject sensitive credential!")
        return False
    except SensitiveDataMemoryError:
        print("   [PASS] Sensitive credential safely rejected by privacy filter.")

    print("\nResult: AI Memory System [PASS]\n")
    return True


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="test_memory",
        description="myoneAI — Controlled AI Memory Test Utility",
    )
    parser.add_argument(
        "--demo",
        "-d",
        action="store_true",
        help="Run non-interactive automated verification demo",
    )

    args = parser.parse_args()
    if args.demo:
        success = asyncio.run(run_demo_test(memory_manager))
        sys.exit(0 if success else 1)
    else:
        asyncio.run(run_interactive_cli(memory_manager))


if __name__ == "__main__":
    main()
