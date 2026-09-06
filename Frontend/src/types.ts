// Categorie reelle du document telle que renvoyee par le backend (champ
// `category` de la table `documents`, alimente par le scraper) — texte libre,
// pas un enum fige.
export interface Document {
  id: string;
  title: string;
  type: string;
  fileType: string;
  date: string | null;
  description: string | null;
  country: string | null;
  year: number | null;
  url: string;
}

export interface SourceItem {
  source: string;
  category: string | null;
  year: number | null;
  score: number | null;
  source_url: string | null;
  // Lien direct vers le fichier original (backend, R2 presigne) - a privilegier
  // sur source_url (page beac.int) pour ouvrir exactement le document consulte.
  url: string | null;
  image_paths: string[] | null;
}

export interface ModelChoice {
  key: string;
  label: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceItem[];
  query_type?: string;
  timestamp: string;
  isError?: boolean;
  feedback?: "positive" | "negative";
  // Present sur un message utilisateur quand la question cible un document
  // precis de la bibliotheque (bouton "Analyser IA"), pour que la recherche
  // se limite a ce document plutot qu'a tout le corpus.
  documentId?: string;
}

export interface Log {
  id: string;
  timestamp: string;
  type: "success" | "warning" | "error";
  message: string;
  targetDoc?: string;
}

export interface DashboardMetrics {
  documentsIndexed: number;
  ragChunks: number;
  feedbackSatisfaction: string;
  avgResponseTime: string;
  systemStatus: string;
}

// Volumetrie + repartitions reelles pour le dashboard admin (GET /api/admin/stats).
export interface DashboardStats {
  by_month: { month: string; count: number }[];
  by_category: { category: string; count: number }[];
  by_country: { country: string; count: number }[];
}

// Etat du pipeline scraping -> upload R2 -> ingestion (GET /api/pipeline/status),
// declenche par le bouton "Demarrer le pipeline" du dashboard admin.
export interface PipelineStatus {
  status: "idle" | "running" | "done" | "error";
  stage: string | null;
  stage_label: string | null;
  started_at: number | null;
  finished_at: number | null;
  new_documents: number;
  error: string | null;
  log_tail: string[];
}
