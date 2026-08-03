# BEAC-Assistant-IA

Chatbot RAG (Retrieval-Augmented Generation) assistant les utilisateurs sur les informations officielles de la **BEAC** (Banque des États de l'Afrique Centrale) : politique monétaire, statistiques économiques, réglementation, communiqués, etc.

## Arborescence réelle du projet

```
BEAC-Assistant-IA/
├─ beac-rag-backend/     # API FastAPI + pipeline RAG (voir son propre README)
├─ Frontend/             # Interface React/Vite/TypeScript
├─ beac_data/             # Corpus brut scrape (PDF/Excel), non versionne (.gitignore)
└─ README.md
```

> Ce README a été mis à jour pour refléter l'architecture réellement en place.
> L'ancienne version décrivait un backend Ollama local et des dossiers
> `Backend/`, `data_pipeline/` qui n'existent plus dans ce projet.

## Vue d'ensemble de l'architecture

- **Frontend** (`Frontend/`) : React 19 + Vite 6 + TypeScript. En développement, `npm run dev`
  lance Vite qui proxifie les appels `/api/*` vers le backend (`vite.config.ts`). En
  production, `npm start` lance un petit serveur Express (`server.ts`) qui sert le build
  et relaie lui-même `/api/*` vers `BACKEND_URL` (voir `Frontend/.env.example`).
- **Backend** (`beac-rag-backend/`) : API FastAPI exposant le moteur RAG. LLM via
  **OpenRouter** (modèle gratuit, plus de dépendance à Ollama/GPU local), embeddings
  **BGE-M3** en local (CPU), base **PostgreSQL + pgvector** (Supabase), documents source
  stockés sur **Cloudflare R2**. Voir `beac-rag-backend/README.md` pour l'installation
  complète, la liste des endpoints et le détail du pipeline.
- **`beac_data/`** : corpus brut issu du scraping du site beac.int (PDF, Excel, Word),
  organisé par rubrique. **Ce dossier n'est pas branché sur le pipeline d'ingestion** :
  `scripts/ingest.py` (dans `beac-rag-backend/`) lit exclusivement depuis le bucket
  Cloudflare R2, pas depuis le disque local. Pour indexer ce corpus, il faut d'abord
  téléverser ces fichiers vers le bucket R2 configuré (`R2_BUCKET_NAME` dans `.env`),
  avec la métadonnée objet attendue par le scraper (`lien`, `module`, `section`,
  `nom_pdf`, `date_publication`, `type_document` — voir `src/ingestion/r2_client.py`).
  Ce dossier est volumineux (plusieurs Go) et exclu de `.gitignore`.

## Démarrage rapide

### Backend

Voir `beac-rag-backend/README.md` pour la procédure complète (Python, Supabase,
Tesseract/Poppler, variables d'environnement). En résumé :

```powershell
cd beac-rag-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # puis renseigner les vraies valeurs
python -m scripts.setup_db
python main.py            # API sur http://localhost:8000
```

### Frontend

```powershell
cd Frontend
npm install
copy .env.example .env    # PORT / BACKEND_URL (utilisés seulement par npm start en prod)
npm run dev                # http://localhost:5173, proxy vers le backend sur :8000
```

## Notes

- Le CORS du backend est restreint aux origines listées dans `CORS_ALLOW_ORIGINS`
  (`beac-rag-backend/.env`) — ajouter l'URL de production quand elle existe.
- La route `POST /cache/clear` est protégée par un jeton (`ADMIN_API_TOKEN` +
  header `X-Admin-Token`) ; elle est désactivée tant que ce jeton n'est pas configuré.
- Le sélecteur de modèle dans l'assistant reflète les modèles réellement configurés
  côté backend (`config/config.yaml` → `llm.model` / `llm.fallback_model`), exposés
  via `GET /metadata`.
