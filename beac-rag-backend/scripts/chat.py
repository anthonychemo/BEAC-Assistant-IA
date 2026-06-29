"""Chat en ligne de commande pour tester le RAG sans frontend.

Usage : python -m scripts.chat
"""
from __future__ import annotations

from src.rag.engine import answer_question


def main() -> None:
    print("=== Chat BEAC RAG (tapez 'exit' pour quitter) ===")
    while True:
        try:
            question = input("\nVous > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue
        result = answer_question(question)
        print(f"\n[type: {result.query_type}]")
        print(f"Assistant > {result.answer}")
        if result.sources:
            print("\nSources :")
            for s in result.sources:
                print(f"  - {s['source']} ({s.get('year')})  score={s.get('score')}")
        if result.sql:
            print(f"\nSQL : {result.sql}")


if __name__ == "__main__":
    main()
