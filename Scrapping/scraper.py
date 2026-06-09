#!/usr/bin/env python3
import os
import re
import time
import json
import csv
import hashlib
import logging
import requests
import threading
import urllib.robotparser
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

# ══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════

@dataclass
class ScraperConfig:
    """Configuration centralisée"""
    base_url: str = "https://www.beac.int"
    
    # Dossiers de sortie
    root_dir: Path = Path("scraping/beac_data")           # PDFs et pages HTML
    text_dir: Path = Path("scraping/beac_text")           # Textes extraits des PDF
    
    # Requêtes HTTP
    delay: float = 1.0
    timeout: int = 30
    retries: int = 3
    backoff_factor: float = 2.0
    
    # Concurrency
    max_workers: int = 2
    max_pages: int = 800
    max_depth: int = 5
    respect_robots_txt: bool = True
    
    # Cache
    cache_dir: Path = Path("scraping/cache")
    
    # Fichier CSV des PDF
    csv_output: Path = Path("scraping/beac_pdfs_export.csv")
    
    # Filtres
    doc_extensions: Set[str] = field(default_factory=lambda: {
        '.pdf', '.docx', '.doc', '.xlsx', '.xls',
        '.csv', '.pptx', '.ppt', '.odt', '.ods', '.rtf'
    })
    
    exclude_paths: Set[str] = field(default_factory=lambda: {
        '/wp-json', '/wp-admin', '/feed', '/embed',
        '/author', '/category', '/tag', '/page/',
        '/?s=', '/search/', '/javascript:'
    })
    
    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.text_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.csv_output.parent.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════
#  EXTRACTEUR DE TEXTE PDF (pdfplumber + pypdf)
# ══════════════════════════════════════════════════════════════════

class PDFTextExtractor:
    """
    Extrait le contenu textuel des fichiers PDF
    Stratégie en cascade : pdfplumber → pypdf
    """
    
    def __init__(self):
        self.has_pdfplumber = False
        self.has_pypdf = False
        
        # Vérifier les dépendances
        try:
            import pdfplumber
            self.pdfplumber = pdfplumber
            self.has_pdfplumber = True
        except ImportError:
            logging.warning("pdfplumber non installé. pip install pdfplumber pour meilleure extraction")
        
        try:
            import pypdf
            self.pypdf = pypdf
            self.has_pypdf = True
        except ImportError:
            logging.warning("pypdf non installé. pip install pypdf pour fallback")
    
    def extraire_avec_pdfplumber(self, chemin_pdf: Path) -> str:
        """Extraction avec pdfplumber (meilleur pour mises en page complexes)"""
        if not self.has_pdfplumber:
            return ""
        
        textes = []
        try:
            with self.pdfplumber.open(chemin_pdf) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    texte = page.extract_text()
                    if texte and texte.strip():
                        textes.append(f"--- Page {i} ---\n{texte.strip()}")
            return "\n\n".join(textes)
        except Exception as e:
            logging.debug(f"pdfplumber erreur pour {chemin_pdf.name}: {e}")
            return ""
    
    def extraire_avec_pypdf(self, chemin_pdf: Path) -> str:
        """Extraction avec pypdf (fallback)"""
        if not self.has_pypdf:
            return ""
        
        textes = []
        try:
            reader = self.pypdf.PdfReader(chemin_pdf)
            for i, page in enumerate(reader.pages, start=1):
                texte = page.extract_text()
                if texte and texte.strip():
                    textes.append(f"--- Page {i} ---\n{texte.strip()}")
            return "\n\n".join(textes)
        except Exception as e:
            logging.debug(f"pypdf erreur pour {chemin_pdf.name}: {e}")
            return ""
    
    def extraire_texte(self, chemin_pdf: Path) -> Tuple[str, bool]:
        """
        Extrait le texte du PDF avec cascade de fallback
        Retourne (texte, succes)
        """
        if not chemin_pdf.exists():
            return "[ERREUR] Fichier PDF introuvable", False
        
        # Tentative 1 : pdfplumber
        texte = self.extraire_avec_pdfplumber(chemin_pdf)
        if texte and len(texte) > 100:
            return texte, True
        
        # Tentative 2 : pypdf
        texte = self.extraire_avec_pypdf(chemin_pdf)
        if texte and len(texte) > 100:
            logging.info(f"  ↪ Extraction via pypdf (fallback): {chemin_pdf.name}")
            return texte, True
        
        # Aucune extraction possible
        return (
            "[AVERTISSEMENT] Impossible d'extraire le texte de ce PDF.\n"
            "Il s'agit probablement d'un PDF scanné (image). "
            "Un outil OCR comme Tesseract serait nécessaire.",
            False
        )
    
    def sauvegarder_texte_pdf(self, chemin_pdf: Path, dossier_sortie: Path, texte: Optional[str] = None) -> Optional[Path]:
        """
        Extrait le texte du PDF et le sauvegarde en .txt
        Retourne le chemin du fichier .txt créé, ou None si échec
        """
        # Déterminer le chemin de sortie (même structure que le PDF)
        # Ex: scraping/beac_data/La beac/documents/rapport.pdf
        #   → scraping/beac_text/La beac/documents/rapport.txt
        
        # Chercher le module (premier dossier après root_dir)
        try:
            # Trouver le chemin relatif par rapport à root_dir
            root_parent = self._find_root_parent(chemin_pdf)
            if root_parent:
                relative = chemin_pdf.relative_to(root_parent)
            else:
                relative = Path(chemin_pdf.name)
        except ValueError:
            relative = Path(chemin_pdf.name)
        
        # Remplacer l'extension .pdf par .txt
        txt_path = dossier_sortie / relative.with_suffix('.txt')
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        
        if texte is None:
            texte, _ = self.extraire_texte(chemin_pdf)
        
        if texte:
            # Ajouter en-tête
            entete = (
                f"Source PDF : {chemin_pdf.name}\n"
                f"Chemin original : {chemin_pdf}\n"
                f"Date extraction : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"{'=' * 70}\n\n"
            )
            txt_path.write_text(entete + texte, encoding='utf-8')
            logging.info(f"  📄 Texte PDF extrait → {txt_path}")
            return txt_path
        
        return None
    
    def _find_root_parent(self, path: Path) -> Optional[Path]:
        """Trouve le dossier parent qui correspond à root_dir"""
        for parent in path.parents:
            if parent.name == "beac_data" or str(parent).endswith("beac_data"):
                return parent
        return None

