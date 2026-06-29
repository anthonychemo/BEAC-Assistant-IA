# BEAC RAG Chatbot — Backend

Pipeline RAG hybride (texte + données chiffrées) sur les données scrappées du site officiel de la **BEAC** (Banque des États de l'Afrique Centrale).

- **LLM** : Llama 3.1 8B en local via **Ollama**
- **Embeddings** : `BAAI/bge-m3` (multilingue FR/EN/ES, CPU)
- **Base** : PostgreSQL 16 + **pgvector** (Docker)
- **OCR** : Tesseract (PDF scannés) + extraction native (PDF natifs)
- **API** : FastAPI (consommée par le frontend, développé séparément)

---

## Architecture

```
                ┌──────────────────────────────────────────────┐
                │              DONNEES BRUTES                  │
                │   PDF natifs · PDF scannés · Excel (.xls/x)  │
                └──────────────────────────────────────────────┘
                                   │ ingestion (scripts/ingest.py)
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
  PDF natif (PyMuPDF)        PDF scanné (Tesseract)      Excel (pandas)
        └──────────────┬───────────┘                          │
                       ▼                                       ▼
                  chunking + BGE-M3                  statistiques (format long)
                       │                                       │
                       ▼                                       ▼
            ┌────────────────────────────────────────────────────┐
            │      PostgreSQL + pgvector                          │
            │  documents · chunks(embedding) · statistics         │
            └────────────────────────────────────────────────────┘
                                   ▲
                                   │ retrieval hybride
              ┌────────────────────┴────────────────────┐
              │            Moteur RAG (engine.py)        │
              │  router → vector search + SQL → Llama 3.1 │
              └────────────────────┬─────────────────────┘
                                   ▼
                          API FastAPI (/query)
```

---

## Prérequis (Windows 11)

1. **Python 3.11+**
2. **Docker Desktop** (pour PostgreSQL + pgvector)
3. **Ollama** — https://ollama.com/download
4. **Tesseract OCR** — https://github.com/UB-Mannheim/tesseract/wiki
   (installer les langues `fra`, `eng`, `spa`)
5. **Poppler** (pour `pdf2image`) — https://github.com/oschwartz10612/poppler-windows/releases
   (décompresser et noter le chemin du dossier `Library\bin`)

---

## Installation

```powershell
# 1. Environnement Python
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Configuration
copy .env.example .env
# Editer .env : chemins Tesseract/Poppler, RAW_DATA_DIR, etc.

# 3. Base de données (Docker)
docker compose up -d

# 4. Modèle LLM
ollama pull llama3.1:8b-instruct-q4_K_M
```

> Le premier lancement télécharge le modèle d'embedding `bge-m3` (~2 Go).

---

## Utilisation

```powershell
# 1. Créer le schéma (tables + index vectoriel)
python -m scripts.setup_db

# 2. Ingestion des données (long pour l'OCR — à lancer une fois)
python -m scripts.ingest --only excel        # commencer par les Excel (rapide)
python -m scripts.ingest --only pdf           # puis les PDF (OCR, lent)
# Options : --limit N (test) · --path "C:/dossier"

# 3. Tester en CLI
python -m scripts.chat

# 4. Lancer l'API
python main.py
# Docs interactives : http://localhost:8000/docs
```

### Avant une démo live

```powershell
python -m scripts.warmup   # pré-charge Llama en RAM (réduit la latence)
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
├── docker-compose.yml          # PostgreSQL + pgvector
├── .env.example                # Variables d'environnement
├── main.py                     # Lance l'API
├── requirements.txt
├── scripts/
│   ├── init_db.sql             # Extensions pgvector (auto au 1er run Docker)
│   ├── setup_db.py             # Crée tables + index HNSW
│   ├── ingest.py               # Ingestion des données
│   ├── warmup.py               # Pré-charge le LLM
│   └── chat.py                 # Chat CLI de test
└── src/
    ├── config/                 # Chargement .env + yaml
    ├── utils/                  # logger, détection métadonnées
    ├── database/               # connexion, schéma, vector_store
    ├── ingestion/              # pdf_processor, excel_processor, chunker, pipeline
    ├── indexing/               # embeddings (BGE-M3)
    ├── rag/                    # router, retriever, sql_generator, engine, llm_client
    └── api/                    # FastAPI (app, models)
```

---

## Notes de performance (CPU sans GPU)

- Llama 3.1 8B Q4 tourne sur CPU : ~5-15 tokens/s. Le `warmup` + `keep_alive` réduisent la latence.
- L'OCR est l'étape la plus lente : la lancer **une seule fois** en amont (les résultats sont persistés en base).
- Si la RAM sature pendant l'ingestion, réduire `embeddings.batch_size` et `ingestion.batch_size` dans `config.yaml`.
```
