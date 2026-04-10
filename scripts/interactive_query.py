#!/usr/bin/env python3
"""
Interactive query tester — ask questions against your knowledge base in real-time.

Usage:
    python scripts/interactive_query.py

Then just type questions and see answers!
"""

import sys
import logging

from infra.container import get_container
from infra.config import settings

logging.basicConfig(
    level=logging.WARNING,  # Suppress debug logs for cleaner output
)

logger = logging.getLogger(__name__)


def main():
    """Interactive query REPL."""

    print("\n" + "="*70)
    print("💬 Context Engine — Interactive Query Tester")
    print("="*70)
    print("""
You can now ask questions about your knowledge base!

Commands:
  • Type your question and press Enter
  • Type 'exit' or 'quit' to stop
  • Type 'lang en' or 'lang hi' to change language
  • Type 'clear' to clear screen

""")

    # Get services
    try:
        container = get_container()
        query_service = container["query_service"]
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        print("   Make sure your .env file is set up correctly")
        sys.exit(1)

    org_id = "shivaramgoud-org"  # You — the SME
    user_id = "you"
    company_name = "Your Organization"
    response_lang = "en"

    while True:
        try:
            # Get user input
            prompt = f"🤔 Question ({response_lang.upper()}): "
            user_input = input(prompt).strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["exit", "quit"]:
                print("\n👋 Goodbye!\n")
                break

            if user_input.lower() == "clear":
                import os
                os.system("clear" if os.name != "nt" else "cls")
                continue

            if user_input.lower().startswith("lang "):
                lang = user_input.split()[1].lower()
                if lang in ["en", "hi"]:
                    response_lang = lang
                    print(f"✅ Language set to {lang.upper()}\n")
                else:
                    print(f"❌ Unknown language: {lang} (try 'en' or 'hi')\n")
                continue

            # Process query
            print("\n⏳ Thinking...\n")

            result = query_service.query(
                user_id=user_id,
                org_id=org_id,
                query_text=user_input,
                company_name=company_name,
            )

            # Display answer
            print("="*70)
            print(f"✅ Answer:\n")
            print(result.answer)
            print()

            # Display citations
            if result.citations:
                print("📚 Sources:")
                for i, citation in enumerate(result.citations, 1):
                    print(f"  {i}. {citation['title']}")
                    print(f"     {citation['url']}")
                print()

            # Display timing
            print("⏱️ Performance:")
            print(f"  • Detect: {result.latency_ms['detect_ms']}ms")
            print(f"  • Translate: {result.latency_ms['translate_ms']}ms")
            print(f"  • Embed: {result.latency_ms['embed_ms']}ms")
            print(f"  • Retrieve: {result.latency_ms['retrieve_ms']}ms")
            print(f"  • Generate: {result.latency_ms['generate_ms']}ms")
            total = sum(result.latency_ms.values())
            print(f"  • Total: {total}ms")
            print("="*70)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break

        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logger.error(f"Query error: {e}")


if __name__ == "__main__":
    main()
