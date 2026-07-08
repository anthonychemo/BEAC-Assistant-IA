# BEAC RAG Chatbot — Backend

Pipeline RAG hybride (texte + données chiffrées) sur les documents du site officiel de la **BEAC** (Banque des États de l'Afrique Centrale), scrapés et téléversés par le projet séparé `Scraping` vers un bucket **Cloudflare R2**.

- **LLM** : modèle gratuit via **OpenRouter** (`google/gemma-4-31b-it:free`, API compatible OpenAI, contexte 256K)
- **Embeddings** : `BAAI/bge-m3` (multilingue FR/EN/ES, CPU, local — gratuit)
- **Stockage des documents** : Cloudflare **R2** (PDF/Excel, avec metadata : lien source, module, section, date, type)
- **Base** : PostgreSQL + **pgvector** sur **Supabase**
- **OCR** : Tesseract (PDF scannés) + extraction native (PDF natifs)
- **API** : FastAPI (consommée par le frontend, développé séparément)

---

## Architecture

```
        Scraper (projet separe)
              │ upload direct, metadata attachee (lien, module, section, ...)
              ▼
        Cloudflare R2 (PDF/Excel)
              │ ingestion (scripts/ingest.py) : liste + telecharge en temp + supprime
        ┌─────┼──────────────────────────────┐
        ▼                                     ▼
  PDF natif (PyMuPDF) / PDF scanné      Excel (pandas)
  (Tesseract)                                 │
        └──────────────┬──────────────────────┘
                       ▼
                  chunking + BGE-M3 (local)      statistiques (format long)
                       │                                  │
                       ▼                                  ▼
            ┌────────────────────────────────────────────────────┐
            │      Supabase : PostgreSQL + pgvector               │
            │  documents · chunks(embedding) · statistics         │
            └────────────────────────────────────────────────────┘
                                   ▲
                                   │ retrieval hybride
              ┌────────────────────┴────────────────────┐
              │            Moteur RAG (engine.py)        │
              │  router → vector search + SQL → LLM      │
              │              (OpenRouter)                 │
              └────────────────────┬─────────────────────┘
                                   ▼
                          API FastAPI (/query)
```

---

## Prérequis (Windows 11)

1. **Python 3.11+**
2. Un projet **Supabase** avec l'extension `pgvector` activable (`create extension if not exists vector;`)
3. Un bucket **Cloudflare R2** (le même que celui utilisé par le projet `Scraping`)
4. **Tesseract OCR** — https://github.com/UB-Mannheim/tesseract/wiki
   (installer les langues `fra`, `eng`, `spa`)
5. **Poppler** (pour `pdf2image`) — https://github.com/oschwartz10612/poppler-windows/releases
   (décompresser et noter le chemin du dossier `Library\bin`)
6. Une clé **OpenRouter** (gratuite) — https://openrouter.ai/keys

---

## Installation

```powershell
# 1. Environnement Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configuration
copy .env.example .env
```

Éditer `.env` :
- `DATABASE_URL_OVERRIDE` : chaîne de connexion Supabase complète (Project Settings → Database → Connection string).
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` : identiques à celles utilisées par le projet `Scraping`.
- `OPENROUTER_API_KEY` : clé OpenRouter (https://openrouter.ai/keys).
- Chemins Tesseract/Poppler.

> Le premier lancement télécharge le modèle d'embedding `bge-m3` (~2 Go).

---

## Utilisation

```powershell
# 1. Créer le schéma sur Supabase (tables + index vectoriel)
python -m scripts.setup_db

# 2. Ingestion des données depuis R2 (long pour l'OCR — a lancer une fois)
python -m scripts.ingest --only excel        # commencer par les Excel (rapide)
python -m scripts.ingest --only pdf           # puis les PDF (OCR, lent)
# Options : --limit N (test)

# 3. Tester en CLI
python -m scripts.chat

# 4. Lancer l'API
python main.py
# Docs interactives : http://localhost:8000/docs
```

---

## Endpoints API

| Méthode | Route             | Description                              |
|---------|-------------------|------------------------------------------|
| GET     | `/health`         | État + comptes (documents, chunks, stats)|
| POST    | `/query`          | Question → réponse JSON + sources        |
| POST    | `/query/stream`   | Réponse en streaming (token par token)   |
| GET     | `/metadata`       | Catégories / pays / années (filtres UI)  |

Exemple :

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Resume la derniere decision de politique monetaire de la BEAC"}'
```

---

## Structure du projet

```
beac-rag-backend/
├── config/config.yaml          # Paramètres fonctionnels
├── .env.example                # Variables d'environnement
├── main.py                     # Lance l'API
├── requirements.txt
├── scripts/
│   ├── setup_db.py             # Crée tables + index HNSW
│   ├── ingest.py               # Ingestion des données
│   ├── warmup.py               # Prépare le client LLM au démarrage
│   ├── evaluate_rag.py         # Évaluation automatique (LLM judge)
│   └── chat.py                 # Chat CLI de test
└── src/
    ├── config/                 # Chargement .env + yaml
    ├── utils/                  # logger, détection métadonnées
    ├── database/                # connexion, schéma, vector_store
    ├── ingestion/               # pdf_processor, excel_processor, chunker, pipeline
    ├── indexing/                # embeddings (BGE-M3)
    ├── rag/                     # router, retriever, sql_generator, engine, llm_client
    └── api/                     # FastAPI (app, models)
```

---

## Notes de performance

- Le LLM tourne côté OpenRouter (modèle gratuit, rate-limité — ~20 req/min, ~200 req/jour) : pas de préchauffage local nécessaire, la latence dépend du réseau et de la charge du modèle gratuit.
- L'embedding (`bge-m3`) tourne en local sur CPU.
- L'OCR est l'étape la plus lente de l'ingestion : la lancer **une seule fois** en amont (les résultats sont persistés en base).
- Si la RAM sature pendant l'ingestion, réduire `embeddings.batch_size` et `ingestion.batch_size` dans `config.yaml`.
