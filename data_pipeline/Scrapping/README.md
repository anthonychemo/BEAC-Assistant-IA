# BEAC Scraper

Ce projet collecte les documents disponibles sur le site de la BEAC, télécharge les fichiers trouvés, extrait le texte des PDF et génère un export CSV enrichi.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Vérifier la connexion

```powershell
python test_connexion.py
```

Ce script teste l'accès au site, à `robots.txt` et à quelques pages importantes.

## Lancer le scraper

```powershell
python scraper.py
```

## Sorties générées

Le scraper crée automatiquement :

```text
scraping/
  beac_data/
    rapport_final.json
  beac_text/
  cache/
    checkpoint.json
  beac_pdfs_export.csv
beac_scraper_v5.log
```

## Configuration principale

La configuration se trouve dans la classe `ScraperConfig` de `scraper.py`.

Paramètres importants :

- `base_url` : site cible
- `delay` : délai entre requêtes
- `timeout` : délai maximum HTTP
- `retries` : nombre de tentatives
- `max_workers` : nombre de threads
- `max_pages` : limite globale de pages
- `max_depth` : profondeur maximale de découverte
- `respect_robots_txt` : respect de `robots.txt`

## Notes

- Les PDF scannés nécessitent un OCR externe pour une extraction texte complète.
- Le cache HTML évite de retélécharger les pages déjà visitées.
- Le checkpoint permet de reprendre le traitement après interruption.
