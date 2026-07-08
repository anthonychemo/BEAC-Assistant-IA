"""Expansion du vocabulaire utilisateur vers la terminologie institutionnelle BEAC/CEMAC.

Problème résolu :
    L'utilisateur dit "gouvernement de la BEAC", "taux d'intérêt", "banque centrale",
    "membres de la direction"... alors que les documents BEAC utilisent "conseil
    d'administration", "TIAO", "organigramme", etc.
    BGE-M3 (embedding sémantique) ne comble pas toujours cet écart terminologique.

Solution :
    Avant de calculer l'embedding de la question, on enrichit la requête avec les
    termes équivalents du vocabulaire BEAC, ce qui améliore le score de similarité
    cosinus avec les chunks pertinents.

Usage :
    from src.rag.query_expander import expand_query
    expanded = expand_query("membres du gouvernement de la BEAC")
    # → "membres du gouvernement de la BEAC Conseil d'Administration gouverneurs
    #    censeurs Directeurs Généraux organes de direction organigramme"
"""
from __future__ import annotations

import re
import unicodedata

from src.utils.logger import logger


# ---------------------------------------------------------------------------
# Normalisation interne (retire accents, minuscules, normalise apostrophes)
# L'apostrophe typographique ' et le guillemet ' sont ramenés à '
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalise : minuscules + suppression diacritiques + apostrophes uniformes."""
    text = text.replace("\u2019", "'").replace("\u2018", "'")   # apostrophes typographiques → ASCII
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text.lower()


# ---------------------------------------------------------------------------
# TABLE DE SYNONYMES BEAC / CEMAC
# ---------------------------------------------------------------------------
# Structure :
#   clé   : expression telle que l'utilisateur la formule (minuscules, avec
#            apostrophes si nécessaire — ex: "taux d'interet")
#   valeur: liste de termes institutionnels présents dans les documents BEAC
#
# Notes :
#   - Les clés sont pré-normalisées via _normalize() au chargement du module.
#   - Plusieurs clés peuvent pointer vers les mêmes synonymes (alias).
#   - Les apostrophes dans les clés sont gérées après normalisation.
# ---------------------------------------------------------------------------

_SYNONYMS: dict[str, list[str]] = {

    # -----------------------------------------------------------------------
    # GOUVERNANCE & ORGANES DE DIRECTION
    # -----------------------------------------------------------------------
    "gouvernement de la beac": [
        "Conseil d'Administration", "organes de direction", "organigramme",
        "gouverneurs", "censeurs", "Directeurs Généraux", "Comité Ministériel",
    ],
    "membres du gouvernement": [
        "gouverneurs", "censeurs", "Directeurs Généraux",
        "Conseil d'Administration", "organigramme", "organes de la BEAC",
    ],
    "membres de la direction": [
        "gouverneurs", "censeurs", "Directeurs Généraux",
        "Comité de Direction", "organigramme BEAC",
    ],
    "gouverneur": [
        "Gouverneur de la BEAC", "Gouverneur", "Vice-Gouverneur",
        "Gouverneur intérimaire",
    ],
    "vice-gouverneur": [
        "Vice-Gouverneur", "Vice Gouverneur", "gouverneur adjoint",
    ],
    "censeur": [
        "Censeur", "censeurs", "Conseil d'Administration censeur",
    ],
    "directeur general": [
        "Directeur Général", "Directeur Général Adjoint", "DGA", "DG BEAC",
    ],
    "directeur general adjoint": [
        "Directeur Général Adjoint", "DGA BEAC",
    ],
    "conseil d'administration": [
        "Conseil d'Administration", "CA BEAC", "administrateurs",
        "membres du Conseil",
    ],
    "conseil d administration": [
        "Conseil d'Administration", "CA BEAC", "administrateurs",
        "membres du Conseil",
    ],
    "organigramme": [
        "organigramme", "structure organisationnelle", "organes de direction",
        "hiérarchie BEAC", "direction générale",
    ],
    "organes": [
        "organes de direction", "Conseil d'Administration",
        "Comité de Direction", "organigramme",
    ],
    "comite ministeriel": [
        "Comité Ministériel", "Comité Ministériel de l'UMAC",
        "Union Monétaire de l'Afrique Centrale", "UMAC",
    ],
    "dirigeants": [
        "gouverneurs", "censeurs", "Directeurs Généraux",
        "Comité de Direction", "organes dirigeants BEAC",
    ],
    "president": [
        "Président du Conseil d'Administration", "Président BEAC",
        "Gouverneur", "Président du Comité Ministériel",
    ],
    "nomination": [
        "nommé", "nommée", "désigné", "prise de fonction",
        "entrée en fonction", "décision de nomination",
    ],
    "mandat": [
        "mandat", "durée du mandat", "renouvellement de mandat",
        "fin de mandat", "prise de fonction",
    ],

    # -----------------------------------------------------------------------
    # NOMS PROPRES — PERSONNALITÉS BEAC / CEMAC
    # -----------------------------------------------------------------------
    "yvon sana bangui": [
        "Gouverneur", "Gouverneur de la BEAC", "organigramme",
        "Conseil d'Administration", "organes de direction",
    ],
    "sana bangui": [
        "Gouverneur de la BEAC", "organigramme", "Conseil d'Administration",
    ],
    "yvon sana": [
        "Gouverneur de la BEAC", "organigramme",
    ],
    # Ajouter ici d'autres noms de dirigeants au fur et à mesure

    # -----------------------------------------------------------------------
    # POLITIQUE MONÉTAIRE
    # -----------------------------------------------------------------------
    "politique monetaire": [
        "politique monétaire", "Comité de Politique Monétaire", "CPM",
        "décision de politique monétaire", "orientation monétaire",
        "stance monétaire",
    ],
    "taux d'interet": [
        "taux directeur", "TIAO", "taux d'intérêt aux opérations",
        "taux de prise en pension", "taux de facilité de dépôt",
        "taux de facilité marginale de prêt",
    ],
    "taux d interet": [
        "taux directeur", "TIAO", "taux d'intérêt aux opérations",
        "taux de prise en pension",
    ],
    "taux directeur": [
        "TIAO", "taux d'intérêt aux opérations", "taux directeur BEAC",
        "taux de prise en pension", "taux repo",
    ],
    "tiao": [
        "TIAO", "taux d'intérêt aux opérations", "taux directeur BEAC",
    ],
    "taux d'inflation": [
        "inflation", "taux d'inflation", "hausse des prix",
        "indice des prix à la consommation", "IPC",
    ],
    "taux d inflation": [
        "inflation", "taux d'inflation", "IPC",
        "indice des prix à la consommation",
    ],
    "inflation": [
        "taux d'inflation", "inflation sous-jacente", "IPC",
        "indice des prix", "hausse des prix à la consommation",
        "pression inflationniste",
    ],
    "injection de liquidite": [
        "injection de liquidités", "opérations d'open market",
        "appels d'offres", "refinancement", "prises en pension",
    ],
    "injection liquidite": [
        "injection de liquidités", "opérations d'open market",
        "appels d'offres", "refinancement",
    ],
    "reserve obligatoire": [
        "réserves obligatoires", "coefficient de réserves obligatoires",
        "assiette des réserves", "taux de réserves",
    ],
    "instrument de politique monetaire": [
        "taux directeur", "réserves obligatoires", "open market",
        "facilités permanentes", "opérations de refinancement",
    ],
    "decision monetaire": [
        "Comité de Politique Monétaire", "CPM", "session CPM",
        "décision de politique monétaire", "communiqué CPM",
    ],
    "stabilite des prix": [
        "stabilité des prix", "objectif d'inflation",
        "ancrage des anticipations", "cible d'inflation",
    ],
    "stabilite prix": [
        "stabilité des prix", "objectif d'inflation", "cible d'inflation",
    ],
    "resserrement monetaire": [
        "hausse du taux directeur", "resserrement monétaire",
        "politique monétaire restrictive",
    ],
    "assouplissement monetaire": [
        "baisse du taux directeur", "assouplissement monétaire",
        "politique monétaire accommodante",
    ],
    "cpm": [
        "Comité de Politique Monétaire", "CPM", "session CPM",
        "décision de politique monétaire",
    ],

    # -----------------------------------------------------------------------
    # MONNAIE & CHANGE
    # -----------------------------------------------------------------------
    "franc cfa": [
        "Franc CFA", "FCFA", "XAF",
        "franc de la Coopération Financière en Afrique",
        "monnaie commune CEMAC",
    ],
    "fcfa": [
        "Franc CFA", "FCFA", "XAF", "monnaie CEMAC",
    ],
    "taux de change": [
        "taux de change", "parité FCFA/EUR", "parité fixe",
        "ancrage monétaire", "convertibilité du FCFA",
    ],
    "parite": [
        "parité fixe", "parité FCFA/EUR", "1 EUR = 655,957 FCFA",
        "ancrage à l'euro",
    ],
    "reserve de change": [
        "réserves de change", "avoirs extérieurs nets",
        "réserves officielles", "réserves en devises",
        "couverture extérieure",
    ],
    "reserves de change": [
        "réserves de change", "avoirs extérieurs nets",
        "réserves officielles", "couverture extérieure en mois d'importations",
    ],
    "avoirs exterieurs": [
        "avoirs extérieurs nets", "réserves de change",
        "couverture extérieure", "réserves officielles de change",
    ],
    "compte d'operations": [
        "Compte d'Opérations", "compte d'opérations Trésor français",
        "accord de coopération monétaire",
    ],
    "compte d operations": [
        "Compte d'Opérations", "accord de coopération monétaire",
    ],

    # -----------------------------------------------------------------------
    # AGRÉGATS MONÉTAIRES
    # -----------------------------------------------------------------------
    "masse monetaire": [
        "masse monétaire", "M2", "M1", "M3",
        "agrégats monétaires", "monnaie en circulation",
        "dépôts bancaires", "créances sur l'économie",
    ],
    "agregat monetaire": [
        "agrégats monétaires", "M1", "M2", "M3",
        "masse monétaire", "monnaie en circulation",
    ],
    "m1": [
        "M1", "monnaie au sens strict", "billets en circulation",
        "pièces en circulation", "dépôts à vue",
    ],
    "m2": [
        "M2", "masse monétaire au sens large", "dépôts à terme",
        "dépôts d'épargne", "agrégat M2",
    ],
    "credit a l'economie": [
        "créances sur l'économie", "crédits à l'économie",
        "crédit intérieur", "encours de crédit",
    ],
    "credit economie": [
        "créances sur l'économie", "crédits à l'économie",
        "crédit intérieur", "encours de crédit",
    ],
    "liquidite bancaire": [
        "liquidité bancaire", "excédent de liquidité",
        "ponction de liquidité", "besoins en liquidité",
        "trésorerie bancaire",
    ],
    "emission monetaire": [
        "émission monétaire", "émission fiduciaire",
        "billets émis", "mise en circulation",
    ],
    "billet": [
        "billets de banque", "émission fiduciaire",
        "fabrication des billets", "billets BEAC",
    ],

    # -----------------------------------------------------------------------
    # SYSTÈME BANCAIRE & STABILITÉ FINANCIÈRE
    # -----------------------------------------------------------------------
    "banque commerciale": [
        "établissements de crédit", "banques commerciales",
        "banques agréées", "système bancaire CEMAC",
    ],
    "etablissement de credit": [
        "établissements de crédit", "banques commerciales",
        "banques agréées CEMAC",
    ],
    "supervision bancaire": [
        "COBAC", "Commission Bancaire de l'Afrique Centrale",
        "supervision bancaire", "contrôle bancaire",
        "agrément bancaire", "normes prudentielles",
    ],
    "cobac": [
        "COBAC", "Commission Bancaire de l'Afrique Centrale",
        "supervision", "réglementation bancaire CEMAC",
    ],
    "solvabilite": [
        "ratio de solvabilité", "fonds propres",
        "adéquation des fonds propres", "Bâle II", "Bâle III CEMAC",
    ],
    "stabilite financiere": [
        "stabilité financière", "risque systémique",
        "surveillance macro-prudentielle", "solidité du système bancaire",
    ],
    "pret refinancement": [
        "opérations de refinancement", "prises en pension",
        "avances aux établissements de crédit",
    ],

    # -----------------------------------------------------------------------
    # FINANCES PUBLIQUES
    # -----------------------------------------------------------------------
    "budget": [
        "budget de l'État", "loi de finances", "recettes budgétaires",
        "dépenses publiques", "solde budgétaire",
    ],
    "deficit budgetaire": [
        "déficit budgétaire", "solde budgétaire négatif",
        "financement du déficit",
    ],
    "dette publique": [
        "dette publique", "dette extérieure", "dette intérieure",
        "service de la dette", "encours de la dette", "endettement public",
    ],
    "recette fiscale": [
        "recettes fiscales", "pression fiscale", "impôts", "taxes",
        "recettes pétrolières",
    ],
    "depense publique": [
        "dépenses publiques", "dépenses de fonctionnement",
        "investissements publics",
    ],
    "petrole": [
        "recettes pétrolières", "revenus pétroliers",
        "production pétrolière", "cours du pétrole", "Brent",
    ],
    "tresor": [
        "Trésor public", "compte du Trésor", "avances au Trésor",
        "concours au Trésor",
    ],

    # -----------------------------------------------------------------------
    # BALANCE DES PAIEMENTS & COMMERCE EXTÉRIEUR
    # -----------------------------------------------------------------------
    "balance des paiements": [
        "balance des paiements", "compte courant",
        "compte de capital", "compte financier",
    ],
    "balance paiements": [
        "balance des paiements", "compte courant",
        "solde de la balance des paiements",
    ],
    "balance commerciale": [
        "balance commerciale", "exportations", "importations",
        "solde commercial",
    ],
    "exportation": [
        "exportations", "recettes d'exportation",
        "exportations de pétrole", "exportations de cacao",
    ],
    "importation": [
        "importations", "achats à l'extérieur", "facture des importations",
    ],
    "investissement etranger": [
        "investissements directs étrangers", "IDE",
        "flux d'IDE", "entrées de capitaux",
    ],

    # -----------------------------------------------------------------------
    # CROISSANCE & ACTIVITÉ ÉCONOMIQUE
    # -----------------------------------------------------------------------
    "croissance economique": [
        "taux de croissance", "PIB", "produit intérieur brut",
        "croissance du PIB", "activité économique",
    ],
    "pib": [
        "PIB", "produit intérieur brut", "croissance économique",
        "PIB réel", "PIB nominal",
    ],
    "recession": [
        "récession", "contraction de l'activité",
        "croissance négative", "repli du PIB",
    ],
    "conjoncture": [
        "conjoncture économique", "situation économique",
        "activité économique", "perspectives économiques",
    ],
    "perspectives economiques": [
        "perspectives économiques", "prévisions macroéconomiques",
        "projections", "outlook CEMAC",
    ],

    # -----------------------------------------------------------------------
    # INSTITUTIONS & ORGANISATIONS
    # -----------------------------------------------------------------------
    "banque centrale": [
        "BEAC", "Banque des États de l'Afrique Centrale",
        "Institut d'émission", "banque centrale CEMAC",
    ],
    "beac": [
        "Banque des États de l'Afrique Centrale",
        "Institut d'émission de la CEMAC",
        "banque centrale des États de l'Afrique Centrale",
    ],
    "cemac": [
        "CEMAC", "Communauté Économique et Monétaire de l'Afrique Centrale",
        "zone CEMAC", "espace CEMAC", "États membres CEMAC",
    ],
    "umac": [
        "UMAC", "Union Monétaire de l'Afrique Centrale",
        "union monétaire", "zone franc CFA",
    ],
    "zone franc": [
        "zone franc", "franc CFA", "FCFA",
        "accords de coopération monétaire", "Trésor français",
    ],
    "fmi": [
        "FMI", "Fonds Monétaire International",
        "programme FMI", "accord FMI", "article IV",
    ],
    "banque mondiale": [
        "Banque Mondiale", "Banque Internationale pour la Reconstruction",
        "IDA", "BIRD",
    ],
    "bdeac": [
        "BDEAC", "Banque de Développement des États de l'Afrique Centrale",
        "banque de développement sous-régionale",
    ],
    "gimac": [
        "GIMAC", "Groupement Interbancaire Monétique de l'Afrique Centrale",
        "monétique CEMAC", "système de paiement",
    ],

    # -----------------------------------------------------------------------
    # PAYS MEMBRES CEMAC
    # -----------------------------------------------------------------------
    "pays membre": [
        "Cameroun", "Congo", "Gabon", "Tchad",
        "République Centrafricaine", "Guinée Équatoriale",
        "États membres CEMAC",
    ],
    "etats membres": [
        "Cameroun", "Congo", "Gabon", "Tchad",
        "République Centrafricaine", "Guinée Équatoriale",
        "États membres CEMAC",
    ],
    "afrique centrale": [
        "CEMAC", "Afrique Centrale", "zone CEMAC",
        "Cameroun", "Congo", "Gabon", "Tchad",
        "Centrafrique", "Guinée Équatoriale",
    ],
    "cameroun": [
        "Cameroun", "République du Cameroun", "Yaoundé",
    ],
    "congo": [
        "Congo", "République du Congo", "Congo-Brazzaville", "Brazzaville",
    ],
    "gabon": [
        "Gabon", "République Gabonaise", "Libreville",
    ],
    "tchad": [
        "Tchad", "République du Tchad", "N'Djamena",
    ],
    "centrafrique": [
        "République Centrafricaine", "RCA", "Centrafrique", "Bangui",
    ],
    "rca": [
        "République Centrafricaine", "RCA", "Centrafrique",
    ],
    "guinee equatoriale": [
        "Guinée Équatoriale", "Guinea Ecuatorial", "Malabo",
    ],

    # -----------------------------------------------------------------------
    # PUBLICATIONS & RAPPORTS
    # -----------------------------------------------------------------------
    "rapport annuel": [
        "rapport annuel", "rapport annuel BEAC", "annual report",
        "rapport d'activité",
    ],
    "rapport monetaire": [
        "rapport sur la politique monétaire",
        "rapport monétaire et financier", "bulletin monétaire",
    ],
    "statistiques beac": [
        "statistiques monétaires", "tableau de bord",
        "bulletin de statistiques", "données statistiques BEAC",
    ],
    "communique de presse": [
        "communiqué de presse", "déclaration", "note d'information",
        "communiqué CPM", "communiqué du Conseil d'Administration",
    ],
    "communique": [
        "communiqué de presse", "déclaration officielle",
        "communiqué CPM",
    ],
    "etats financiers": [
        "états financiers", "bilan BEAC", "compte de résultat",
        "rapport des commissaires aux comptes",
    ],
    "reglement": [
        "règlement COBAC", "règlement CEMAC", "directive CEMAC",
        "textes réglementaires", "instruction BEAC",
    ],
    "texte reglementaire": [
        "textes réglementaires", "règlement", "directive",
        "instruction BEAC", "circulaire BEAC",
    ],

    # -----------------------------------------------------------------------
    # OPÉRATIONS & SYSTÈMES BEAC
    # -----------------------------------------------------------------------
    "appel d'offres": [
        "appels d'offres", "opérations d'open market",
        "adjudication", "opérations de cession temporaire",
    ],
    "appel d offres": [
        "appels d'offres", "opérations d'open market", "adjudication",
    ],
    "systeme de paiement": [
        "système de paiement", "SYGMA", "GIMAC",
        "système de paiement interbancaire",
    ],
    "compensation interbancaire": [
        "chambre de compensation", "SYSTAC",
        "système de transfert automatisé et de compensation",
    ],
    "recrutement": [
        "recrutement", "appel à candidatures", "offre d'emploi",
        "liste des candidats", "avis de recrutement BEAC",
    ],
    "emploi beac": [
        "recrutement BEAC", "postes à pourvoir",
        "offres d'emploi BEAC", "concours BEAC",
    ],
}


# ---------------------------------------------------------------------------
# Pré-calcul des clés normalisées (chargement unique au démarrage)
# ---------------------------------------------------------------------------

_NORMALIZED_SYNONYMS: dict[str, list[str]] = {
    _normalize(k): v for k, v in _SYNONYMS.items()
}


# ---------------------------------------------------------------------------
# Fonctions publiques
# ---------------------------------------------------------------------------

def expand_query(question: str) -> str:
    """Enrichit la question utilisateur avec les termes institutionnels BEAC.

    La question originale est conservée en tête. Les termes ajoutés
    sont dédupliqués et ordonnés par ordre de premier match.

    Exemple :
        >>> expand_query("membres du gouvernement de la BEAC en 2026")
        'membres du gouvernement de la BEAC en 2026 Conseil d\\'Administration
         organes de direction organigramme gouverneurs censeurs ...'
    """
    norm_q = _normalize(question)
    additions: list[str] = []
    matched_keys: list[str] = []

    for norm_key, synonyms in _NORMALIZED_SYNONYMS.items():
        if norm_key in norm_q:
            matched_keys.append(norm_key)
            for syn in synonyms:
                if syn not in additions:
                    additions.append(syn)

    if not additions:
        return question

    expanded = question + " " + " ".join(additions)
    logger.debug(
        "[query_expander] '{}' → triggers={}, +{} termes",
        question[:60], matched_keys, len(additions),
    )
    return expanded


def get_matched_synonyms(question: str) -> dict[str, list[str]]:
    """Retourne le détail des synonymes déclenchés — utile pour debug/tests."""
    norm_q = _normalize(question)
    result: dict[str, list[str]] = {}
    for norm_key, synonyms in _NORMALIZED_SYNONYMS.items():
        if norm_key in norm_q:
            # Retrouver la clé originale (avant normalisation)
            original_key = next(
                k for k in _SYNONYMS if _normalize(k) == norm_key
            )
            result[original_key] = synonyms
    return result