# ══════════════════════════════════════════════════════════════════
#  GESTIONNAIRE DE PDF (avec export CSV enrichi)
# ══════════════════════════════════════════════════════════════════

class PDFManager:
    """
    Gère le suivi des PDF téléchargés et l'export CSV
    avec extraction du contenu texte des PDF
    """
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.pdf_records: List[Dict[str, str]] = []
        self.processed_pdfs: Set[str] = set()
        self.pdf_extractor = PDFTextExtractor()
        self.lock = threading.Lock()
        
        # Charger les anciens enregistrements
        self._load_existing_records()
    
    def _load_existing_records(self):
        """Charge les enregistrements existants depuis le CSV"""
        if self.config.csv_output.exists():
            try:
                with open(self.config.csv_output, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f, delimiter=';')
                    for row in reader:
                        if 'lien' in row and row['lien']:
                            self.processed_pdfs.add(row['lien'])
                            self.pdf_records.append(row)
                logging.info(f"✓ Chargé {len(self.pdf_records)} PDF depuis CSV existant")
            except Exception as e:
                logging.warning(f"Erreur chargement CSV: {e}")
    
    def extraire_date_page(self, soup: BeautifulSoup, url: str) -> str:
        """Extrait la date de publication d'une page"""
        # Meta tags
        meta_selectors = [
            ('meta[property="article:published_time"]', 'content'),
            ('meta[name="date"]', 'content'),
            ('meta[property="og:published_time"]', 'content'),
            ('meta[name="dc.date"]', 'content'),
        ]
        
        for selector, attr in meta_selectors:
            meta = soup.select_one(selector)
            if meta and meta.get(attr):
                date_str = meta[attr]
                parsed = self._parse_date(date_str)
                if parsed:
                    return parsed
        
        # Classes de date
        date_classes = ['.date', '.post-date', '.published', '.entry-date', '.article-date']
        for selector in date_classes:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                parsed = self._parse_date(date_text)
                if parsed:
                    return parsed
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse une chaîne de date"""
        if not date_str:
            return None
        
        date_str = date_str.strip()
        formats = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%dT%H:%M:%S']
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
    
    def determiner_type_document(self, url: str, title: str, section: str) -> str:
        """Détermine le type de document"""
        text = (title + " " + section + " " + url).lower()
        
        types_map = {
            'rapport_annuel': ['rapport annuel', 'annual report', 'rapport d\'activité'],
            'note_etude': ['note d\'étude', 'note de recherche', 'working paper', 'étude'],
            'note_conjoncture': ['note de conjoncture', 'conjoncture'],
            'decision': ['décision', 'decision', 'arrete', 'arrêté'],
            'reglement': ['règlement', 'reglement', 'instruction'],
            'communique': ['communiqué', 'communique', 'press release'],
            'bulletin': ['bulletin', 'newsletter'],
            'statistique': ['statistique', 'statistics', 'data'],
            'presentation': ['présentation', 'presentation', 'slide'],
        }
        
        for doc_type, keywords in types_map.items():
            if any(kw in text for kw in keywords):
                return doc_type
        
        return 'document'
    
    def ajouter_pdf(self, pdf_info: Dict[str, str], extraire_texte: bool = True):
        """
        Ajoute un PDF téléchargé avec ses métadonnées
        Si extraire_texte=True, tente d'extraire le contenu du PDF
        """
        lien = pdf_info.get('lien', '')
        with self.lock:
            if lien in self.processed_pdfs:
                return
            self.processed_pdfs.add(lien)
        
        # Ajouter timestamp
        if 'date_extraction' not in pdf_info:
            pdf_info['date_extraction'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Extraire le contenu du PDF si demandé et si le fichier existe
        contenu_pdf = ""
        chemin_txt = None
        
        if extraire_texte and 'chemin_absolu' in pdf_info:
            chemin_pdf = Path(pdf_info['chemin_absolu'])
            if chemin_pdf.exists():
                # Extraire le texte
                texte, _ = self.pdf_extractor.extraire_texte(chemin_pdf)
                if texte:
                    # Limiter la taille pour le CSV (premiers 5000 caractères)
                    contenu_pdf = texte[:5000] + ("..." if len(texte) > 5000 else "")
                    
                    # Sauvegarder le texte complet dans le dossier text_dir
                    chemin_txt = self.pdf_extractor.sauvegarder_texte_pdf(
                        chemin_pdf, self.config.text_dir, texte
                    )
                    if chemin_txt:
                        pdf_info['chemin_texte'] = str(chemin_txt)
        
        pdf_info['contenu_pdf'] = contenu_pdf
        
        with self.lock:
            self.pdf_records.append(pdf_info)
        
        # Sauvegarder immédiatement
        self.sauvegarder_csv()
    
    def sauvegarder_csv(self):
        """Exporte tous les PDF vers le CSV"""
        with self.lock:
            records = list(self.pdf_records)
        
        if not records:
            return
        
        # Colonnes (avec la nouvelle colonne contenu_pdf)
        fieldnames = [
            'chemin_relatif',      # Chemin local du fichier PDF
            'chemin_texte',        # Chemin du fichier texte extrait (nouveau)
            'date_publication',    # Date de publication
            'nom_pdf',             # Nom du fichier PDF
            'lien',                # URL source
            'module',              # Module BEAC
            'section',             # Section spécifique
            'sous_section',        # Sous-section
            'page_source',         # Page source
            'date_extraction',     # Date d'extraction
            'taille_ko',           # Taille en Ko
            'type_document',       # Type de document
            'contenu_pdf'          # Contenu texte du PDF (NOUVEAU)
        ]
        
        try:
            temp_output = self.config.csv_output.with_suffix(self.config.csv_output.suffix + ".tmp")
            with open(temp_output, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                writer.writerows(records)
            temp_output.replace(self.config.csv_output)
            
            logging.info(f"💾 CSV mis à jour: {len(records)} PDFs")
            
        except Exception as e:
            logging.error(f"Erreur sauvegarde CSV: {e}")

# ══════════════════════════════════════════════════════════════════
#  STRUCTURE STATIQUE CORRIGÉE
# ══════════════════════════════════════════════════════════════════

class StaticStructure:
    """Structure statique du site BEAC - URLs vérifiées"""
    
    MAIN_MODULES = {
        "la_beac": {"url": "/beac/", "title": "La BEAC", "priority": 10},
        "politique_monetaire": {"url": "/politique-monetaire/", "title": "Politique monétaire", "priority": 9},
        "supervision_bancaire": {"url": "/supervision-bancaire/", "title": "Supervision bancaire", "priority": 9},
        "economie_statistiques": {"url": "/economie-stats/", "title": "Économie et statistiques", "priority": 8},
        "publications": {"url": "/publications/", "title": "Publications", "priority": 10},
        "politique_changes": {"url": "/politique-des-changes/", "title": "Politique des changes", "priority": 7},
        "systemes_paiement": {"url": "/systemes-de-paiement/", "title": "Systèmes de paiement", "priority": 7},
        "marche_titres": {"url": "/marche-des-titres-publics/", "title": "Marché des titres publics", "priority": 8},
        "billets_pieces": {"url": "/billets-et-pieces/", "title": "Billets et pièces", "priority": 6}
    }
    
    @classmethod
    def get_entry_points(cls) -> List[Dict[str, Any]]:
        entry_points = []
        for key, module in cls.MAIN_MODULES.items():
            entry_points.append({
                "key": key,
                "title": module["title"],
                "url": module["url"],
                "depth": 0,
                "priority": module["priority"],
                "source": "static"
            })
        return entry_points

# ══════════════════════════════════════════════════════════════════
#  DÉCOUVERTE DYNAMIQUE
# ══════════════════════════════════════════════════════════════════

class DynamicDiscovery:
    """Découverte dynamique des liens"""
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.discovered_urls: Set[str] = set()
    
    def discover_from_page(self, soup: BeautifulSoup, current_url: str, 
                          current_depth: int) -> List[Dict[str, Any]]:
        """Découvre les liens depuis une page"""
        if current_depth >= self.config.max_depth:
            return []
        
        discovered = []
        
        strategies = [
            self._discover_nav_menu,
            self._discover_sidebar,
            self._discover_content_links,
        ]
        
        for strategy in strategies:
            links = strategy(soup, current_url, current_depth)
            for link in links:
                if link["url"] not in self.discovered_urls:
                    self.discovered_urls.add(link["url"])
                    discovered.append(link)
        
        return discovered
    
    def _discover_nav_menu(self, soup: BeautifulSoup, current_url: str, 
                           depth: int) -> List[Dict[str, Any]]:
        links = []
        nav_selectors = ["nav.main-navigation", ".menu-principal-container", "header nav"]
        
        for selector in nav_selectors:
            nav = soup.select_one(selector)
            if nav:
                for a in nav.find_all("a", href=True):
                    link = self._process_link(a, current_url, depth + 1)
                    if link:
                        links.append(link)
                break
        return links
    
    def _discover_sidebar(self, soup: BeautifulSoup, current_url: str, 
                         depth: int) -> List[Dict[str, Any]]:
        links = []
        sidebar = soup.select_one("#secondary, .sidebar, .widget-area")
        if sidebar:
            for a in sidebar.find_all("a", href=True):
                link = self._process_link(a, current_url, depth + 1)
                if link:
                    links.append(link)
        return links
    
    def _discover_content_links(self, soup: BeautifulSoup, current_url: str, 
                               depth: int) -> List[Dict[str, Any]]:
        links = []
        content = soup.find("main") or soup.find("article") or soup.find("body")
        if content:
            for a in content.find_all("a", href=True):
                link = self._process_link(a, current_url, depth + 1)
                if link and len(a.get_text(strip=True)) > 3:
                    links.append(link)
        return links
    
    def _process_link(self, a_tag, base_url: str, depth: int) -> Optional[Dict[str, Any]]:
        href = a_tag.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return None
        
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        
        if parsed.netloc not in ["", "www.beac.int", "beac.int"]:
            return None
        
        full_url = parsed._replace(fragment="").geturl()
        path = parsed.path.rstrip('/')
        url_to_check = full_url.lower()
        if not path or any(exclude in url_to_check for exclude in self.config.exclude_paths):
            return None
        
        if Path(path).suffix.lower() in self.config.doc_extensions:
            return None
        
        title = a_tag.get_text(strip=True)
        if not title or len(title) < 2:
            title = path.split("/")[-1].replace("-", " ").title()
        
        return {
            "url": full_url,
            "path": path,
            "title": title[:100],
            "depth": depth,
            "source": "dynamic"
        }

# ══════════════════════════════════════════════════════════════════
#  SCRAPER PRINCIPAL
# ══════════════════════════════════════════════════════════════════

class BEACScraper:
    """Scraper principal avec extraction du texte des PDF"""
    
    MODULE_FOLDERS = {
        "beac": "La beac",
        "billets-et-pieces": "Billets et pieces",
        "economie-stats": "Economie et statistique",
        "marche-des-titres-publics": "Marche des titres publics",
        "politique-des-changes": "Politique des changes",
        "politique-monetaire": "Politique monetaire",
        "publications": "Publications",
        "supervision-bancaire": "Supervision bancaire",
        "systemes-de-paiement": "Systemes de paiement",
    }
    
    SECTION_FOLDERS = {
        "authentification-des-signes-monetaires": "Authentification des signes monétaires",
        "histoire-du-franc-cfa": "Histoire du Franc CFA",
        "role-de-la-beac": "Rôle de la BEAC",
        "signes-monetaires": "Signes monétaires",
        "echanges-de-billets-deteriores-et-demonetises": "Échanges de billets détériorés et démonétisés",
        "base-de-donnees-economiques-monetaires-financieres": "Base de Données Économiques, Monétaires et Financières",
        "statistiques-de-balance-paiements": "Statistiques de la Balance des Paiements",
        "statistiques-de-lemission-monetaire": "Statistiques de l’Emission Monétaire",
        "statistiques-systemes-de-paiement": "Statistiques des Systèmes de Paiement",
        "statistiques-titres-publics": "Statistiques des Titres Publics",
        "statistiques-marche-monetaire": "Statistiques du Marché Monétaire",
        "statistiques-economiques": "Statistiques Economiques",
        "statistiques-monetaires": "Statistiques Monétaires",
        "communiques-de-presse": "Communiqués de presse",
        "la-beac": "la beac",
        "fonctionnement-de-la-beac": "Le Fonctionnement de la BEAC",
        "gouvernement-de-la-banque": "Le Gouvernement de la Banque",
        "mises-en-concurrence": "Mises en concurrence",
        "programme-de-stages-academiques-a-la-beac": "Programme de stages académiques à la BEAC",
        "projets-en-cours": "Projets en cours",
        "travailler-a-la-beac": "Travailler à la BEAC",
        "annonces-et-communiques": "Annonces et Communiqués",
        "cadre-reglementaire": "Cadre réglementaire",
        "calendriers-trimestriels-demissions-des-titres": "Calendriers trimestriels d’émissions des Titres",
        "presentation-generale-du-marche-des-titres-publics": "Présentation Générale du Marché des Titres Publics",
        "publics-des-etats-de-la-cemac": "Publics des États de la CEMAC",
        "circulaires-et-decisions": "Circulaires et décisions",
        "communiques": "Communiqués",
        "formulaires": "Formulaires",
        "instructions": "Instructions",
        "presentation-generale-de-la-politique-de-change": "Présentation générale de la Politique de Change",
        "reglements": "Règlements",
        "appels-doffres": "Appels d’offres",
        "calendrier-des-reunions-du-comite-de-politique": "Calendrier des réunions du Comité de Politique",
        "decisions-de-politique-monetaire": "Décisions de politique monétaire",
        "comite-de-politique-monetaire": "Le Comité de Politique Monétaire de la BEAC",
        "marche-monetaire-de-la-cemac": "Marché Monétaire de la CEMAC",
        "monetaire": "Monétaire",
        "programmation-monetaire-de-la-beac": "Programmation monétaire de la BEAC",
        "strategie-de-politique-monetaire": "Stratégie de politique monétaire",
        "elements-methodologiques": "éléments méthodologiques",
        "bulletin-des-couts-et-conditions-du-credit": "Bulletin des Coûts et Conditions du Crédit",
        "etats-financiers": "Etats financiers",
        "notes-de-conjoncture": "Notes de Conjoncture",
        "notes-detudes-et-de-recherches": "Notes d’Etudes et de Recherches",
        "occasional-papers": "Occasional papers",
        "rapports-annuels-de-la-banque": "Rapports Annuels de la Banque",
        "situations-comptables": "Situations Comptables",
        "tests-previsionnels-de-conjoncture": "Tests Prévisionnels de Conjoncture",
        "working-papers": "Working Papers",
        "instructions-de-la-cobac": "Instructions de la COBAC",
        "commission-bancaire-de-lafrique-centrale": "La Commission Bancaire de l’Afrique Centrale",
        "lexique-des-banques-de-la-cemac": "Lexique des Banques de la CEMAC",
        "lexique-des-etablissements-financiers": "Lexique des établissements financiers",
        "microfinance": "Microfinance",
        "reglements-de-la-cobac": "Règlements de la COBAC",
        "instructions-circulaires-et-reglements": "Instructions, Circulaires et Règlements",
        "reforme-des-systemes-et-moyens-de-paiement-de-la-cemac": "Réforme des systèmes et moyens de paiement de la CEMAC",
        "systeme-de-gros-montants-automatise-sygma": "Système de Gros Montants Automatisé (SYGMA)",
        "systeme-de-monetique-interbancaire": "Système de Monétique Interbancaire",
        "systeme-de-telecompensation-en-afrique-centrale-systac": "Système de Télécompensation en Afrique Centrale (SYSTAC)",
    }
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.session = self._create_session()
        self.dynamic_discovery = DynamicDiscovery(config)
        self.pdf_manager = PDFManager(config)
        self.processed_urls: Set[str] = set()
        self.queued_urls: Set[str] = set()
        self.url_queue = deque()
        self.lock = threading.Lock()
        self.robots_parser = self._load_robots_parser()
        
        self.stats = {
            "pages": 0,
            "documents": 0,
            "textes_extraits": 0,
            "dynamic_discoveries": 0,
            "errors": 0,
            "cache_hits": 0
        }
        
        self.checkpoint_file = config.cache_dir / "checkpoint.json"
        self._load_checkpoint()
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "BEAC-DataCollector/1.0 (+https://www.beac.int)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        })
        return session
    
    def _load_robots_parser(self) -> Optional[urllib.robotparser.RobotFileParser]:
        if not self.config.respect_robots_txt:
            return None
        robots_url = urljoin(self.config.base_url + "/", "robots.txt")
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
            return parser
        except Exception as e:
            logging.warning(f"Impossible de lire robots.txt: {e}")
            return None
    
    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(urljoin(self.config.base_url + "/", url))
        return parsed._replace(fragment="").geturl()
    
    def _can_fetch(self, url: str) -> bool:
        if not self.robots_parser:
            return True
        user_agent = self.session.headers.get("User-Agent", "*")
        try:
            return self.robots_parser.can_fetch(user_agent, url)
        except Exception as e:
            logging.warning(f"Erreur vérification robots.txt pour {url}: {e}")
            return True
    
    def _increment_stat(self, key: str, value: int = 1):
        with self.lock:
            self.stats[key] = self.stats.get(key, 0) + value
    
    def _safe_path_part(self, value: str, fallback: str = "general") -> str:
        value = unquote(value or "").strip().lower()
        value = re.sub(r'[<>:"/\\|?*\s]+', '_', value)
        value = re.sub(r'_+', '_', value).strip("._-")
        return value[:80] or fallback
    
    def _safe_folder_name(self, value: str, fallback: str = "General") -> str:
        value = unquote(value or "").strip()
        value = re.sub(r'[<>:"/\\|?*]+', ' ', value)
        value = re.sub(r'\s+', ' ', value).strip(" ._-")
        return value[:120] or fallback
    
    def _folder_from_slug(self, slug: str, mapping: Dict[str, str], fallback: str) -> str:
        slug = unquote(slug or "").strip("/")
        return self._safe_folder_name(mapping.get(slug, slug.replace("-", " ").title()), fallback)
    
    def _safe_filename(self, title: str, url: str, ext: str) -> str:
        parsed_name = Path(unquote(urlparse(url).path)).stem
        base_name = title.strip() or parsed_name or "document"
        base_name = re.sub(r'[<>:"/\\|?*\s]+', '_', base_name)
        base_name = re.sub(r'_+', '_', base_name).strip("._-")
        if not base_name:
            base_name = "document"
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
        return f"{base_name[:90]}_{url_hash}{ext}"
    
    def _load_checkpoint(self):
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_urls = {self._normalize_url(url) for url in data.get("processed_urls", [])}
                    self.stats = data.get("stats", self.stats)
                logging.info(f"✓ Checkpoint: {len(self.processed_urls)} URLs traitées")
            except Exception as e:
                logging.warning(f"Erreur checkpoint: {e}")
    
    def _save_checkpoint(self):
        try:
            with self.lock:
                processed_urls = list(self.processed_urls)
                stats = dict(self.stats)
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "processed_urls": processed_urls,
                    "stats": stats,
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logging.warning(f"Erreur sauvegarde checkpoint: {e}")
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        url = self._normalize_url(url)
        if not self._can_fetch(url):
            logging.warning(f"Accès interdit par robots.txt: {url}")
            self._increment_stat("errors")
            return None
        
        cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_file = self.config.cache_dir / f"{cache_key}.html"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self._increment_stat("cache_hits")
                    return BeautifulSoup(f.read(), "lxml")
            except Exception as e:
                logging.debug(f"Erreur lecture cache {cache_file}: {e}")
        
        for attempt in range(1, self.config.retries + 1):
            try:
                time.sleep(self.config.delay)
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                
                if response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding or 'utf-8'
                
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                
                return BeautifulSoup(response.text, "lxml")
                
            except requests.RequestException as e:
                logging.warning(f"Erreur {url} (tentative {attempt}): {e}")
                if attempt == self.config.retries:
                    self._increment_stat("errors")
                    return None
                time.sleep(self.config.backoff_factor ** attempt)
        
        return None
    
    def sauvegarder_document(self, doc_url: str, filename: str, docs_dir: Path,
                             metadata: Dict[str, str]) -> bool:
        """Télécharge un document et extrait son texte"""
        doc_url = self._normalize_url(doc_url)
        if not self._can_fetch(doc_url):
            logging.warning(f"  ✗ Document interdit par robots.txt: {doc_url}")
            self._increment_stat("errors")
            return False
        
        filepath = docs_dir / filename
        
        # Si le fichier existe déjà, ne pas retélécharger
        if filepath.exists():
            size_kb = filepath.stat().st_size / 1024
            metadata['taille_ko'] = f"{size_kb:.1f}"
            metadata['chemin_absolu'] = str(filepath)
            self.pdf_manager.ajouter_pdf(metadata, extraire_texte=True)
            return True
        
        for attempt in range(1, self.config.retries + 1):
            try:
                time.sleep(self.config.delay)
                response = self.session.get(doc_url, stream=True, timeout=self.config.timeout)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                
                # Métadonnées du fichier
                size_kb = filepath.stat().st_size / 1024
                metadata['taille_ko'] = f"{size_kb:.1f}"
                metadata['chemin_absolu'] = str(filepath)
                
                # Ajouter au gestionnaire avec extraction du texte
                self.pdf_manager.ajouter_pdf(metadata, extraire_texte=True)
                
                self._increment_stat("documents")
                logging.info(f"  ✓ PDF: {filename} ({size_kb:.0f} Ko)")
                return True
                
            except Exception as e:
                logging.warning(f"  ✗ Erreur {filename}: {e}")
                if attempt == self.config.retries:
                    return False
                time.sleep(self.config.backoff_factor ** attempt)
        
        return False
    
    def traiter_url(self, url_info: Dict):
        """Traite une URL"""
        url = self._normalize_url(url_info["url"])
        url_info["url"] = url
        
        with self.lock:
            if url in self.processed_urls or self.stats.get("pages", 0) >= self.config.max_pages:
                return
        
        logging.info(f"\n▶ {url_info.get('title', url)}")
        
        soup = self.fetch_page(url)
        if not soup:
            return
        
        # Extraire les infos de module/section
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        module_slug = path_parts[0] if path_parts else "general"
        module = self._folder_from_slug(module_slug, self.MODULE_FOLDERS, "General")
        section_source = path_parts[1] if len(path_parts) > 1 else url_info.get("title", "page")
        section = self._folder_from_slug(section_source, self.SECTION_FOLDERS, "General")
        
        # Dossier des PDFs
        docs_dir = self.config.root_dir / module / section
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Extraire et télécharger les PDFs
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href:
                continue
            
            ext = Path(urlparse(href).path).suffix.lower()
            if ext in self.config.doc_extensions:
                pdf_url = urljoin(url, href)
                pdf_title = a.get_text(strip=True)
                
                if not pdf_title:
                    pdf_title = Path(urlparse(pdf_url).path).stem
                
                # Nettoyer le nom
                filename = self._safe_filename(pdf_title, pdf_url, ext)
                
                # Date de publication
                date_pub = self.pdf_manager.extraire_date_page(soup, url)
                
                # Type de document
                doc_type = self.pdf_manager.determiner_type_document(pdf_url, pdf_title, section)
                
                # Métadonnées pour CSV
                metadata = {
                    'chemin_relatif': str((docs_dir / filename).relative_to(self.config.root_dir)),
                    'date_publication': date_pub,
                    'nom_pdf': pdf_title,
                    'lien': pdf_url,
                    'module': module,
                    'section': section,
                    'sous_section': '',
                    'page_source': url,
                    'type_document': doc_type
                }
                
                self.sauvegarder_document(pdf_url, filename, docs_dir, metadata)
        
        # Découverte dynamique
        new_urls = self.dynamic_discovery.discover_from_page(soup, url, url_info.get("depth", 0))
        if new_urls:
            self._increment_stat("dynamic_discoveries", len(new_urls))
            for new_url in new_urls:
                normalized_new_url = self._normalize_url(new_url["url"])
                new_url["url"] = normalized_new_url
                with self.lock:
                    should_queue = (
                        normalized_new_url not in self.processed_urls
                        and normalized_new_url not in self.queued_urls
                        and len(self.processed_urls) + len(self.queued_urls) < self.config.max_pages
                    )
                if should_queue:
                    self.url_queue.append(new_url)
                    with self.lock:
                        self.queued_urls.add(normalized_new_url)
        
        with self.lock:
            self.processed_urls.add(url)
            self.queued_urls.discard(url)
            self.stats["pages"] += 1
        
        with self.lock:
            should_checkpoint = len(self.processed_urls) % 10 == 0
        if should_checkpoint:
            self._save_checkpoint()
            self.pdf_manager.sauvegarder_csv()
    
    def scraper(self):
        """Point d'entrée principal"""
        logging.info("=" * 70)
        logging.info("BEAC SCRAPER v5.0 - AVEC EXTRACTION TEXTE DES PDF")
        logging.info(f"Démarrage: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        logging.info(f"📁 PDFs: {self.config.root_dir}")
        logging.info(f"📄 Textes: {self.config.text_dir}")
        logging.info(f"📊 CSV: {self.config.csv_output}")
        logging.info("=" * 70)
        
        # Initialiser la queue
        entry_points = StaticStructure.get_entry_points()
        for entry in entry_points:
            entry["url"] = self._normalize_url(entry["url"])
            if entry["url"] not in self.processed_urls and entry["url"] not in self.queued_urls:
                self.url_queue.append(entry)
                self.queued_urls.add(entry["url"])
        
        logging.info(f"📋 Points d'entrée: {len(entry_points)}\n")
        
        # Traitement
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = set()
            
            while self.url_queue or futures:
                while len(futures) < self.config.max_workers and self.url_queue:
                    with self.lock:
                        if self.stats.get("pages", 0) >= self.config.max_pages:
                            self.url_queue.clear()
                            break
                    url_info = self.url_queue.popleft()
                    future = executor.submit(self.traiter_url, url_info)
                    futures.add(future)
                
                if not futures:
                    continue
                
                done, futures = wait(futures, timeout=1, return_when=FIRST_COMPLETED)
                for future in done:
                    try:
                        future.result()
                    except Exception as e:
                        logging.exception(f"Erreur inattendue pendant le traitement d'une URL: {e}")
                        self._increment_stat("errors")
        
        # Rapport final
        self._generer_rapport()
    
    def _generer_rapport(self):
        """Génère rapport final"""
        self._save_checkpoint()
        self.pdf_manager.sauvegarder_csv()
        
        # Compter les textes extraits
        textes_count = len(list(self.config.text_dir.rglob("*.txt")))
        
        rapport = {
            "date": datetime.now().isoformat(),
            "stats": self.stats,
            "pdfs_exportes": len(self.pdf_manager.pdf_records),
            "textes_extraits": textes_count,
            "pdf_directory": str(self.config.root_dir),
            "text_directory": str(self.config.text_dir),
            "csv_file": str(self.config.csv_output)
        }
        
        rapport_file = self.config.root_dir / "rapport_final.json"
        with open(rapport_file, 'w', encoding='utf-8') as f:
            json.dump(rapport, f, ensure_ascii=False, indent=2)
        
        logging.info("\n" + "=" * 70)
        logging.info("  RAPPORT FINAL")
        logging.info(f"  ✓ Pages scrapées: {self.stats['pages']}")
        logging.info(f"  ✓ PDFs téléchargés: {self.stats['documents']}")
        logging.info(f"  📄 Textes extraits des PDF: {textes_count}")
        logging.info(f"  📊 PDFs dans CSV: {len(self.pdf_manager.pdf_records)}")
        logging.info(f"  📁 Dossier PDFs: {self.config.root_dir}")
        logging.info(f"  📁 Dossier textes: {self.config.text_dir}")
        logging.info(f"  📁 CSV: {self.config.csv_output}")
        logging.info(f"  ✗ Erreurs: {self.stats['errors']}")
        logging.info("=" * 70)

# ══════════════════════════════════════════════════════════════════
#  EXÉCUTION
# ══════════════════════════════════════════════════════════════════

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("beac_scraper_v5.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    
    config = ScraperConfig()
    scraper = BEACScraper(config)
    scraper.scraper()

if __name__ == "__main__":
    main()