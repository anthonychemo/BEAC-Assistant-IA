"""Extraction de texte PDF avec bascule automatique vers l'OCR.

Strategie :
1. On tente l'extraction native (PyMuPDF) - rapide, parfaite pour PDF natifs.
2. Si le texte natif est trop pauvre (< seuil), on bascule en OCR (Tesseract)
   page par page via pdf2image + pytesseract, parallelise sur plusieurs coeurs.
3. Si l'OCR ne retourne rien (PDF image/graphique pur), on extrait les images
   brutes du PDF et on genere un texte descriptif pour le referencement RAG.
"""
from __future__ import annotations

import io
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF
import pytesseract

# Désactive les logs MuPDF pour éviter l'affichage des erreurs de PDF corrompus
fitz.TOOLS.mupdf_warnings(False)
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

from src.config import CONFIG, settings
from src.utils.logger import logger

_ING = CONFIG.get("ingestion", {})
_OCR_THRESHOLD = int(_ING.get("ocr_text_threshold", 100))
_OCR_DPI = int(_ING.get("ocr_dpi", 300))

_OCR_MAX_PAGES_PARALLEL = int(_ING.get("ocr_workers", 4))  # déjà géré

_OCR_WORKERS = int(_ING.get("ocr_workers", 0))
if _OCR_WORKERS <= 0:
    _OCR_WORKERS = max(1, (os.cpu_count() or 4) // 2)

_IMAGE_DIR = _ING.get("image_extract_dir")
if _IMAGE_DIR:
    _IMAGE_DIR = Path(_IMAGE_DIR)
    if not _IMAGE_DIR.is_absolute():
        _IMAGE_DIR = (Path(__file__).resolve().parents[2] / _IMAGE_DIR).resolve()
    _IMAGE_DIR.mkdir(parents=True, exist_ok=True)

# Configuration Tesseract (Windows)
if settings.tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


@dataclass
class PdfExtractionResult:
    text: str
    method: str  # "native" | "ocr" | "image_extracted"
    page_count: int
    image_paths: list[str] = field(default_factory=list)
    char_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


def _extract_native(path: Path) -> tuple[str, int]:
    """Extraction texte native via PyMuPDF."""
    try:
        texts: list[str] = []
        with fitz.open(path) as doc:
            page_count = doc.page_count
            for page in doc:
                text = page.get_text("text")
                # Nettoyage des caracteres de controle invalides pour PostgreSQL
                text = text.replace("\x00", " ").replace("\x07", " ")
                texts.append(text)
        return "\n".join(texts).strip(), page_count
    except Exception as exc:
        logger.error(f"PDF corrompu ou illisible ({path.name}): {exc}")
        return "", 0


def _ocr_page(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang=settings.ocr_langs)


def _ocr_single_page(args: tuple[str, int, str, int, str]) -> str:
    """Worker picklable pour l'OCR d'une page (utilise par ProcessPoolExecutor)."""
    path_str, page_num, poppler, dpi, ocr_langs = args
    try:
        images = convert_from_path(
            path_str,
            dpi=dpi,
            poppler_path=poppler or None,
            first_page=page_num,
            last_page=page_num,
        )
    except Exception:
        return ""
    texts: list[str] = []
    for image in images:
        try:
            text = pytesseract.image_to_string(image, lang=ocr_langs)
            # Nettoyage des caracteres de controle invalides pour PostgreSQL
            text = text.replace("\x00", " ").replace("\x07", " ")
            texts.append(text)
        except Exception:
            pass
        finally:
            image.close()
    return "\n".join(texts)


def _extract_ocr(path: Path) -> str:
    """OCR complet du PDF, page par page, parallelise sur _OCR_WORKERS coeurs.

    Utilise ProcessPoolExecutor pour lancer plusieurs instances Tesseract
    simultanement et reduire le temps d'OCR des PDF multi-pages.
    """
    poppler = settings.poppler_path or ""

    try:
        info = pdfinfo_from_path(str(path), poppler_path=poppler or None)
        n_pages = int(info["Pages"])
    except Exception as exc:
        logger.error(f"OCR info echouee pour {path.name}: {exc}")
        return ""

    # Prepare les arguments pour chaque page
    args_list = [
        (str(path), page_num, poppler, _OCR_DPI, settings.ocr_langs)
        for page_num in range(1, n_pages + 1)
    ]

    texts: list[str] = [""] * n_pages
    with ProcessPoolExecutor(max_workers=_OCR_WORKERS) as executor:
        future_to_page = {
            executor.submit(_ocr_single_page, args): idx
            for idx, args in enumerate(args_list)
        }
        for future in as_completed(future_to_page):
            idx = future_to_page[future]
            try:
                texts[idx] = future.result()
            except Exception as exc:
                logger.warning(f"OCR page {idx + 1} echouee ({path.name}): {exc}")

    return "\n".join(t for t in texts if t).strip()


def _extract_images(path: Path) -> tuple[list[str], str]:
    """Extrait les images d'un PDF graphique pur et genere un texte descriptif.

    Retourne (liste des chemins d'images sauvegardees, texte descriptif).
    """
    if not _IMAGE_DIR:
        return [], ""

    saved: list[str] = []
    doc_folder = _IMAGE_DIR / path.stem
    doc_folder.mkdir(parents=True, exist_ok=True)

    with fitz.open(path) as doc:
        for page_idx in range(doc.page_count):
            page = doc[page_idx]
            img_list = page.get_images(full=True)
            for img_idx, img in enumerate(img_list, start=1):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    img_path = doc_folder / f"page_{page_idx + 1}_img_{img_idx}.{ext}"
                    with img_path.open("wb") as f:
                        f.write(image_bytes)
                    # Stocke le chemin relatif pour l'API : doc_name/filename
                    saved.append(f"{doc_folder.name}/{img_path.name}")
                except Exception as exc:
                    logger.debug(f"Image extraction failed {path.name} p{page_idx}: {exc}")

    # Genere un texte descriptif basique a partir du nom de fichier
    desc = (
        f"Document graphique : {path.stem.replace('_', ' ')}. "
        f"Ce fichier contient {len(saved)} image(s) ou graphique(s). "
        f"Cela peut etre une courbe, un tableau ou un schema non textuel."
    )
    logger.info(f"Images extraites ({len(saved)}) pour {path.name}")
    return saved, desc


def extract_pdf_text(path: str | Path) -> PdfExtractionResult:
    """Extrait le texte d'un PDF (natif -> OCR -> images descriptives)."""
    path = Path(path)
    native_text, page_count = _extract_native(path)

    # PDF corrompu : page_count = 0
    if page_count == 0:
        logger.warning(f"PDF ignore (corrompu) : {path.name}")
        return PdfExtractionResult(text="", method="error", page_count=0)

    # Heuristique : assez de texte natif -> on garde
    if len(native_text) >= _OCR_THRESHOLD:
        return PdfExtractionResult(text=native_text, method="native", page_count=page_count)

    logger.info(f"PDF scanne detecte, OCR en cours : {path.name}")
    ocr_text = _extract_ocr(path)

    # Si l'OCR donne plus de contenu, on le prend
    if len(ocr_text) > len(native_text):
        return PdfExtractionResult(text=ocr_text, method="ocr", page_count=page_count)

    # Fallback : PDF image/graphique pur -> extraction des images + description
    if not native_text.strip() and not ocr_text.strip():
        img_paths, desc = _extract_images(path)
        if img_paths:
            return PdfExtractionResult(
                text=desc, method="image_extracted", page_count=page_count,
                image_paths=img_paths,
            )

    return PdfExtractionResult(text=native_text, method="native", page_count=page_count)
