# 🏗️ Architecture - Exploitation des PDFs BEAC

## 📐 Vue Globale du Système

```
┌─────────────────────────────────────────────────────────────────┐
│                    BEAC DOCUMENT PIPELINE v2.0                  │
└─────────────────────────────────────────────────────────────────┘

PHASE 1: SCRAPING (data_pipeline/Scrapping/)
═══════════════════════════════════════════════════════════════════

    ┌──────────────┐
    │ Site BEAC    │
    │ (https://...)│
    └──────┬───────┘
           │
    ┌──────▼────────────────────────────────────┐
    │         SCRAPER (scraper.py)              │
    │                                            │
    │  • Télécharge pages HTML                  │
    │  • Trouve et télécharge PDFs              │
    │  • Respecte robots.txt                    │
    │  • Gère cache + checkpoint                │
    └──────┬────────────────────────────────────┘
           │
           ├──────────────────┬──────────────────┐
           ▼                  ▼                  ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ PDFs Texte   │  │ PDFs Scannés │  │ HTML Pages   │
    │ (Direct)     │  │ (Images)     │  │              │
    └──────┬───────┘  └──────┬───────┘  └──────────────┘
           │                 │
    ┌──────▼─────────────────▼──────────────────────────┐
    │  EXTRACTION TEXTE (PDFTextExtractor)              │
    │                                                   │
    │  Pipeline en Cascade:                            │
    │  1. pdfplumber → Extraction directe              │
    │  2. pypdf → Fallback texte                       │
    │  3. PaddleOCR ← 🆕 Pour PDFs scannés            │
    └──────┬──────────────────────────────────────────┘
           │
    ┌──────▼────────────────────────┐
    │ TEXTE EXTRAIT + MÉTADONNÉES   │
    │ • Texte brut                  │
    │ • Confiance OCR (si applicable)│
    │ • Méthode extraction          │
    └──────┬────────────────────────┘
           │


PHASE 2: ENRICHISSEMENT (pdf_advanced.py) ← 🆕
═══════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────────────────────┐
    │      ENRICHISSEMENT AUTOMATIQUE (Parallèle)          │
    └──────────────────────────────────────────────────────┘
    
    ┌────────────────────┐  ┌────────────────────┐
    │ 2️⃣ MÉTADONNÉES    │  │ 3️⃣ TABLEAUX       │
    │ (PDFMetadata...)   │  │ (TableExtractor)   │
    │                    │  │                    │
    │ • Titre            │  │ • Détection auto   │
    │ • Auteur           │  │ • Export CSV       │
    │ • Dates            │  │ • Export Markdown  │
    │ • Langue détectée  │  │ • Export JSON      │
    │ • Mots-clés        │  │                    │
    └────────────┬───────┘  └────────┬───────────┘
                 │                   │
                 └─────────┬─────────┘
                           ▼
            ┌──────────────────────────────────┐
            │ DONNÉES ENRICHIES CONSOLIDÉES    │
            │ • Texte + Métadonnées OCR        │
            │ • Métadonnées document           │
            │ • Tableaux structurés            │
            └──────────┬───────────────────────┘
                       │


PHASE 3: STOCKAGE ET SUIVI (Outputs)
═══════════════════════════════════════════════════════════════════

    ┌──────────────────────────────────────────┐
    │  4️⃣ MONITORING & STATISTIQUES            │
    │  (PDFMonitor)                            │
    │                                          │
    │  Suivit en temps réel:                   │
    │  • Taux de succès                        │
    │  • Pages traitées                        │
    │  • PDFs OCR                              │
    │  • Temps moyen                           │
    └──────────┬───────────────────────────────┘
               │
    ┌──────────▼──────────────────────────┐
    │  5️⃣ OPTIMISATION PERFORMANCE        │
    │  (PDFBatchProcessor)                │
    │                                     │
    │  • Cache en mémoire                 │
    │  • Batch processing                 │
    │  • Logging progressif               │
    └──────────┬──────────────────────────┘
               │
    ┌──────────▼──────────────────────────────────────┐
    │             SORTIE FINALE                       │
    ├──────────────────────────────────────────────────┤
    │                                                  │
    │  📁 scraping/beac_data/        → PDFs originaux │
    │  📄 scraping/beac_text/        → Textes .txt    │
    │  📊 scraping/beac_tables/      → Tableaux       │
    │  📋 scraping/beac_pdfs_export.csv (ENRICHI)    │
    │  📈 scraping/rapport_traitement.txt            │
    │  📝 beac_scraper_v5.log                        │
    │                                                  │
    └──────────┬───────────────────────────────────────┘
               │
               ▼
    ┌──────────────────────────────┐
    │  PHASE SUIVANTE: VECTORIZATION│
    │  (data_pipeline/Vectorization)│
    │                              │
    │  • Chunking des textes       │
    │  • Génération embeddings     │
    │  • Stockage pgvector         │
    └──────────────────────────────┘
```

