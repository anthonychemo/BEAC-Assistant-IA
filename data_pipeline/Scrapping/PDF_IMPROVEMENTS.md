# 📚 Guide Complet des Améliorations PDF

## Vue d'ensemble

5 améliorations majeures pour le traitement des PDFs BEAC :

| # | Fonctionnalité | Fichier | Classe | Avantages |
|---|---|---|---|---|
| **1️⃣** | PDFs scannés + OCR | `scraper.py` | `OCRProcessor` | Traite les documents scannés automatiquement |
| **2️⃣** | Métadonnées enrichies | `pdf_advanced.py` | `PDFMetadataExtractor` | Récupère titre, auteur, dates, langue |
| **3️⃣** | Extraction tableaux | `pdf_advanced.py` | `TableExtractor` | CSV, Markdown, JSON |
| **4️⃣** | Monitoring | `pdf_advanced.py` | `PDFMonitor` | Statistiques détaillées |
| **5️⃣** | Performance | `pdf_advanced.py` | `PDFBatchProcessor` | Cache, parallélisation |

---

## 1️⃣ Gestion des PDFs Scannés avec OCR

### 📦 Installation

```bash
pip install -r requirements.txt
# Contient déjà: paddleocr, pdf2image
```

### 🔄 Fonctionnement

**Pipeline en cascade** :

```
PDF
  ↓
pdfplumber (extraction directe)
  ↓ [Échec ou < 100 caractères]
pypdf (fallback)
  ↓ [Échec ou < 100 caractères]
PaddleOCR (pour PDFs scannés) ← 🆕
  ↓
Texte extrait + métadonnées OCR
```

### 💻 Utilisation

```python
from scraper import PDFTextExtractor, OCRProcessor

extractor = PDFTextExtractor()
texte, succes, metadata_ocr = extractor.extraire_texte(Path("document.pdf"))

if metadata_ocr:
    print(f"✅ OCR réussi")
    print(f"Confiance: {metadata_ocr['confidence']:.2%}")
    print(f"Caractères extraits: {metadata_ocr['chars_extracted']}")
```

### 📊 Métadonnées OCR dans CSV

Nouvelles colonnes ajoutées :
- `extraction_method` : "text" ou "PaddleOCR"
- `ocr_confidence` : Confiance du modèle OCR
- `ocr_metadata` : Données complètes en JSON

### ⚙️ Configuration

Dans `scraper.py`, classe `OCRProcessor` :

```python
self.ocr = PaddleOCR(
    use_angle_cls=True,          # Rotation automatique
    lang=['en', 'fr'],           # Multilingue
    show_log=False,
    cpu_threads=2                # Ajuster si besoin
)
```

### 📈 Statistiques

```python
stats = ocr_processor.get_stats()
# {
#     'scanned_pdfs_processed': 42,
#     'total_ocr_chars': 156000,
#     'avg_chars_per_pdf': 3714
# }
```

---

## 2️⃣ Métadonnées Enrichies

### 🎯 Informations Extraites

```python
from pdf_advanced import PDFMetadataExtractor

extractor = PDFMetadataExtractor()
metadata = extractor.extraire_metadata(Path("rapport.pdf"))

# Résultat :
{
    'title': 'Rapport Annuel 2023',
    'author': 'BEAC',
    'subject': 'Politique monétaire',
    'creator': 'Microsoft Word',
    'creation_date': '2023-12-15',
    'modification_date': '2023-12-20',
    'producer': 'PDF Producer v1.0',
    'num_pages': 45,
    'language': 'fr',
    'keywords': ['inflation', 'politique', 'monétaire']
}
```

### 💻 Utilisation Avancée

```python
# Intégration dans PDFManager
from pdf_advanced import PDFMetadataExtractor

class PDFManager:
    def __init__(self, config):
        # ... code existant ...
        self.metadata_extractor = PDFMetadataExtractor()
    
    def ajouter_pdf(self, pdf_info, extraire_texte=True):
        # ... code existant ...
        
        # Ajouter métadonnées
        metadata = self.metadata_extractor.extraire_metadata(chemin_pdf)
        pdf_info.update(metadata.to_dict())
        
        # ... continuer ...
```

### 📝 Détection Automatique de Langue

```python
# Utilise des mots-clés communs pour détecter FR vs EN
# Peut être étendu avec langdetect ou textblob
metadata = extractor.extraire_metadata(pdf_path)
if metadata.language == 'fr':
    print("Document en français")
```

---

## 3️⃣ Extraction de Tableaux

### 🗂️ Formats Supportés

```python
from pdf_advanced import TableExtractor

extractor = TableExtractor()
tableaux = extractor.extraire_tableaux(Path("document.pdf"))

# Sauvegarder en différents formats
extractor.sauvegarder_tableaux(pdf_path, output_dir, format='csv')      # CSV
extractor.sauvegarder_tableaux(pdf_path, output_dir, format='markdown')  # Markdown
extractor.sauvegarder_tableaux(pdf_path, output_dir, format='json')      # JSON
```

