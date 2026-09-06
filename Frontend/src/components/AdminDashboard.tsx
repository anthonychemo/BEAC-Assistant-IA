import React, { useState } from "react";
import { Log, DashboardMetrics, PipelineStatus, DashboardStats } from "../types";
import { Play, Loader2, RefreshCw, Plus, Trash2, ListFilter, Activity, BarChart3, Database, Clock, Smile, Sparkles, CheckCircle2, AlertTriangle, PieChart, Globe2 } from "lucide-react";
import { motion } from "motion/react";

interface AdminDashboardProps {
  metrics: DashboardMetrics;
  logs: Log[];
  onAddLog: (text: string, type: "success" | "warning" | "error") => void;
  onClearLogs: () => void;
  pipelineStatus: PipelineStatus;
  onStartPipeline: () => void;
  stats: DashboardStats;
}

const MONTH_LABELS: Record<string, string> = {
  "01": "Jan", "02": "Fév", "03": "Mar", "04": "Avr", "05": "Mai", "06": "Juin",
  "07": "Juil", "08": "Août", "09": "Sep", "10": "Oct", "11": "Nov", "12": "Déc",
};

function formatMonth(ym: string): string {
  const [year, month] = ym.split("-");
  return `${MONTH_LABELS[month] ?? month} ${year.slice(2)}`;
}