---

## 🔗 Dépendances et Flux de Données

### Import Graph

```python
# Niveau 1: Libraires externes
import pdfplumber, pypdf, paddleocr
import psycopg2, requests
import numpy, Pillow, pdf2image

# Niveau 2: Core
scraper.py
  ├─ PDFTextExtractor
  ├─ OCRProcessor          ← 🆕
  └─ PDFManager

# Niveau 3: Advanced (optionnel)
pdf_advanced.py
  ├─ PDFMetadataExtractor  ← 🆕
  ├─ TableExtractor        ← 🆕
  ├─ PDFMonitor           ← 🆕
  └─ PDFBatchProcessor    ← 🆕

# Niveau 4: Applications
demo_pdf_advanced.py     ← Exemples
scraper.py (main)        ← Produit du pipeline
```

---

## 🔄 Flux de Données Détaillé

### Pour un PDF Unique

```python
pdf_path = Path("rapport.pdf")

1. DÉTECTION
   ├─ existe? ✓
   ├─ format PDF? ✓
   └─ size ok? ✓
   
2. TENTATIVE 1: Texte direct
   ├─ pdfplumber.open(pdf) 
   ├─ extract_text() → 3000 chars
   └─ Succès ✅
   
   OU
   
   2. TENTATIVE 2: Fallback pypdf
   ├─ PdfReader(pdf)
   ├─ extract_text() → 2500 chars
   └─ Succès ✅
   
   OU
   
   2. TENTATIVE 3: OCR pour PDFs scannés
   ├─ est_pdf_scanne()? ✓ (< 100 chars)
   ├─ convert_from_path() → [Image, Image, ...]
   ├─ PaddleOCR.ocr(image) 
   │  ├─ detect text
   │  ├─ confidence: 0.87
   │  └─ chars: 4200
   └─ Succès ✅ + metadata_ocr
   
3. ENRICHISSEMENT PARALLÈLE
   ├─ Métadonnées
   │  ├─ reader.metadata
   │  ├─ title: "Rapport 2023"
   │  ├─ author: "BEAC"
   │  └─ language: "fr"
   │
   ├─ Tableaux
   │  ├─ page.extract_tables()
   │  ├─ [Table1, Table2, ...]
   │  └─ save CSV/Markdown
   │
   └─ Monitoring
      ├─ num_pages: 45
      ├─ num_chars: 4200
      ├─ num_tables: 3
      └─ time: 1.23s

4. SAUVEGARDE
   ├─ scraping/beac_text/rapport.txt (texte complet)
   ├─ scraping/beac_tables/rapport_table_*.csv
   ├─ CSV record:
   │  ├─ extraction_method: "PaddleOCR"
   │  ├─ ocr_confidence: "87.3%"
   │  ├─ ocr_metadata: {...}
   │  └─ ...
   └─ Rapport stats ✅
```

---

## 🎯 Points Critiques

### 1️⃣ OCR (scraper.py)