### 📊 Exemple de Tableau Extrait

**Données brutes** (format interne) :
```python
{
    'page_number': 5,
    'rows': [
        ['Année', 'Inflation', 'PIB'],
        ['2021', '2.3%', '3.1%'],
        ['2022', '5.8%', '1.9%']
    ],
    'columns': 3
}
```

**Format CSV** :
```csv
Année,Inflation,PIB
2021,2.3%,3.1%
2022,5.8%,1.9%
```

**Format Markdown** :
```markdown
| Année | Inflation | PIB |
|-------|-----------|-----|
| 2021  | 2.3%      | 3.1% |
| 2022  | 5.8%      | 1.9% |
```

### 💡 Cas d'Usage

- Conversion de rapports PDF en données structurées
- Analyse de tableaux statistiques
- Export vers bases de données
- Visualisation automatique

---

## 4️⃣ Monitoring et Statistiques

### 📊 Rapport Automatique

```python
from pdf_advanced import PDFMonitor

monitor = PDFMonitor()

# Pendant le traitement
for pdf in pdf_list:
    result = traiter_pdf(pdf)
    monitor.record_success(
        num_pages=result['pages'],
        num_chars=result['chars'],
        num_tables=result['tables'],
        is_ocr=result['used_ocr'],
        time_taken=result['duration']
    )

# Afficher le rapport
print(monitor.get_report())

# Sauvegarder
monitor.sauvegarder_rapport(Path("rapport.txt"))
```

### 📈 Exemple de Rapport

```
╔════════════════════════════════════════════════╗
║   RAPPORT DE TRAITEMENT PDF                     ║
╠════════════════════════════════════════════════╣
║ PDFs traités:        150                         ║
║ Extractions réussies: 148                        ║
║ Échecs:              2                           ║
║ Taux de succès:      98.7%                       ║
║ Pages totales:       3245                        ║
║ Caractères extraits: 2,156,789                   ║
║ Tableaux trouvés:    87                          ║
║ Images détectées:    342                         ║
║ PDFs scannés (OCR):  34                          ║
║ Temps moyen:         1.23s                       ║
╚════════════════════════════════════════════════╝
```

### 🎯 Métriques Disponibles

- **Taux de succès** : % d'extractions réussies
- **Pages/Caractères** : Volume traité
- **Tableaux détectés** : # de tableaux
- **Temps moyen** : Performance
- **PDFs scannés** : # traités par OCR

---

## 5️⃣ Optimisation de Performance

### ⚡ Batch Processing avec Cache

```python
from pdf_advanced import PDFBatchProcessor

# Configuration
processor = PDFBatchProcessor(
    batch_size=5,       # PDFs par lot
    enable_cache=True   # Cache des résultats
)

# Fonction de traitement
def traiter_pdf(pdf_path):
    # Votre logique ici
    return {...}

# Traiter les PDFs
pdfs = list(Path("data").glob("*.pdf"))
resultats = processor.traiter_lot(pdfs, traiter_pdf)

# Deuxième appel = instantané (cache!)
resultats = processor.traiter_lot(pdfs, traiter_pdf)

# Vider le cache
processor.clear_cache()
```

### 🚀 Performance Estimée

| Opération | Temps (1ère fois) | Temps (cache) |
|-----------|-------------------|---------------|
| 10 PDFs texte | 5s | 0.1s |
| 10 PDFs OCR | 45s | 0.1s |
| 100 PDFs mix | 120s | 1s |

### 🔧 Optimisations Intégrées

1. **Cache en mémoire** : Stocke les résultats
2. **Batch processing** : Traite par lots
3. **Logging progressif** : Suivi en temps réel
4. **Gestion ressources** : Limite mémoire

### 💾 Vider le Cache Automatiquement

```python
# Pour éviter la consommation excessive de mémoire
if len(processor.cache) > 1000:
    processor.clear_cache()
```

---

## 📋 Intégration Complète

### Pipeline Recommandé

