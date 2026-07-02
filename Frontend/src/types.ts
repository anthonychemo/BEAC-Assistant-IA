export type DocumentType = "Rapports" | "Bulletins" | "Working Papers" | "Communiques" | "Reglementation";

export interface Document {
  id: string;
  title: string;
  type: DocumentType;
  fileType: string;
  fileSize: string;
  date: string;
  description: string;
  section: "Politique Monétaire" | "Stabilité Financière" | "Études Statistiques";
  url: string;
}

export interface SourceItem {
  source: string;
  category: string | null;
  year: number | null;
  score: number | null;
  image_paths: string[] | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceItem[];
  query_type?: string;
  timestamp: string;
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
