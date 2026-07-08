"""Évaluation automatique du pipeline RAG.

Génère un jeu de questions-réponses à partir de chunks aléatoires de la base,
puis exécute le RAG et évalue la qualité des réponses avec un LLM judge.

Usage:
    (.venv) $ python -m scripts.evaluate_rag --samples 50 --output results/eval.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import time
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.config import CONFIG, settings
from src.database.schema import Chunk, Document
from src.database.vector_store import engine
from src.rag.engine import RAGResponse, answer_question
from src.rag.llm_client import get_llm
from src.utils.logger import logger


_JUDGE_SYSTEM = (
    "Tu es un évaluateur strict. Tu dois noter la réponse d'un système RAG "
    "sur la base du contexte fourni et de la réponse attendue. "
    "Réponds uniquement par un JSON avec 3 entiers entre 1 et 5."
)

_JUDGE_PROMPT = """Contexte pertinent :
{context}

Question : {question}
Réponse attendue : {expected_answer}
Réponse générée : {generated_answer}

Évalue selon les critères suivants (1 = très mauvais, 5 = excellent) :
- context_recall : le contexte pertinent est-il présent dans les sources récupérées ?
- faithfulness : la réponse générée est-elle fidèle au contexte ? Pas d'hallucination.
- answer_relevance : la réponse répond-elle directement à la question ?

Réponds uniquement par ce format JSON, sans explication :
{{"context_recall": X, "faithfulness": Y, "answer_relevance": Z}}"""


def _parse_judge_response(text: str) -> dict[str, int]:
    """Extrait les scores JSON du judge."""
    text = text.strip()
    # Enlève les éventuels blocs markdown
    if text.startswith("```"):
        text = text.split("```")[1].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    # Fallback : cherche un bloc JSON entre accolades
    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    try:
        parsed = json.loads(text)
        return {
            "context_recall": int(parsed.get("context_recall", 0)),
            "faithfulness": int(parsed.get("faithfulness", 0)),
            "answer_relevance": int(parsed.get("answer_relevance", 0)),
        }
    except Exception:
        return {"context_recall": 0, "faithfulness": 0, "answer_relevance": 0}


def generate_qa_pair(chunk: Chunk, doc: Document) -> dict[str, Any]:
    """Génère une question et une réponse courte à partir d'un chunk."""
    system = (
        "Tu es un assistant spécialisé en économie et finance de la BEAC et de la CEMAC. "
        "Tu dois créer une question factuelle en français à partir du texte fourni. "
        "Réponds uniquement par un JSON avec les clés 'question' et 'expected_answer'."
    )
    prompt = (
        f"Document : {doc.filename}\n"
        f"Catégorie : {doc.category or 'inconnue'}\n"
        f"Pays : {doc.country or 'inconnu'}\n"
        f"Année : {doc.year or 'inconnue'}\n\n"
        f"Extrait du document :\n{chunk.content}\n\n"
        "Crée une question factuelle en français dont la réponse se trouve explicitement "
        "dans l'extrait ci-dessus. Fournis aussi une réponse courte (1 phrase).\n"
        "Réponds uniquement par ce format JSON :\n"
        '{"question": "...", "expected_answer": "..."}'
    )
    response = get_llm().generate(prompt, system=system)
    try:
        parsed = json.loads(response)
        return {
            "question": parsed["question"],
            "expected_answer": parsed["expected_answer"],
            "chunk_id": chunk.id,
            "document_id": doc.id,
            "filename": doc.filename,
            "category": doc.category,
            "country": doc.country,
            "year": doc.year,
            "chunk_content": chunk.content,
        }
    except Exception as exc:
        logger.warning(f"Échec génération QA pour chunk {chunk.id} : {exc}")
        return {}