```
PDFTextExtractor
  ├─ extraire_avec_pdfplumber() → pdfplumber.open()
  ├─ extraire_avec_pypdf() → PdfReader()
  ├─ extraire_texte() [NOUVEAU]
  │  ├─ return (texte, succes, metadata_ocr)  ← Signature changée!
  │  └─ fallback → OCRProcessor
  └─ sauvegarder_texte_pdf() [MODIFIÉ]
     └─ return (path, metadata_ocr)  ← Signature changée!

OCRProcessor [NOUVEAU]
  ├─ est_pdf_scanne()
  ├─ convertir_pdf_en_images()
  ├─ extraire_texte_avec_ocr()
  └─ traiter_pdf_scanne()

PDFManager [MODIFIÉ]
  └─ ajouter_pdf()
     ├─ appelle extraire_texte() [3 retours]
     ├─ appelle sauvegarder_texte_pdf() [2 retours]
     └─ stocke metadata_ocr dans CSV
```

### 2️⃣ Métadonnées (pdf_advanced.py)

```
PDFMetadataExtractor [NOUVEAU]
  ├─ extraire_metadata()
  │  ├─ pypdf: reader.metadata
  │  ├─ détection: _detecter_langue()
  │  └─ return PDFMetadata
  └─ PDFMetadata.to_dict()

Structure:
{
  'title': ...,
  'author': ...,
  'creation_date': ...,
  'language': ...,
  'num_pages': ...,
  ...
}
```

### 3️⃣ Tableaux (pdf_advanced.py)

```
TableExtractor [NOUVEAU]
  ├─ extraire_tableaux()
  │  ├─ page.extract_tables()
  │  └─ return List[TableData]
  └─ sauvegarder_tableaux()
     ├─ format='csv' → to_csv()
     ├─ format='markdown' → to_markdown()
     └─ format='json' → to_dict()

TableData:
{
  'page_number': 1,
  'rows': [['A', 'B'], ['C', 'D']],
  'columns': 2
}
```

### 4️⃣ Monitoring (pdf_advanced.py)

```
PDFMonitor [NOUVEAU]
  ├─ record_success()
  │  ├─ successful_extractions++
  │  ├─ total_chars += chars
  │  └─ avg_extraction_time
  ├─ record_failure()
  ├─ get_report()
  └─ sauvegarder_rapport()

PDFProcessingStats:
{
  'total_pdfs': 150,
  'successful_extractions': 148,
  'success_rate': 98.7%,
  'total_pages': 3245,
  ...
}
```

### 5️⃣ Performance (pdf_advanced.py)

```
PDFBatchProcessor [NOUVEAU]
  ├─ traiter_lot()
  │  ├─ cache check: str(pdf_path) in self.cache
  │  ├─ si cache hit → return cached
  │  └─ sinon → process + cache
  ├─ clear_cache()
  └─ self.cache: Dict[str, Any]

Effet:
1ère passage:  traiter_lot() → 50s (traitement)
2e passage:    traiter_lot() → 0.5s (cache)
```

---

## 📊 Structure CSV Enrichie

### Avant v2.0

```csv
chemin_relatif;nom_pdf;lien;module;section;date_publication;taille_ko;type_document
beac_data/rapport.pdf;rapport.pdf;https://...;La BEAC;Rapports;2023-12-15;250;rapport_annuel
```

### Après v2.0 (3 colonnes + métadonnées)

```csv
chemin_relatif;chemin_texte;date_publication;nom_pdf;lien;module;section;page_source;date_extraction;taille_ko;type_document;extraction_method;ocr_confidence;ocr_metadata;contenu_pdf
beac_data/rapport.pdf;beac_text/rapport.txt;2023-12-15;rapport.pdf;https://...;La BEAC;Rapports;source_page;2026-06-17 14:30:00;250;rapport_annuel;PaddleOCR;87.5%;{"method":"PaddleOCR","confidence":0.875,"chars_extracted":4200};Rapport de la BEAC 2023...
```

**Nouvelles colonnes** :
- `extraction_method` : Méthode utilisée
- `ocr_confidence` : Qualité de l'extraction
- `ocr_metadata` : Données complètes JSON

---

## 🔀 Patterns et Conventions

### Pattern 1: Cascade de Fallback

