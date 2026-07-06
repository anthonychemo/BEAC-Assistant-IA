"""Chat en ligne de commande pour tester le RAG.

Usage :
  python -m scripts.chat                          # Ollama (local)
  python -m scripts.chat --provider openrouter    # Gemma via OpenRouter
  python -m scripts.chat --provider openrouter --model mistral-7b
"""
from __future__ import annotations

import argparse
from src.rag.engine import answer_question


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="ollama", choices=["ollama", "openrouter"])
    parser.add_argument("--model", default="gemma-4-26b", dest="model_key")
    args = parser.parse_args()

    print(f"\n=== Chat BEAC RAG | provider={args.provider} model={args.model_key} ===")
    print("(tapez 'exit' pour quitter)\n")

    while True:
        try:
            question = input("Vous > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue

        result = answer_question(question, provider=args.provider, model_key=args.model_key)

        print(f"\n[type: {result.query_type}]")
        print(f"\nAssistant >\n{result.answer}\n")

        if result.sources:
            print("Sources :")
            for s in result.sources:
                print(f"  - {s['source']} ({s.get('year')})  score={s.get('score')}")
        if result.sql:
            print(f"\nSQL : {result.sql}")
        print()


if __name__ == "__main__":
    main()
