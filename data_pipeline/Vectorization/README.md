# Vectorisation BEAC Assistant

Ce dossier contient le code d'import et de stockage des chunks en base PostgreSQL + pgvector.

- `ingest_to_pgvector.py` : script qui crée les embeddings Ollama et importe les chunks dans la table `beac_documents`.

## Lancement

```bash
cd data_pipeline/Vectorization
python ingest_to_pgvector.py --source-dir "../Scrapping/scraping/beac_text"
```

## Architecture

- Scraping : `data_pipeline/Scrapping`
- Chunking : `data_pipeline/Chunking`
- Vectorization : `data_pipeline/Vectorization`
