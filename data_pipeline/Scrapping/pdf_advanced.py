#!/usr/bin/env python3
"""
Fonctionnalités avancées pour l'extraction PDF :
- 2️⃣ Métadonnées enrichies
- 3️⃣ Extraction de tableaux
- 4️⃣ Monitoring
- 5️⃣ Performance
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import pypdf
import pdfplumber

# ══════════════════════════════════════════════════════════════════
#  2️⃣ EXTRACTEUR DE MÉTADONNÉES PDF
# ══════════════════════════════════════════════════════════════════

@dataclass
class PDFMetadata:
    """Métadonnées complètes d'un PDF"""
    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    producer: Optional[str] = None
    num_pages: Optional[int] = None
    language: Optional[str] = None
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire"""
        data = asdict(self)
        # Convertir les dates en strings ISO
        if self.creation_date:
            data['creation_date'] = str(self.creation_date)
        if self.modification_date:
            data['modification_date'] = str(self.modification_date)
        return {k: v for k, v in data.items() if v is not None}


class PDFMetadataExtractor:
    """Extrait les métadonnées complètes d'un PDF"""
    
    def __init__(self):
        self.has_pdfplumber = False
        self.has_pypdf = False
        
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            logging.warning("pdfplumber non installé pour extraction de métadonnées")
        
        try:
            import pypdf
            self.pypdf = pypdf
            self.has_pypdf = True
        except ImportError:
            logging.warning("pypdf non installé pour extraction de métadonnées")
    
    def extraire_metadata(self, chemin_pdf: Path) -> PDFMetadata:
        """Extrait les métadonnées du PDF"""
        metadata = PDFMetadata()
        
        if not chemin_pdf.exists():
            return metadata
        
        # Essayer avec pypdf d'abord (plus rapide)
        if self.has_pypdf:
            try:
                with open(chemin_pdf, 'rb') as f:
                    reader = self.pypdf.PdfReader(f)
                    doc_info = reader.metadata
                    
                    if doc_info:
                        metadata.title = doc_info.get('/Title')
                        metadata.author = doc_info.get('/Author')
                        metadata.subject = doc_info.get('/Subject')
                        metadata.creator = doc_info.get('/Creator')
                        metadata.producer = doc_info.get('/Producer')
                        
                        # Dates
                        creation_date = doc_info.get('/CreationDate')
                        if creation_date:
                            metadata.creation_date = self._parse_pdf_date(creation_date)
                        
                        mod_date = doc_info.get('/ModDate')
                        if mod_date:
                            metadata.modification_date = self._parse_pdf_date(mod_date)
                    
                    metadata.num_pages = len(reader.pages)
            
            except Exception as e:
                logging.debug(f"Erreur extraction métadonnées pypdf: {e}")
        
        # Déterminer la langue (basique)
        if self.has_pdfplumber and not metadata.language:
            try:
                with self.pdfplumber.open(chemin_pdf) as pdf:
                    texte_sample = ""
                    for page in pdf.pages[:3]:  # Première 3 pages
                        texte = page.extract_text() or ""
                        texte_sample += texte
                    
                    metadata.language = self._detecter_langue(texte_sample)
            except Exception as e:
                logging.debug(f"Erreur détection langue: {e}")
        
        return metadata
    
    def _parse_pdf_date(self, date_str: str) -> str:
        """Parse une date PDF (format D:YYYYMMDDHHmmSS...)"""
        try:
            if isinstance(date_str, bytes):
                date_str = date_str.decode('utf-8', errors='ignore')
            
            # Format: D:20230615143022
            if date_str.startswith('D:'):
                date_str = date_str[2:]
            
            if len(date_str) >= 8:
                return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"
        except Exception:
            pass
        
        return None
    
    def _detecter_langue(self, texte: str) -> Optional[str]:
        """Détecte la langue d'un texte (basique)"""
        if not texte:
            return None
        
        texte_lower = texte.lower()
        
        # Mots-clés français communs
        mots_fr = ['de', 'le', 'la', 'et', 'un', 'une', 'les', 'à', 'en', 'est', 'par', 'pour']
        score_fr = sum(1 for mot in mots_fr if f" {mot} " in f" {texte_lower} ")
        
        # Mots-clés anglais communs
        mots_en = ['the', 'and', 'to', 'of', 'a', 'in', 'is', 'that', 'for', 'with']
        score_en = sum(1 for mot in mots_en if f" {mot} " in f" {texte_lower} ")
        
        if score_fr > score_en and score_fr > 0:
            return "fr"
        elif score_en > 0:
            return "en"
        
        return None