```python
def extraire_texte(pdf):
    # Méthode 1
    resultat = methode_1(pdf)
    if resultat and len(resultat) > SEUIL:
        return resultat
    
    # Fallback 1
    resultat = methode_2(pdf)
    if resultat and len(resultat) > SEUIL:
        return resultat
    
    # Fallback 2
    resultat = methode_3(pdf)
    if resultat:
        return resultat
    
    # Échec
    return None
```

**Appliqué à** :
- PDFTextExtractor (pdfplumber → pypdf → OCR)
- Métadonnées (pypdf → pdfplumber)

### Pattern 2: Metadata Pairing

```python
def extraire_texte_avec_metadata(pdf):
    texte, metadata = extraire(pdf)
    metadata['extraction_method'] = 'PaddleOCR'
    metadata['confidence'] = 0.87
    return texte, metadata

# Stockage
pdf_info['ocr_metadata'] = json.dumps(metadata)
```

### Pattern 3: Batch Processing

```python
def traiter_lot(pdfs, batch_size=20, cache=True):
    for pdf in pdfs:
        if cache and pdf in self.cache:
            return self.cache[pdf]
        
        resultat = process(pdf)
        self.cache[pdf] = resultat
        
        if len(self.cache) > batch_size:
            # Log progress, continue
            pass
    
    return resultats
```

---

## 🎬 Scénario Complet

**Scenario** : Traiter tous les PDFs BEAC avec v2.0

```
1. Lancer le scraper
   $ python scraper.py
   
2. Scraper télécharge les PDFs
   • 150 PDFs trouvés
   • ~110 PDFs texte direct
   • ~40 PDFs scannés (OCR)
   
3. Pour chaque PDF:
   ✓ Extraction texte (avec OCR si nécessaire)
   ✓ Extraction métadonnées
   ✓ Extraction tableaux
   ✓ Enregistrement stats
   
4. Résultats:
   beac_text/          : 150 fichiers .txt
   beac_tables/        : 87 fichiers tableaux
   beac_pdfs_export.csv: 150 lignes enrichies
   rapport_*.txt       : Statistiques
   
5. Visualiser le rapport
   $ cat rapport_traitement.txt
   
   Résultat:
   ╔════════════════════════════════════════════════╗
   ║ PDFs traités:        150                         ║
   ║ Extractions réussies: 150                        ║
   ║ Taux de succès:      100%                        ║
   ║ PDFs scannés (OCR):  40                          ║
   ║ Tableaux trouvés:    87                          ║
   ║ Temps moyen:         0.92s                       ║
   ╚════════════════════════════════════════════════╝
   
6. Passer à la phase Chunking
   $ cd ../Chunking
   $ python chunking.py
   
7. Ensuite Vectorization
   $ cd ../Vectorization
   $ python ingest_to_pgvector.py
```

---

## 🔍 Points d'Observation

### Logs Attendus

```
✓ PaddleOCR initialisé (multilingue: EN, FR)
✓ Chargé 0 PDF depuis CSV existant
🔄 Traitement OCR: rapport_scanne.pdf
  Conversion: 45 pages converties
  OCR page 1/45...
  OCR page 2/45...
  ...
✅ OCR: 12450 chars extraits (confiance: 87.25%)
📄 Texte PDF extrait → scraping/beac_text/rapport.txt
💾 CSV mis à jour: 150 PDFs | OCR: 40 PDFs scannés traités
```

### Métriques à Surveiller

```
extraction_method distribution:
  - "text" : 110 (73%)
  - "PaddleOCR" : 40 (27%)

ocr_confidence distribution:
  - 90%+ : 35 PDFs
  - 80-90% : 4 PDFs
  - <80% : 1 PDF

Success rate:
  - Text extraction: 100%
  - OCR extraction: 95%
  - Overall: 99.3%
```

---

## 🚀 Performance Attendue

| Opération | Temps |
|-----------|-------|
| Extraction PDF texte | 0.5s |
| Extraction PDF scannée (OCR) | 2.5s |
| Extraction métadonnées | 0.1s |
| Extraction tableaux | 0.3s |
| Sauvegarde CSV | 1.0s |
| **Total 150 PDFs (1ère fois)** | ~120s |
| **Total 150 PDFs (cache)** | ~1s |

---

**Visualisation complète du système v2.0 ✅**