// Liste de barres horizontales proportionnelles, reutilisee pour les
// repartitions par categorie et par pays (donnees reelles, /api/admin/stats).
function BreakdownList({
  items,
  colorClass,
}: {
  items: { label: string; count: number }[];
  colorClass: string;
}) {
  if (items.length === 0) {
    return <p className="text-xs text-black/40 text-center py-8">Aucune donnée pour le moment</p>;
  }
  const max = Math.max(...items.map((i) => i.count));
  return (
    <div className="flex flex-col gap-2.5">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <span className="text-[10px] font-semibold text-black/70 w-32 shrink-0 truncate" title={item.label}>
            {item.label}
          </span>
          <div className="flex-1 bg-gray-100 rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-full rounded-full ${colorClass}`}
              style={{ width: `${max > 0 ? (item.count / max) * 100 : 0}%` }}
            />
          </div>
          <span className="text-[10px] font-bold text-[#0D2D5E] w-10 text-right shrink-0">
            {item.count.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function AdminDashboard({
  metrics,
  logs,
  onAddLog,
  onClearLogs,
  pipelineStatus,
  onStartPipeline,
  stats,
}: AdminDashboardProps) {
  const isPipelineRunning = pipelineStatus.status === "running";
  const [logInput, setLogInput] = useState("");
  const [logType, setLogType] = useState<"success" | "warning" | "error">("success");
  const [logFilter, setLogFilter] = useState<string>("all");

  const handleAddCustomLog = (e: React.FormEvent) => {
    e.preventDefault();
    if (!logInput.trim()) return;
    onAddLog(logInput.trim(), logType);
    setLogInput("");
  };

  const filteredLogs = logs.filter((log) => {
    if (logFilter === "all") return true;
    if (logFilter === "success") return log.type === "success";
    if (logFilter === "warning-error") return log.type === "warning" || log.type === "error";
    return true;
  });

  return (
    <div className="flex-1 bg-[#f8f9fa] py-8 px-4 md:px-16">
      <div className="max-w-[1280px] mx-auto">
        
        {/* Title */}
        <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
          <div>
            <h1 className="font-sans text-[#0D2D5E] text-2xl md:text-3xl font-extrabold tracking-tight mb-2">
              Statistiques &amp; Pipeline RAG BEAC
            </h1>
            <p className="text-black/60 font-sans text-sm font-medium">
              Supervisez les opérations du pipeline d'ingestion sémantique et la santé du cluster IA en temps réel.
            </p>
          </div>

          <div className="flex flex-col items-end gap-1.5">
            <button
              onClick={onStartPipeline}
              disabled={isPipelineRunning}
              title="Scrape le site de la BEAC, uploade les nouveaux documents vers R2 et les indexe"
              className={`flex items-center gap-2 py-2.5 px-5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all shadow-sm ${
                isPipelineRunning
                  ? "bg-emerald-600/60 text-white cursor-not-allowed"
                  : "bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer"
              }`}
            >
              {isPipelineRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {pipelineStatus.stage_label || "Pipeline en cours..."}
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  Démarrer le Pipeline
                </>
              )}
            </button>
            {pipelineStatus.status === "error" && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-red-600">
                <AlertTriangle className="w-3 h-3" />
                Echec : {pipelineStatus.error}
              </span>
            )}
            {pipelineStatus.status === "done" && (
              <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-600">
                <CheckCircle2 className="w-3 h-3" />
                {pipelineStatus.new_documents} nouveau{pipelineStatus.new_documents > 1 ? "x" : ""} document{pipelineStatus.new_documents > 1 ? "s" : ""} indexe{pipelineStatus.new_documents > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>

        {/* Core KPI metrics grid with BEAC theme */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          
          <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm flex items-center gap-5">
            <div className="w-12 h-12 bg-[#0D2D5E]/10 rounded-lg flex items-center justify-center text-[#0D2D5E] shrink-0">
              <Database className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-gray-500 font-mono block uppercase tracking-wider">
                DOCUMENTS INDEXÉS
              </span>
              <span className="text-2xl font-black text-[#0D2D5E] font-sans">
                {metrics.documentsIndexed.toLocaleString()}
              </span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm flex items-center gap-5">
            <div className="w-12 h-12 bg-[#C8971A]/10 rounded-lg flex items-center justify-center text-[#C8971A] shrink-0">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-gray-500 font-mono block uppercase tracking-wider">
                CHUNKS DE PHRASES (RAG)
              </span>
              <span className="text-2xl font-black text-[#0D2D5E] font-sans">
                {metrics.ragChunks.toLocaleString()}
              </span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm flex items-center gap-5">
            <div className="w-12 h-12 bg-[#0D2D5E]/10 rounded-lg flex items-center justify-center text-[#0D2D5E] shrink-0">
              <Clock className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-gray-500 font-mono block uppercase tracking-wider">
                TEMPS DE RÉPONSE IA
              </span>
              <span className="text-2xl font-black text-[#0D2D5E] font-sans">
                {metrics.avgResponseTime}
              </span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm flex items-center gap-5">
            <div className="w-12 h-12 bg-[#C8971A]/10 rounded-lg flex items-center justify-center text-[#C8971A] shrink-0">
              <Smile className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[10px] font-bold text-gray-500 font-mono block uppercase tracking-wider">
                SATISFACTION RETOURS
              </span>
              <span className="text-2xl font-black text-[#0D2D5E] font-sans">
                {metrics.feedbackSatisfaction}
              </span>
            </div>
          </div>

        </div>

        {/* Dashboard Panels (Charts Left, Terminal Logs Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start mb-8">
          
          {/* Custom Interactive SVG charts left column */}
          <div className="lg:col-span-6 flex flex-col gap-6">
            
            {/* Chart 1 - Activity Graph */}
            <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <h3 className="font-sans text-[#0D2D5E] text-base font-bold">
                    Volumétrie mensuelle d'ingestion
                  </h3>
                  <p className="text-[10px] text-gray-500 font-medium">Documents indexés par mois (date réelle d'ingestion)</p>
                </div>
                <div className="flex items-center gap-1 bg-[#0D2D5E]/5 text-[#0D2D5E] px-2.5 py-1 rounded text-[10px] font-bold">
                  <BarChart3 className="w-3.5 h-3.5" /> DONNÉES RÉELLES
                </div>
              </div>

              <BreakdownList
                items={stats.by_month.map((m) => ({ label: formatMonth(m.month), count: m.count }))}
                colorClass="bg-[#0D2D5E]"
              />
            </div>

            {/* Pipeline Status box */}
            <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <div className={`w-3.5 h-3.5 rounded-full ${isPipelineRunning ? "bg-emerald-500 animate-pulse" : "bg-gray-300"}`} />
                <h4 className="font-sans text-[#0D2D5E] text-sm font-bold">
                  Agent d'Extraction : {isPipelineRunning ? `En cours (${pipelineStatus.stage_label})` : "Au repos"}
                </h4>
              </div>
              <p className="text-xs text-black/60 leading-relaxed font-sans">
                {isPipelineRunning
                  ? "Scraping du site beac.int, upload des nouveaux documents vers R2 et indexation vectorielle en cours."
                  : "Cliquez sur \"Démarrer le Pipeline\" pour scraper le site de la BEAC et indexer les documents publiés depuis le dernier passage."}
              </p>
              
              <div className="grid grid-cols-3 gap-2 mt-2">
                <div className="bg-gray-100 p-2.5 rounded text-center">
                  <span className="text-[9px] text-gray-500 font-bold block mb-1">CRAWL hebdomadaire</span>
                  <span className="text-xs font-bold text-[#0D2D5E]">Lundi 04:00</span>
                </div>
                <div className="bg-gray-100 p-2.5 rounded text-center">
                  <span className="text-[9px] text-gray-500 font-bold block mb-1">CLUSTER STATUS</span>
                  <span className="text-xs font-bold text-emerald-600">Sain</span>
                </div>
                <div className="bg-gray-100 p-2.5 rounded text-center">
                  <span className="text-[9px] text-gray-500 font-bold block mb-1">SYNC DÉLAI</span>
                  <span className="text-xs font-bold text-[#0D2D5E]">0,5s</span>
                </div>
              </div>
            </div>

          </div>

          {/* Interactive Logs Terminal Right column */}
          <div className="lg:col-span-6 flex flex-col gap-6">
            
            <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm flex flex-col">
              
              {/* Terminal Title / header actions */}
              <div className="flex justify-between items-center mb-6 pb-4 border-b border-gray-100">
                <div>
                  <h3 className="font-sans text-[#0D2D5E] text-base font-bold">
                    Terminal de logs d'indexation
                  </h3>
                  <p className="text-[10px] text-gray-500 font-medium">Activité interne du pipeline de chunking RAG</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={onClearLogs}
                    className="p-1.5 hover:bg-gray-100 text-gray-500 rounded hover:text-red-500 transition-colors cursor-pointer"
                    title="Nettoyer les logs"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Filter pills */}
              <div className="flex gap-2 mb-4">
                {[
                  { id: "all", label: "Tous" },
                  { id: "success", label: "Succès uniquement" },
                  { id: "warning-error", label: "Avertissements / Erreurs" },
                ].map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setLogFilter(f.id)}
                    className={`text-[10px] font-bold px-3 py-1.5 rounded transition-all cursor-pointer ${
                      logFilter === f.id
                        ? "bg-[#0D2D5E] text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* Terminal Screen box */}
              <div className="bg-gray-950 rounded-lg p-4 font-mono text-[11px] text-gray-300 h-80 overflow-y-auto space-y-2.5 mb-6 shadow-inner select-text scrollbar-thin">
                {filteredLogs.map((log) => (
                  <div key={log.id} className="leading-relaxed hover:bg-white/5 px-1 py-0.5 rounded">
                    <span className="text-gray-500 font-semibold mr-1.5">&#91;{log.timestamp}&#93;</span>
                    
                    {log.type === "success" && (
                      <span className="text-emerald-400 font-bold uppercase mr-1.5">Succès :</span>
                    )}
                    {log.type === "warning" && (
                      <span className="text-amber-400 font-bold uppercase mr-1.5">Alerte :</span>
                    )}
                    {log.type === "error" && (
                      <span className="text-red-400 font-bold uppercase mr-1.5">ERREUR :</span>
                    )}

                    <span>{log.message}</span>
                    {log.targetDoc && (
                      <span className="text-indigo-400 font-bold underline select-all ml-1 cursor-pointer">
                        {log.targetDoc}
                      </span>
                    )}
                  </div>
                ))}

                {filteredLogs.length === 0 && (
                  <div className="text-center text-gray-500 py-12">
                    Aucun log pour ce filtre
                  </div>
                )}
              </div>

              {/* Add Custom Log Form */}
              <form onSubmit={handleAddCustomLog} className="flex gap-2 items-center">
                <input
                  type="text"
                  placeholder="Écrire un message d'injection de logs..."
                  value={logInput}
                  onChange={(e) => setLogInput(e.target.value)}
                  className="flex-1 bg-gray-50 border border-gray-200 py-2 px-3 rounded-lg text-xs font-mono placeholder:text-gray-400 focus:outline-none focus:border-[#C8971A]"
                />
                
                <select
                  value={logType}
                  onChange={(e) => setLogType(e.target.value as any)}
                  className="bg-gray-50 border border-gray-200 py-2 px-2.5 rounded-lg text-xs font-bold text-gray-700 focus:outline-none focus:border-[#C8971A]"
                >
                  <option value="success">Succès</option>
                  <option value="warning">Alerte</option>
                  <option value="error">Erreur</option>
                </select>

                <button
                  type="submit"
                  disabled={!logInput.trim()}
                  className="bg-[#C8971A] hover:bg-[#F2B824] text-[#0D2D5E] font-bold p-2 px-3 rounded-lg text-xs transition-all flex items-center gap-1 shrink-0 cursor-pointer disabled:opacity-50"
                  title="Injecter le log"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Ajouter</span>
                </button>
              </form>

            </div>

          </div>

        </div>

        {/* Repartitions reelles du corpus (categorie / pays) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm">
            <div className="flex items-center gap-2 mb-5">
              <div className="w-9 h-9 bg-[#0D2D5E]/10 rounded-lg flex items-center justify-center text-[#0D2D5E] shrink-0">
                <PieChart className="w-4.5 h-4.5" />
              </div>
              <div>
                <h3 className="font-sans text-[#0D2D5E] text-sm font-bold">Répartition par catégorie</h3>
                <p className="text-[10px] text-gray-500 font-medium">Corpus indexé, toutes catégories</p>
              </div>
            </div>
            <BreakdownList
              items={stats.by_category.map((c) => ({ label: c.category, count: c.count }))}
              colorClass="bg-[#0D2D5E]"
            />
          </div>

          <div className="bg-white p-6 rounded-xl border border-[#c4c6d0]/40 shadow-sm">
            <div className="flex items-center gap-2 mb-5">
              <div className="w-9 h-9 bg-[#C8971A]/10 rounded-lg flex items-center justify-center text-[#C8971A] shrink-0">
                <Globe2 className="w-4.5 h-4.5" />
              </div>
              <div>
                <h3 className="font-sans text-[#0D2D5E] text-sm font-bold">Répartition par pays</h3>
                <p className="text-[10px] text-gray-500 font-medium">Documents rattachés à un pays de la CEMAC</p>
              </div>
            </div>
            <BreakdownList
              items={stats.by_country.map((c) => ({ label: c.country, count: c.count }))}
              colorClass="bg-[#C8971A]"
            />
          </div>

        </div>

      </div>
    </div>
  );
}
