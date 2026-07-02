# BEAC-Assistant-IA
Conception et implémentation d'une architecture RAG d'un chatbot permettant d'assister les utilisateurs sur les informations du site officiel de la BEAC.

## Architecture du projet

Voici l'arborescence principale :

```
BEAC-Assistant-IA/
├─ Backend/
│  ├─ main.py
│  ├─ requirements.txt
│  └─ README.md
├─ Frontend/
│  ├─ server.ts
│  ├─ package.json
│  └─ vite.config.ts
├─ data_pipeline/
│  ├─ Scrapping/
│  │  ├─ scraper.py
│  │  ├─ test_connexion.py
│  │  ├─ requirements.txt
│  │  └─ README.md
│  ├─ Chunking/
│  │  ├─ chunking.py
│  │  └─ README.md
│  └─ Vectorization/
│     ├─ ingest_to_pgvector.py
│     └─ README.md
├─ .env.example
└─ README.md
```

## Pipeline RAG local

Ce projet utilise :
- Scraping de la BEAC dans `data_pipeline/Scrapping`
- Chunking du texte dans `data_pipeline/Chunking`
- Vectorisation et import en base dans `data_pipeline/Vectorization`
- Backend Python FastAPI dans `Backend/main.py` pour la recherche RAG
- Frontend React/Vite dans `Frontend/` avec proxy vers FastAPI en développement

## Étapes d'installation sur Windows

1. Installer PostgreSQL pour Windows.
   - Téléchargez l'installateur officiel depuis https://www.postgresql.org/download/windows/
   - Installez PostgreSQL et activez l'option `Stack Builder` pour les extensions.

2. Installer l'extension `pgvector`.
   - Ouvrez `psql` ou `pgAdmin`.
   - Lancez :
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Si l'extension n'est pas disponible, utilisez Stack Builder ou installez `pgvector` depuis GitHub :
     https://github.com/pgvector/pgvector

3. Créer la base de données :
   ```psql
   CREATE DATABASE beac_rag;
   ```

4. Configurer les variables d'environnement.
   - Dupliquez `.env.example` en `.env` à la racine du projet.
   - Ajustez `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL`.

5. Installer les dépendances Python pour l'ingestion :
   ```bash
   cd data_pipeline/Scrapping
   python -m pip install -r requirements.txt
   ```

6. Exécuter le script d'indexation :
   ```bash
   python ingest_to_pgvector.py --source-dir "scraping/beac_text"
   ```

7. Installer les dépendances Node du frontend :
   ```bash
   cd Frontend
   npm install
   ```

8. Lancer le serveur local :
   ```bash
   npm run dev
   ```

## Notes

- Le backend de `Frontend/server.ts` utilise `ollama embed` pour créer les embeddings et `ollama run` pour répondre aux prompts.
- Si `ollama` n'est pas sur le PATH Windows, ajoutez-le ou utilisez une invite de commandes où `ollama` fonctionne.
- La table PostgreSQL `beac_documents` est créée automatiquement avec la dimension d'embedding détectée par le script.
