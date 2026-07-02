#!/usr/bin/env python3
"""
Exemple complet d'utilisation de toutes les fonctionnalités PDF avancées
Démontre les 5 points d'amélioration
"""

import logging
import time
from pathlib import Path
from pdf_advanced import (
    PDFMetadataExtractor,
    TableExtractor,
    PDFMonitor,
    PDFBatchProcessor
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def exemple_metadata():
    """Démo 2️⃣ - Extraction de métadonnées"""
    print("\n" + "="*60)
    print("2️⃣  EXTRACTION DE MÉTADONNÉES ENRICHIES")
    print("="*60)
    
    extractor = PDFMetadataExtractor()
    
    # Exemple avec un PDF test
    pdf_test = Path("scraping/beac_data")
    
    # Trouver les premiers PDFs
    pdfs = list(pdf_test.rglob("*.pdf"))[:3]
    
    if pdfs:
        for pdf in pdfs:
            print(f"\n📋 {pdf.name}")
            metadata = extractor.extraire_metadata(pdf)
            
            meta_dict = metadata.to_dict()
            for key, value in meta_dict.items():
                print(f"   {key}: {value}")
    else:
        print("⚠️  Aucun PDF trouvé pour la démo")


def exemple_tableaux():
    """Démo 3️⃣ - Extraction de tableaux"""
    print("\n" + "="*60)
    print("3️⃣  EXTRACTION DE TABLEAUX")
    print("="*60)
    
    extractor = TableExtractor()
    output_dir = Path("scraping/beac_tables")
    
    # Exemple avec un PDF test
    pdf_test = Path("scraping/beac_data")
    pdfs = list(pdf_test.rglob("*.pdf"))[:3]
    
    if pdfs:
        for pdf in pdfs:
            print(f"\n📊 Traitement: {pdf.name}")
            
            tableaux = extractor.extraire_tableaux(pdf)
            if tableaux:
                print(f"   ✓ {len(tableaux)} tableau(x) trouvé(s)")
                
                # Sauvegarder en plusieurs formats
                for format in ['csv', 'markdown', 'json']:
                    fichiers = extractor.sauvegarder_tableaux(pdf, output_dir, format)
                    if fichiers:
                        print(f"   ✓ Sauvegardé en {format}: {len(fichiers)} fichier(s)")
            else:
                print("   ℹ️  Aucun tableau détecté")
    else:
        print("⚠️  Aucun PDF trouvé pour la démo")


def exemple_monitoring():
    """Démo 4️⃣ - Monitoring et statistiques"""
    print("\n" + "="*60)
    print("4️⃣  MONITORING ET STATISTIQUES")
    print("="*60)
    
    monitor = PDFMonitor()
    
    # Simuler le traitement de PDFs
    pdfs_count = 10
    monitor.set_total_pdfs(pdfs_count)
    
    print(f"\n📊 Simulation de traitement de {pdfs_count} PDFs...\n")
    
    for i in range(pdfs_count):
        # Simuler le traitement
        num_pages = (i % 5) + 1
        num_chars = num_pages * 3000
        num_tables = (i % 3)
        is_ocr = i % 3 == 0  # Certains PDFs sont scannés
        time_taken = (i % 2) * 0.5 + 1.0
        
        monitor.record_success(
            num_pages=num_pages,
            num_chars=num_chars,
            num_tables=num_tables,
            is_ocr=is_ocr,
            time_taken=time_taken
        )
        
        print(f"✓ PDF {i+1}/{pdfs_count} - Pages: {num_pages}, OCR: {is_ocr}")
    
    # Afficher le rapport
    print(monitor.get_report())
    
    # Sauvegarder le rapport
    rapport_path = Path("scraping/rapport_traitement.txt")
    monitor.sauvegarder_rapport(rapport_path)


def exemple_batch_processing():
    """Démo 5️⃣ - Traitement par lot avec cache"""
    print("\n" + "="*60)
    print("5️⃣  OPTIMISATION DE PERFORMANCE - BATCH PROCESSING")
    print("="*60)
    
    processor = PDFBatchProcessor(batch_size=5, enable_cache=True)
    
    # Exemple de fonction de traitement
    def process_pdf(pdf_path: Path) -> dict:
        """Simule le traitement d'un PDF"""
        # Simuler du travail
        time.sleep(0.5)
        return {
            'file': pdf_path.name,
            'size': pdf_path.stat().st_size if pdf_path.exists() else 0,
            'processed': True
        }
    
    # Trouver les PDFs
    pdf_dir = Path("scraping/beac_data")
    pdf_list = list(pdf_dir.rglob("*.pdf"))[:5]
    
    if pdf_list:
        print(f"\n⚙️  Traitement de {len(pdf_list)} PDFs avec cache...\n")
        
        start_time = time.time()
        resultats = processor.traiter_lot(pdf_list, process_pdf)
        elapsed = time.time() - start_time
        
        print(f"\n✓ Traitement complet en {elapsed:.2f}s")
        print(f"✓ {len(resultats)} PDFs traités")
        
        # Deuxième passage pour montrer l'efficacité du cache
        print(f"\n⚙️  Deuxième passage (avec cache)...\n")
        
        start_time = time.time()
        resultats = processor.traiter_lot(pdf_list, process_pdf)
        elapsed = time.time() - start_time
        
        print(f"\n✓ Cache hit: traitement en {elapsed:.2f}s (plus rapide!)")
    else:
        print("⚠️  Aucun PDF trouvé pour la démo")


def exemple_pipeline_complet():
    """Démontre le pipeline complet"""
    print("\n" + "="*60)
    print("🚀 PIPELINE COMPLET")
    print("="*60)
    
    pdf_dir = Path("scraping/beac_data")
    pdfs = list(pdf_dir.rglob("*.pdf"))[:2]
    
    if not pdfs:
        print("⚠️  Aucun PDF trouvé")
        return
    
    metadata_extractor = PDFMetadataExtractor()
    table_extractor = TableExtractor()
    monitor = PDFMonitor()
    output_dir = Path("scraping/pdf_analysis")
    
    monitor.set_total_pdfs(len(pdfs))
    
    for pdf_path in pdfs:
        print(f"\n📄 Traitement: {pdf_path.name}")
        
        start_time = time.time()
        
        # 1. Métadonnées
        metadata = metadata_extractor.extraire_metadata(pdf_path)
        print(f"   ✓ Métadonnées: titre='{metadata.title}', pages={metadata.num_pages}")
        
        # 2. Tableaux
        tableaux = table_extractor.extraire_tableaux(pdf_path)
        if tableaux:
            table_extractor.sauvegarder_tableaux(pdf_path, output_dir / "tables", "csv")
            print(f"   ✓ Tableaux: {len(tableaux)} trouvé(s)")
        
        # 3. Record stats
        time_taken = time.time() - start_time
        monitor.record_success(
            num_pages=metadata.num_pages or 0,
            num_chars=1000,  # Simulé
            num_tables=len(tableaux),
            is_ocr=False,
            time_taken=time_taken
        )
    
    # Afficher le rapport final
    print(monitor.get_report())


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║  DÉMONSTRATION - 5 AMÉLIORATIONS PDF                      ║
╚════════════════════════════════════════════════════════════╝
    
1️⃣  Gestion PDFs scannés avec OCR        [scraper.py]
2️⃣  Métadonnées enrichies                 [pdf_advanced.py]
3️⃣  Extraction de tableaux                [pdf_advanced.py]
4️⃣  Monitoring et statistiques            [pdf_advanced.py]
5️⃣  Optimisation de performance           [pdf_advanced.py]
    """)
    
    try:
        # Exécuter les démos
        exemple_metadata()
        exemple_tableaux()
        exemple_monitoring()
        exemple_batch_processing()
        exemple_pipeline_complet()
        
        print("\n" + "="*60)
        print("✅ Toutes les démos complétées avec succès!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
