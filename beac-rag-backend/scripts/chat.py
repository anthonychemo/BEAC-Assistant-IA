"""Chat CLI pour tester le RAG avec OpenRouter + mesure des temps.

Usage :
  python -m scripts.chat
  python -m scripts.chat --model mistral-7b
"""
from __future__ import annotations

import argparse
import time
from src.rag.engine import answer_question, _build_context
from src.rag.llm_client import DEFAULT_MODEL_KEY, OPENROUTER_MODELS, LLMClient
from src.rag.prompts import SYSTEM_PROMPT, build_rag_prompt
from src.indexing.embeddings import get_embedder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL_KEY, dest="model_key",
                        choices=list(OPENROUTER_MODELS.keys()))
    args = parser.parse_args()

    print(f"\n=== Chat BEAC RAG | modele={args.model_key} ({OPENROUTER_MODELS[args.model_key]}) ===")
    print("(tapez 'exit' pour quitter)\n")

    # Precharger l'embedder
    t0 = time.time()
    get_embedder()
    print(f"[init] Embedder charge en {time.time()-t0:.2f}s\n")

    while True:
        try:
            question = input("Vous > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue

        t_total = time.time()

        # Etape 1: embedding + retrieval
        t0 = time.time()
        from src.rag.query_router import classify_query
        from src.rag.retriever import retrieve_context
        from src.rag.sql_generator import format_sql_context, run_statistics_query
        from src.rag.retriever import format_context
        from src.rag.query_router import QueryType

        routed = classify_query(question)
        context_parts = []
        vector_items = []
        sql_used = None

        if routed.query_type in (QueryType.SQL, QueryType.HYBRID):
            sql_result = run_statistics_query(question)
            sql_used = sql_result.sql
            context_parts.append(format_sql_context(sql_result))

        if routed.query_type in (QueryType.VECTOR, QueryType.HYBRID):
            vector_items = retrieve_context(question)
            context_parts.append(format_context(vector_items))

        context = "\n\n".join(p for p in context_parts if p)
        t_retrieval = time.time() - t0
        print(f"  [retrieval] {t_retrieval:.2f}s — {len(vector_items)} chunks")

        # Etape 2: generation LLM
        t0 = time.time()
        prompt = build_rag_prompt(question, context)
        llm = LLMClient(model_key=args.model_key)
        answer = llm.generate(prompt, system=SYSTEM_PROMPT)
        t_llm = time.time() - t0
        print(f"  [LLM]       {t_llm:.2f}s")
        print(f"  [TOTAL]     {time.time()-t_total:.2f}s\n")

        print(f"Assistant >\n{answer}\n")

        if vector_items:
            print("Sources :")
            from src.rag.retriever import _sources_from_items
            for s in _sources_from_items(vector_items):
                print(f"  - {s['source']} ({s.get('year')})  score={s.get('score')}")
        print()


if __name__ == "__main__":
    main()