# ══════════════════════════════════════════════════════════════════
#  3️⃣ EXTRACTEUR DE TABLEAUX
# ══════════════════════════════════════════════════════════════════

@dataclass
class TableData:
    """Structure pour un tableau extrait"""
    page_number: int
    rows: List[List[str]]
    columns: int
    
    def to_csv(self) -> str:
        """Convertir en CSV"""
        lines = []
        for row in self.rows:
            # Échapper les guillemets
            escaped_row = [f'"{cell.replace(chr(34), chr(34)+chr(34))}"' if cell else "" for cell in row]
            lines.append(','.join(escaped_row))
        return '\n'.join(lines)
    
    def to_markdown(self) -> str:
        """Convertir en Markdown"""
        if not self.rows or not self.rows[0]:
            return ""
        
        lines = []
        # En-tête
        header = '| ' + ' | '.join(self.rows[0]) + ' |'
        lines.append(header)
        lines.append('|' + '|'.join(['---'] * len(self.rows[0])) + '|')
        
        # Lignes
        for row in self.rows[1:]:
            lines.append('| ' + ' | '.join(row) + ' |')
        
        return '\n'.join(lines)


class TableExtractor:
    """Extrait les tableaux des PDFs"""
    
    def __init__(self):
        self.has_pdfplumber = False
        
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            logging.warning("pdfplumber nécessaire pour l'extraction de tableaux")
    
    def extraire_tableaux(self, chemin_pdf: Path) -> List[TableData]:
        """Extrait tous les tableaux du PDF"""
        if not self.has_pdfplumber or not chemin_pdf.exists():
            return []
        
        tableaux = []
        try:
            with self.pdfplumber.open(chemin_pdf) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables()
                    
                    if tables:
                        for table in tables:
                            # Nettoyer les cellules
                            cleaned_rows = []
                            for row in table:
                                cleaned_row = [
                                    str(cell).strip() if cell else ""
                                    for cell in row
                                ]
                                cleaned_rows.append(cleaned_row)
                            
                            if cleaned_rows:
                                tableaux.append(TableData(
                                    page_number=page_num,
                                    rows=cleaned_rows,
                                    columns=len(cleaned_rows[0]) if cleaned_rows[0] else 0
                                ))
        
        except Exception as e:
            logging.error(f"Erreur extraction tableaux: {e}")
        
        return tableaux
    
    def sauvegarder_tableaux(self, chemin_pdf: Path, chemin_sortie: Path, format: str = 'csv'):
        """
        Sauvegarde les tableaux extraits
        format: 'csv', 'markdown', ou 'json'
        """
        tableaux = self.extraire_tableaux(chemin_pdf)
        if not tableaux:
            return None
        
        nom_base = chemin_pdf.stem
        fichiers_crees = []
        
        for idx, tableau in enumerate(tableaux, start=1):
            if format == 'csv':
                nom_fichier = f"{nom_base}_table_{tableau.page_number}_{idx}.csv"
                contenu = tableau.to_csv()
            elif format == 'markdown':
                nom_fichier = f"{nom_base}_table_{tableau.page_number}_{idx}.md"
                contenu = tableau.to_markdown()
            elif format == 'json':
                nom_fichier = f"{nom_base}_table_{tableau.page_number}_{idx}.json"
                contenu = json.dumps({
                    'page': tableau.page_number,
                    'rows': tableau.rows,
                    'columns': tableau.columns
                }, ensure_ascii=False, indent=2)
            else:
                continue
            
            chemin_fichier = chemin_sortie / nom_fichier
            chemin_sortie.mkdir(parents=True, exist_ok=True)
            
            chemin_fichier.write_text(contenu, encoding='utf-8')
            fichiers_crees.append(chemin_fichier)
            logging.info(f"  📊 Tableau sauvegardé: {nom_fichier}")
        
        return fichiers_crees


# ══════════════════════════════════════════════════════════════════
#  4️⃣ MONITORING ET STATISTIQUES
# ══════════════════════════════════════════════════════════════════