```python
from scraper import PDFManager, ScraperConfig
from pdf_advanced import (
    PDFMetadataExtractor,
    TableExtractor,
    PDFMonitor,
    PDFBatchProcessor
)

# Configuration
config = ScraperConfig()

# Gestionnaire principal
pdf_manager = PDFManager(config)

# Outils avancés
metadata_extractor = PDFMetadataExtractor()
table_extractor = TableExtractor()
monitor = PDFMonitor()
batch_processor = PDFBatchProcessor()

# Traitement
def traiter_pdf_complet(pdf_path):
    # 1. Extraire texte (avec OCR)
    texte, succes, metadata_ocr = pdf_manager.pdf_extractor.extraire_texte(pdf_path)
    
    # 2. Métadonnées
    metadata = metadata_extractor.extraire_metadata(pdf_path)
    
    # 3. Tableaux
    tableaux = table_extractor.extraire_tableaux(pdf_path)
    
    # 4. Enregistrer statistiques
    monitor.record_success(
        num_pages=metadata.num_pages or 0,
        num_chars=len(texte),
        num_tables=len(tableaux),
        is_ocr=metadata_ocr is not None,
        time_taken=0.0
    )
    
    return {
        'texte': texte,
        'metadata': metadata.to_dict(),
        'tableaux': tableaux
    }

# Appliquer à tous les PDFs
pdf_list = list(Path("data").glob("*.pdf"))
resultats = batch_processor.traiter_lot(pdf_list, traiter_pdf_complet)

# Rapport final
print(monitor.get_report())
```

---

## 📝 Exemples Concrets

### Exemple 1 : Rapport Annuel Complet

```python
pdf_path = Path("rapport_annuel_2023.pdf")

# 1. Métadonnées
metadata = metadata_extractor.extraire_metadata(pdf_path)
print(f"Rapport: {metadata.title}")
print(f"Pages: {metadata.num_pages}")
print(f"Auteur: {metadata.author}")

# 2. Texte principal (avec OCR si nécessaire)
texte, _, ocr_meta = pdf_manager.pdf_extractor.extraire_texte(pdf_path)
print(f"Extraction: {'OCR' if ocr_meta else 'Texte direct'}")

# 3. Tableaux statistiques
tableaux = table_extractor.extraire_tableaux(pdf_path)
for i, table in enumerate(tableaux):
    table_extractor.sauvegarder_tableaux(
        pdf_path, 
        Path("data/tables"), 
        format='csv'
    )

# 4. Enregistrer tout dans la base de données
pdf_manager.ajouter_pdf({
    'nom_pdf': pdf_path.name,
    'chemin_absolu': str(pdf_path),
    'titre': metadata.title,
    'num_pages': metadata.num_pages,
    'num_tableaux': len(tableaux)
})
```

### Exemple 2 : Batch Processing Massif

```python
# Traiter tous les PDFs BEAC
all_pdfs = list(Path("scraping/beac_data").rglob("*.pdf"))

# Avec cache et batch processing
processor = PDFBatchProcessor(batch_size=10, enable_cache=True)
monitor = PDFMonitor()
monitor.set_total_pdfs(len(all_pdfs))

def process(pdf):
    return pdf_manager.pdf_extractor.extraire_texte(pdf)

start = time.time()
resultats = processor.traiter_lot(all_pdfs, process)
print(f"Traité en {time.time() - start:.2f}s")

# Deuxième passage avec cache (beaucoup plus rapide)
start = time.time()
resultats = processor.traiter_lot(all_pdfs, process)
print(f"Cache hit en {time.time() - start:.2f}s")
```

---

## 🐛 Troubleshooting

### Problème : OCR trop lent

```python
# Solution 1 : Réduire la DPI
# Dans OCRProcessor.convertir_pdf_en_images()
images = convert_from_path(chemin_pdf, dpi=150)  # Au lieu de 300

# Solution 2 : Activer le GPU
from paddleocr import PaddleOCR
self.ocr = PaddleOCR(use_gpu=True)
```

### Problème : Mémoire insuffisante

```python
# Vider le cache régulièrement
if len(processor.cache) > 500:
    processor.clear_cache()

# Ou limiter la batch size
processor = PDFBatchProcessor(batch_size=1)
```

### Problème : Tableaux mal détectés

```python
# Vérifier manuellement
tables = table_extractor.extraire_tableaux(pdf_path)
if not tables:
    logging.warning("Aucun tableau trouvé - PDF peut être scanné ou mal formé")
```

---

## 📚 Fichiers Modifiés

| Fichier | Changements |
|---------|-----------|
| `requirements.txt` | + paddleocr, pdf2image, Pillow, numpy |
| `scraper.py` | + OCRProcessor, modification PDFTextExtractor |
| `pdf_advanced.py` | 🆕 Tous les outils avancés |
| `demo_pdf_advanced.py` | 🆕 Exemples et démos |

---

## ✅ Checklist d'Utilisation

- [ ] Installer les dépendances : `pip install -r requirements.txt`
- [ ] Vérifier l'OCR : Tester avec un PDF scanné
- [ ] Vérifier les métadonnées : Extraire d'un rapport BEAC
- [ ] Vérifier les tableaux : Chercher dans un document avec tableaux
- [ ] Lancer le monitoring : Traiter un lot et voir le rapport
- [ ] Tester la performance : Comparer 1ère vs 2e passage avec cache

---

**Besoin d'aide ?** Lancez la démo : `python demo_pdf_advanced.py`
