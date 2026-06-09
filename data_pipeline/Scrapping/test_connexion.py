#!/usr/bin/env python3
"""
Test rapide : vérifie robots.txt et accessibilité de quelques pages BEAC
"""
import requests
import time
from bs4 import BeautifulSoup

BASE_URL = "https://www.beac.int"
HEADERS = {
    "User-Agent": "BEAC-DataCollector/1.0 (recherche; contact@example.cm)",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

URLS_TEST = [
    "/",
    "/robots.txt",
    "/beac/la-beac/",
    "/publications/",
    "/economie-stats/",
    "/politique-monetaire/",
]

session = requests.Session()
session.headers.update(HEADERS)

print("=" * 55)
print("  TEST DE CONNEXION — BEAC.INT")
print("=" * 55)

for path in URLS_TEST:
    url = BASE_URL + path
    try:
        resp = session.get(url, timeout=30)
        status = resp.status_code
        size = len(resp.text)
        
        # Compter les liens et PDFs si c'est du HTML
        n_links = 0
        n_pdfs = 0
        if "html" in resp.headers.get("content-type", ""):
            soup = BeautifulSoup(resp.text, "lxml")
            links = soup.find_all("a", href=True)
            n_links = len(links)
            n_pdfs = sum(1 for a in links if ".pdf" in a["href"].lower())
        
        icon = "✓" if status == 200 else "✗"
        print(f"\n{icon} {path}")
        print(f"   Statut : {status} | Taille : {size:,} octets")
        if n_links:
            print(f"   Liens  : {n_links} dont {n_pdfs} PDF(s)")
        if path == "/robots.txt":
            print(f"   Contenu robots.txt :")
            for line in resp.text.split("\n")[:15]:
                if line.strip():
                    print(f"     {line}")
                    
    except requests.Timeout as e:
        print(f"\n⚠ {path}")
        print(f"   TIMEOUT : {e}")
    except Exception as e:
        print(f"\n✗ {path}")
        print(f"   ERREUR : {e}")
    
    time.sleep(1.5)

print("\n" + "=" * 55)
print("  Test terminé. Consultez les résultats ci-dessus.")
print("=" * 55)