@dataclass
class PDFProcessingStats:
    """Statistiques de traitement"""
    total_pdfs: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    total_pages: int = 0
    total_chars: int = 0
    total_tables: int = 0
    total_images: int = 0
    ocr_pdfs: int = 0
    avg_extraction_time: float = 0.0
    
    def get_success_rate(self) -> float:
        """Taux de succès"""
        if self.total_pdfs == 0:
            return 0.0
        return (self.successful_extractions / self.total_pdfs) * 100
    
    def get_summary(self) -> str:
        """Résumé des statistiques"""
        return f"""
╔════════════════════════════════════════════════╗
║   RAPPORT DE TRAITEMENT PDF                     ║
╠════════════════════════════════════════════════╣
║ PDFs traités:        {self.total_pdfs:<27} ║
║ Extractions réussies: {self.successful_extractions:<27} ║
║ Échecs:              {self.failed_extractions:<27} ║
║ Taux de succès:      {self.get_success_rate():.1f}%{'':<21} ║
║ Pages totales:       {self.total_pages:<27} ║
║ Caractères extraits: {self.total_chars:<27} ║
║ Tableaux trouvés:    {self.total_tables:<27} ║
║ Images détectées:    {self.total_images:<27} ║
║ PDFs scannés (OCR):  {self.ocr_pdfs:<27} ║
║ Temps moyen:         {self.avg_extraction_time:.2f}s{'':<20} ║
╚════════════════════════════════════════════════╝
"""


class PDFMonitor:
    """Monitore le traitement des PDFs"""
    
    def __init__(self):
        self.stats = PDFProcessingStats()
        self.extraction_times: List[float] = []
        self.start_time = datetime.now()
    
    def record_success(self, num_pages: int, num_chars: int, num_tables: int = 0, is_ocr: bool = False, time_taken: float = 0.0):
        """Enregistre une extraction réussie"""
        self.stats.successful_extractions += 1
        self.stats.total_pages += num_pages
        self.stats.total_chars += num_chars
        self.stats.total_tables += num_tables
        
        if is_ocr:
            self.stats.ocr_pdfs += 1
        
        if time_taken > 0:
            self.extraction_times.append(time_taken)
            self.stats.avg_extraction_time = sum(self.extraction_times) / len(self.extraction_times)
    
    def record_failure(self):
        """Enregistre un échec d'extraction"""
        self.stats.failed_extractions += 1
    
    def set_total_pdfs(self, total: int):
        """Définit le nombre total de PDFs"""
        self.stats.total_pdfs = total
    
    def get_report(self) -> str:
        """Génère le rapport final"""
        return self.stats.get_summary()
    
    def sauvegarder_rapport(self, chemin_sortie: Path):
        """Sauvegarde le rapport en fichier"""
        chemin_sortie.parent.mkdir(parents=True, exist_ok=True)
        
        rapport = f"""
Rapport de traitement PDF
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Durée totale: {(datetime.now() - self.start_time).total_seconds():.2f}s

{self.get_report()}

Détail des temps d'extraction:
- Min: {min(self.extraction_times) if self.extraction_times else 0:.2f}s
- Max: {max(self.extraction_times) if self.extraction_times else 0:.2f}s
- Moyenne: {self.stats.avg_extraction_time:.2f}s
"""
        chemin_sortie.write_text(rapport, encoding='utf-8')
        logging.info(f"📊 Rapport sauvegardé: {chemin_sortie}")


# ══════════════════════════════════════════════════════════════════
#  5️⃣ OPTIMISATION DE PERFORMANCE
# ══════════════════════════════════════════════════════════════════

class PDFBatchProcessor:
    """
    Traite les PDFs par lot avec gestion des ressources
    Optimise la mémoire et le temps de traitement
    """
    
    def __init__(self, batch_size: int = 5, enable_cache: bool = True):
        self.batch_size = batch_size
        self.enable_cache = enable_cache
        self.cache: Dict[str, Any] = {}
    
    def traiter_lot(self, pdf_paths: List[Path], callback) -> List[Any]:
        """
        Traite un lot de PDFs
        callback: fonction à appeler pour chaque PDF
        """
        resultats = []
        
        for i, pdf_path in enumerate(pdf_paths, start=1):
            # Vérifier le cache
            if self.enable_cache and str(pdf_path) in self.cache:
                resultats.append(self.cache[str(pdf_path)])
                logging.debug(f"Cache hit: {pdf_path.name}")
                continue
            
            # Traiter le PDF
            try:
                resultat = callback(pdf_path)
                resultats.append(resultat)
                
                # Cacher le résultat
                if self.enable_cache:
                    self.cache[str(pdf_path)] = resultat
                
                # Log de progression
                if i % self.batch_size == 0:
                    logging.info(f"Progression: {i}/{len(pdf_paths)} PDFs traités")
            
            except Exception as e:
                logging.error(f"Erreur traitement {pdf_path.name}: {e}")
                resultats.append(None)
        
        return resultats
    
    def clear_cache(self):
        """Vide le cache"""
        self.cache.clear()
        logging.debug("Cache vidé")
