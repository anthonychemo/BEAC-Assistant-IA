# Ingestion sur machine GPU (10 Go VRAM)

Procédure pour basculer le pipeline d'embeddings sur GPU et lancer
l'ingestion complète des ~4972 PDF beaucoup plus rapidement (10-20x).

> En local (CPU), garder `EMBEDDING_DEVICE=cpu`. Cette procédure ne concerne
> que la machine cible équipée d'un GPU NVIDIA.

---

## 1. Pré-requis (machine cible)

- GPU NVIDIA avec **10 Go de VRAM**
- Pilote NVIDIA à jour (`nvidia-smi` doit fonctionner)
- Python 3.11 + venv comme en local
- PostgreSQL + pgvector installés et accessibles
- Ollama installé avec le modèle `llama3.1:8b-instruct-q4_K_M`
- Tesseract + Poppler installés (chemins à ajuster dans `.env`)

Vérifier le pilote :
```powershell
nvidia-smi
```

---

## 2. Installer torch en version CUDA

Le `torch` installé en local est la build **CPU** (`+cpu`). Sur la machine GPU,
il faut le remplacer par une build CUDA. Choisir la version CUDA selon le pilote
(`nvidia-smi` affiche la version CUDA max supportée en haut à droite).

```powershell
# Desinstaller la version CPU existante
pip uninstall -y torch

# Installer la build CUDA (CUDA 12.4 ; adapter si besoin : cu121, cu118, etc.)
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Vérifier que CUDA est bien détecté :
```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Sortie attendue (exemple) :
```
2.6.0+cu124 True NVIDIA GeForce RTX ...
```
Si `torch.cuda.is_available()` renvoie `False`, la build CUDA n'est pas bien
installée ou le pilote est incompatible : ne pas continuer.

---

## 3. Activer le GPU dans la configuration

Dans `.env` (machine cible) :
```ini
EMBEDDING_DEVICE=cuda
```

Le mode offline HuggingFace reste actif par défaut (cf. `src/indexing/embeddings.py`).
Si le modèle BGE-M3 n'est PAS encore en cache sur cette machine, il faut le
télécharger une première fois en autorisant le réseau :
```powershell
$env:HF_HUB_OFFLINE=0
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```
Ensuite il sera servi depuis le cache local (plus besoin de réseau).

---

## 4. Budget VRAM (10 Go)

| Composant            | VRAM approx. |
|----------------------|--------------|
| BGE-M3 (embeddings)  | ~2 Go        |
| Llama 3.1 8B q4_K_M  | ~5-6 Go      |
| Marge / overhead     | ~1-2 Go      |

Les deux tiennent dans 10 Go. Pour l'**ingestion**, seul BGE-M3 est utilisé
(Ollama n'est sollicité qu'au moment des requêtes). On peut donc augmenter
le débit d'embeddings sans risque OOM pendant l'ingestion.

### Optionnel : augmenter le batch d'embeddings sur GPU
Dans `config/config.yaml`, section `embeddings` :
```yaml
embeddings:
  batch_size: 64   # 16 par defaut (CPU) ; 64-128 possible sur GPU 10 Go
```

---

## 5. Lancer l'ingestion complète

L'ingestion est **idempotente** (les fichiers déjà traités sont ignorés) et
**atomique** (un échec ne laisse pas de document orphelin). On peut donc
l'interrompre (Ctrl+C) et la relancer sans perte.

```powershell
# Test de fumee : quelques fichiers
python -m scripts.ingest --only pdf --limit 10

# Ingestion complete (PDF + Excel)
python -m scripts.ingest
```

Suivre l'avancement via la barre de progression et `logs/pipeline_*.log`.

---

## 6. Vérifications post-ingestion

```sql
-- Repartition par methode d'extraction
SELECT extraction_method, COUNT(*) FROM documents GROUP BY extraction_method;

-- Documents sans chunk (doit etre VIDE grace a l'atomicite)
SELECT d.id, d.filename
FROM documents d
LEFT JOIN chunks c ON c.document_id = d.id
WHERE c.id IS NULL;
```

Comptes globaux via l'API :
```powershell
# Apres demarrage de l'API
curl http://localhost:8000/health
```

---

## 7. Retour en local (CPU)

Sur la machine de dev sans GPU, garder dans `.env` :
```ini
EMBEDDING_DEVICE=cpu
```
Le code détecte le device via cette variable ; aucun changement de code requis.