def evaluate_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Exécute le RAG et évalue le résultat."""
    question = sample["question"]
    logger.info(f"Évaluation question : {question[:80]}")

    rag_response: RAGResponse = answer_question(question)
    context = rag_response.context_used
    generated_answer = rag_response.answer

    judge_prompt = _JUDGE_PROMPT.format(
        context=context,
        question=question,
        expected_answer=sample["expected_answer"],
        generated_answer=generated_answer,
    )
    judge_text = get_llm().generate(judge_prompt, system=_JUDGE_SYSTEM)
    scores = _parse_judge_response(judge_text)

    return {
        **sample,
        "generated_answer": generated_answer,
        "query_type": rag_response.query_type,
        "context_used": context,
        "context_recall": scores["context_recall"],
        "faithfulness": scores["faithfulness"],
        "answer_relevance": scores["answer_relevance"],
        "sources": json.dumps(
            [
                {
                    "source": s.get("source"),
                    "category": s.get("category"),
                    "year": s.get("year"),
                    "score": s.get("score"),
                }
                for s in (rag_response.sources or [])
            ],
            ensure_ascii=False,
        ),
    }


def fetch_random_chunks(n_samples: int) -> list[tuple[Chunk, Document]]:
    """Récupère N chunks aléatoires avec leur document."""
    with Session(engine) as session:
        stmt = (
            select(Chunk, Document)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.content.isnot(None))
            .where(func.length(Chunk.content) > 200)
            .order_by(func.random())
            .limit(n_samples)
        )
        return list(session.execute(stmt).all())


def run_evaluation(n_samples: int, output_csv: Path) -> None:
    """Pipeline complet : génération QA + évaluation RAG + rapport."""
    logger.info(f"Récupération de {n_samples} chunks aléatoires...")
    rows = fetch_random_chunks(n_samples)
    logger.info(f"{len(rows)} chunks récupérés")

    if not rows:
        logger.error("Aucun chunk trouvé en base. Abandon.")
        return

    results: list[dict[str, Any]] = []
    qa_pairs: list[dict[str, Any]] = []

    logger.info("Génération des questions-réponses...")
    for chunk, doc in rows:
        qa = generate_qa_pair(chunk, doc)
        if qa:
            qa_pairs.append(qa)

    logger.info(f"{len(qa_pairs)} paires QA générées. Évaluation RAG...")
    for sample in qa_pairs:
        try:
            evaluated = evaluate_sample(sample)
            results.append(evaluated)
            time.sleep(0.5)   # laisse le CPU refroidir entre les appels LLM
        except Exception as exc:
            logger.error(f"Échec évaluation pour sample {sample.get('chunk_id')} : {exc}")

    if not results:
        logger.error("Aucun résultat d'évaluation. Abandon.")
        return

    # Sauvegarde CSV
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "chunk_id",
        "document_id",
        "filename",
        "category",
        "country",
        "year",
        "question",
        "expected_answer",
        "generated_answer",
        "query_type",
        "context_recall",
        "faithfulness",
        "answer_relevance",
        "sources",
        "context_used",
        "chunk_content",
    ]
    def _clean_csv_value(value: Any) -> str:
        if value is None:
            return ""
        s = str(value)
        # Remplace les sauts de ligne pour garder une ligne par ligne CSV
        s = s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        return s

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: _clean_csv_value(r.get(k, "")) for k in fieldnames})

    # Rapport synthétique
    metrics = {
        "context_recall": [r["context_recall"] for r in results],
        "faithfulness": [r["faithfulness"] for r in results],
        "answer_relevance": [r["answer_relevance"] for r in results],
    }
    summary = {
        "total_samples": len(results),
        "avg_context_recall": round(sum(metrics["context_recall"]) / len(results), 2),
        "avg_faithfulness": round(sum(metrics["faithfulness"]) / len(results), 2),
        "avg_answer_relevance": round(sum(metrics["answer_relevance"]) / len(results), 2),
    }
    summary["avg_global"] = round(
        (summary["avg_context_recall"] + summary["avg_faithfulness"] + summary["avg_answer_relevance"]) / 3,
        2,
    )

    summary_path = output_csv.with_suffix(".json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("=" * 60)
    logger.info(f"Évaluation terminée : {len(results)} samples")
    logger.info(f"CSV  : {output_csv}")
    logger.info(f"JSON : {summary_path}")
    logger.info("Scores moyens :")
    logger.info(f"  Context recall    : {summary['avg_context_recall']:.2f} / 5")
    logger.info(f"  Faithfulness      : {summary['avg_faithfulness']:.2f} / 5")
    logger.info(f"  Answer relevance  : {summary['avg_answer_relevance']:.2f} / 5")
    logger.info(f"  Global            : {summary['avg_global']:.2f} / 5")
    logger.info("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Évaluation automatique du RAG BEAC")
    parser.add_argument("--samples", type=int, default=20, help="Nombre de questions à générer")
    parser.add_argument("--output", type=str, default="results/eval.csv", help="Chemin du CSV de résultats")
    parser.add_argument("--seed", type=int, default=42, help="Seed pour la reproductibilité")
    args = parser.parse_args()

    random.seed(args.seed)
    run_evaluation(args.samples, Path(args.output))


if __name__ == "__main__":
    main()
