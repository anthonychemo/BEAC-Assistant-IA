import { Document, Log } from "./types";

export const INITIAL_DOCUMENTS: Document[] = [
  {
    id: "doc-1",
    title: "Rapport sur la politique monétaire dans la CEMAC - Exercice 2023",
    type: "Rapports",
    fileType: "PDF",
    date: "15 Mars 2024",
    description: "Ce document présente une analyse approfondie des évolutions macroéconomiques de la zone CEMAC au cours de l'année écoulée, mettant en lumière les décisions prises par le Comité de Politique Monétaire.",
    country: null,
    year: 2024,
    url: "https://www.beac.int"
  },
  {
    id: "doc-2",
    title: "Indicateurs de convergence macroéconomique - T4 2023",
    type: "Bulletins",
    fileType: "XLS",
    date: "02 Mars 2024",
    description: "Tableaux statistiques détaillés incluant les taux d'inflation, les réserves de change et les balances commerciales agrégées des six États membres de la BEAC.",
    country: null,
    year: 2024,
    url: "https://www.beac.int"
  },
  {
    id: "doc-3",
    title: "Communiqué de presse du Comité de Politique Monétaire (CPM)",
    type: "Communiqués",
    fileType: "PDF",
    date: "28 Février 2024",
    description: "Décisions relatives au maintien du taux directeur et orientations stratégiques pour la gestion de la liquidité bancaire au premier semestre 2024.",
    country: null,
    year: 2024,
    url: "https://www.beac.int"
  },
  {
    id: "doc-4",
    title: "Impact de la digitalisation des paiements sur la vélocité monétaire",
    type: "Working Papers",
    fileType: "PDF",
    date: "10 Février 2024",
    description: "Une étude empirique menée par la Direction de la Recherche sur l'évolution des habitudes de consommation et l'adoption du mobile money dans la région.",
    country: null,
    year: 2024,
    url: "https://www.beac.int"
  },
  {
    id: "doc-5",
    title: "Rapport Annuel de Surveillance Financière Régionale",
    type: "Rapports",
    fileType: "PDF",
    date: "12 Décembre 2023",
    description: "Analyse rétrospective des ratios prudentiels de capitalisation et de liquidité des établissements de crédit assujettis aux règlements COBAC.",
    country: null,
    year: 2023,
    url: "https://www.beac.int"
  },
  {
    id: "doc-6",
    title: "Directive COBAC n°01/23 relative aux risques cybernétiques",
    type: "Réglementation",
    fileType: "PDF",
    date: "18 Novembre 2023",
    description: "Définition du cadre minimal de régulation de la cyber-sécurité et audit technique obligatoire pour tous les intermédiaires financiers nationaux.",
    country: null,
    year: 2023,
    url: "https://www.beac.int"
  },
  {
    id: "doc-7",
    title: "Bulletin d'Études Statistiques N°41 - Balance des paiements CEMAC",
    type: "Bulletins",
    fileType: "PDF",
    date: "05 Octobre 2023",
    description: "Agrégation statistique des comptes nationaux extérieurs, flux d'investissements directs étrangers et réserve de monnaies étrangères de compensation.",
    country: null,
    year: 2023,
    url: "https://www.beac.int"
  }
];

export const INITIAL_LOGS: Log[] = [
  {
    id: "log-1",
    timestamp: "10:45:22",
    type: "success",
    message: "Indexation terminée pour ",
    targetDoc: "BEAC_Annual_Report_2023.pdf"
  },
  {
    id: "log-2",
    timestamp: "10:45:10",
    type: "warning",
    message: "Attention: Haute latence détectée sur le Service d'Embedding (Zone: Centrale)"
  },
  {
    id: "log-3",
    timestamp: "10:44:05",
    type: "success",
    message: "Battement de cœur du pipeline : Sain"
  },
  {
    id: "log-4",
    timestamp: "10:42:15",
    type: "error",
    message: "Erreur : Connexion refusée pour Node_04 dans le cluster VectorDB. Nouvelle tentative..."
  },
  {
    id: "log-5",
    timestamp: "10:40:59",
    type: "success",
    message: "Nettoyage du cache pour les sessions RAG expirées (128 sessions purgées)"
  },
  {
    id: "log-6",
    timestamp: "10:38:22",
    type: "success",
    message: "Nouveau traitement par lots démarré : Statistiques Régionales CEMAC (15 fichiers)"
  },
  {
    id: "log-7",
    timestamp: "10:35:00",
    type: "success",
    message: "Tâche de maintenance planifiée : \"Vérification de la cohérence du corpus\" terminée."
  }
];
