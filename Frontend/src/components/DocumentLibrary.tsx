import React, { useState, useEffect, useCallback } from "react";
import { Document } from "../types";
import { Search, SearchCode, Eye, FileText, Upload, Sparkles, Database, ChevronLeft, ChevronRight as ChevronRightIcon, Loader2, WifiOff, X, ArrowDownAZ, ArrowUpAZ } from "lucide-react";

const PAGE_SIZE = 50;

type SortOrder = "recent" | "oldest";

interface DocumentLibraryProps {
  onUploadDocument: (doc: Document) => void;
  onAskDocInChat: (text: string, documentId?: string) => void;
  preSelectedType: string | null;
  setPreSelectedType: (type: string | null) => void;
  // Incrementer cette valeur (ex: apres un pipeline termine) force un
  // rechargement de la page courante depuis le backend.
  refreshKey?: number;
}

export default function DocumentLibrary({
  onUploadDocument,
  onAskDocInChat,
  preSelectedType,
  setPreSelectedType,
  refreshKey,
}: DocumentLibraryProps) {
  const [search, setSearch] = useState("");
  const [selectedType, setSelectedType] = useState<string>("Tous");
  const [selectedCountry, setSelectedCountry] = useState<string>("Tous");
  const [sortOrder, setSortOrder] = useState<SortOrder>("recent");
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>("");

  // Pagination & data
  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [countries, setCountries] = useState<string[]>([]);
  const [searchMode, setSearchMode] = useState<"exact" | "semantic">("exact");

  const fetchDocuments = useCallback(
    async (p: number, type: string, q: string, country: string, sort: SortOrder) => {
      setLoading(true);
      setLoadError(false);
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(p * PAGE_SIZE),
        sort,
      });
      if (q) params.set("search", q);
      if (type !== "Tous") params.set("doc_type", type);
      if (country !== "Tous") params.set("country", country);
      try {
        const res = await fetch(`/api/documents?${params}`);
        if (!res.ok) throw new Error("Reponse backend non OK");
        const data = await res.json();
        setDocuments(data.documents ?? []);
        setTotal(data.total ?? 0);
        setSearchMode(data.searchMode === "semantic" ? "semantic" : "exact");
      } catch {
        setDocuments([]);
        setTotal(0);
        setLoadError(true);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  // Charger quand les filtres, le tri, la page changent, ou qu'un rafraichissement est demande
  useEffect(() => {
    fetchDocuments(page, selectedType, search, selectedCountry, sortOrder);
  }, [page, selectedType, selectedCountry, sortOrder, fetchDocuments, refreshKey]);

  // Recherche avec debounce
  useEffect(() => {
    const t = setTimeout(() => {
      setPage(0);
      fetchDocuments(0, selectedType, search, selectedCountry, sortOrder);
    }, 400);
    return () => clearTimeout(t);
  }, [search]);

  // Categories & pays reels (pour les filtres), issus du corpus indexe
  useEffect(() => {
    fetch("/api/metadata")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        setCategories(data?.categories ?? []);
        setCountries(data?.countries ?? []);
      })
      .catch(() => {
        setCategories([]);
        setCountries([]);
      });
  }, []);

  useEffect(() => {
    if (preSelectedType) {
      setSelectedType(preSelectedType);
      setPage(0);
      setPreSelectedType(null);
    }
  }, [preSelectedType, setPreSelectedType]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const handleTypeChange = (type: string) => {
    setSelectedType(type);
    setPage(0);
  };

  const handleCountryChange = (country: string) => {
    setSelectedCountry(country);
    setPage(0);
  };

  const handleSortChange = (sort: SortOrder) => {
    setSortOrder(sort);
    setPage(0);
  };

  const hasActiveFilters =
    search !== "" || selectedType !== "Tous" || selectedCountry !== "Tous" || sortOrder !== "recent";

  const resetFilters = () => {
    setSearch("");
    setSelectedType("Tous");
    setSelectedCountry("Tous");
    setSortOrder("recent");
    setPage(0);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const processUploadedFile = (name: string) => {
    const newDoc: Document = {
      id: `doc-uploaded-${Date.now()}`,
      title: name.replace(/\.[^/.]+$/, ""), // remove extension
      type: "Import local",
      fileType: name.split(".").pop()?.toUpperCase() || "PDF",
      date: new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" }),
      description: "Ce document a été importé par l'utilisateur. Il est temporairement archivé en mémoire locale pour cette session (non envoyé au backend).",
      country: null,
      year: new Date().getFullYear(),
      url: "#"
    };

    setUploadStatus("Analyse du document...");
    setTimeout(() => {
      onUploadDocument(newDoc);
      setUploadStatus("Indexation complétée !");
      setTimeout(() => setUploadStatus(""), 2000);
    }, 1500);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processUploadedFile(e.dataTransfer.files[0].name);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processUploadedFile(e.target.files[0].name);
    }
  };

  const docTypes: string[] = ["Tous", ...categories];

  return (
    <div className="flex-1 bg-[#f8f9fa] py-8 px-4 sm:px-6 md:px-10 xl:px-16">
      <div className="w-full max-w-[1920px] mx-auto">

        {/* Title */}
        <div className="mb-8">
          <h1 className="font-sans text-[#0D2D5E] text-2xl md:text-3xl font-extrabold tracking-tight mb-2">
            Bibliothèque Universelle de la BEAC
          </h1>
          <p className="text-black/60 font-sans text-sm font-medium">
            Consultez le corpus documentaire et importez de nouvelles pièces pour indexation vectorielle.
          </p>
        </div>

        {/* Main content */}
        <div className="flex flex-col gap-6">

          {/* Action Bar (Search & Quick Type selection) */}
          <div className="bg-white p-4 border border-[#c4c6d0]/40 rounded-xl shadow-sm flex flex-col gap-4">
            {/* Search input */}
            <div className="relative flex items-center bg-gray-50 border border-gray-200 rounded-lg py-2.5 px-3 focus-within:border-[#C8971A]/70 focus-within:bg-white transition-all">
              <Search className="text-black/40 w-4 h-4 mr-2 shrink-0" />
              <input
                type="text"
                placeholder="Rechercher par mot-clé, pays, année ou titre..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-transparent border-none text-black placeholder:text-black/40 focus:outline-none w-full text-sm"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch("")}
                  aria-label="Effacer la recherche"
                  className="ml-2 shrink-0 text-black/30 hover:text-black/60 transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Badges select */}
            <div className="flex flex-wrap gap-2 pt-1 border-t border-gray-100">
              {docTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => handleTypeChange(type)}
                  className={`text-xs font-semibold px-4 py-2 rounded-full transition-all cursor-pointer ${
                    selectedType === type
                      ? "bg-[#0D2D5E] text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>

            {/* Pays, tri et reinitialisation */}
            <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-gray-100">
              <label className="flex items-center gap-2 text-xs font-semibold text-black/60">
                Pays
                <select
                  value={selectedCountry}
                  onChange={(e) => handleCountryChange(e.target.value)}
                  className="bg-gray-50 border border-gray-200 rounded-lg py-1.5 px-2 text-xs font-semibold text-[#0D2D5E] focus:outline-none focus:border-[#C8971A]/70 cursor-pointer"
                >
                  <option value="Tous">Tous</option>
                  {countries.map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </label>

              <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
                <button
                  type="button"
                  onClick={() => handleSortChange("recent")}
                  className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                    sortOrder === "recent" ? "bg-white text-[#0D2D5E] shadow-sm" : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  <ArrowDownAZ className="w-3.5 h-3.5" />
                  Plus récents
                </button>
                <button
                  type="button"
                  onClick={() => handleSortChange("oldest")}
                  className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md transition-all cursor-pointer ${
                    sortOrder === "oldest" ? "bg-white text-[#0D2D5E] shadow-sm" : "text-gray-500 hover:text-gray-700"
                  }`}
                >
                  <ArrowUpAZ className="w-3.5 h-3.5" />
                  Plus anciens
                </button>
              </div>

              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={resetFilters}
                  className="flex items-center gap-1 text-xs font-semibold text-[#C8971A] hover:text-[#0D2D5E] transition-colors cursor-pointer ml-auto"
                >
                  <X className="w-3.5 h-3.5" />
                  Réinitialiser les filtres
                </button>
              )}
            </div>
          </div>

          {/* Document Count Header */}
          <div className="flex justify-between items-center px-1 gap-3">
            <span className="text-xs font-bold text-black/60 font-mono">
              {loading ? "Chargement..." : `${total} DOCUMENT(S) — PAGE ${page + 1}/${totalPages || 1}`}
            </span>
            {!loading && searchMode === "semantic" && documents.length > 0 && (
              <span className="flex items-center gap-1.5 text-[11px] font-semibold text-[#C8971A] bg-[#C8971A]/10 border border-[#C8971A]/30 rounded-full px-3 py-1 shrink-0">
                <Sparkles className="w-3 h-3 fill-current" />
                Résultats par sens (aucune correspondance exacte du texte)
              </span>
            )}
          </div>

          {/* Document List */}
          {loading ? (
            <div className="flex items-center justify-center py-24">
              <Loader2 className="w-8 h-8 animate-spin text-[#C8971A]" />
            </div>
          ) : documents.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="bg-white p-5 border border-[#c4c6d0]/40 rounded-xl hover:border-[#C8971A] hover:shadow-md transition-all duration-200 shadow-sm flex flex-col justify-between"
                >
                  <div>
                    {/* Badge and metadata */}
                    <div className="flex justify-between items-start gap-2 mb-4">
                      <span className="bg-[#0D2D5E]/5 text-[#0D2D5E] border border-[#0D2D5E]/10 rounded px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider line-clamp-1">
                        {doc.type}
                      </span>
                      <span className="shrink-0 text-[10px] text-gray-500 font-mono">{doc.fileType}</span>
                    </div>

                    {/* Title */}
                    <h3
                      className="font-sans text-[#0D2D5E] text-sm font-bold mb-2 hover:text-[#C8971A] transition-colors line-clamp-2 break-words"
                      title={doc.title}
                    >
                      {doc.title}
                    </h3>

                    {/* Date & pays */}
                    <div className="flex items-center gap-2 mb-3 text-[11px] text-black/50 font-medium">
                      {doc.date && <span>{doc.date}</span>}
                      {doc.date && doc.country && <span className="text-gray-300">|</span>}
                      {doc.country && <span className="text-[#C8971A]/95 font-semibold">{doc.country}</span>}
                    </div>

                    {/* Description */}
                    {doc.description && (
                      <p className="text-black/70 font-sans text-xs mb-6 line-clamp-3 leading-relaxed">
                        {doc.description}
                      </p>
                    )}
                  </div>

                  {/* Bottom Action buttons */}
                  <div className="grid grid-cols-2 gap-2 pt-4 border-t border-gray-100">
                    <a
                      href={doc.url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-center gap-1.5 py-2 px-2 border border-gray-200 hover:border-black hover:bg-gray-50 text-black font-semibold text-xs rounded-lg transition-all text-center cursor-pointer"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      Consulter
                    </a>

                    <button
                      onClick={() => onAskDocInChat(`Explique-moi le document "${doc.title}".`, doc.id)}
                      className="flex items-center justify-center gap-1.5 py-2 px-2 bg-[#C8971A] hover:bg-[#F2B824] text-[#0D2D5E] font-bold text-xs rounded-lg transition-all cursor-pointer shadow-sm"
                    >
                      <Sparkles className="w-3.5 h-3.5 fill-current" />
                      Analyser IA
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : loadError ? (
            <div className="bg-white rounded-xl border border-dashed border-red-200 p-16 text-center select-none">
              <WifiOff className="mx-auto w-12 h-12 text-red-300 mb-4" />
              <h3 className="text-base font-sans font-bold text-gray-700 mb-1">Bibliothèque indisponible</h3>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                Le serveur backend n'a pas répondu. Vérifiez qu'il est bien démarré, puis réessayez.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-dashed border-gray-300 p-16 text-center select-none">
              <SearchCode className="mx-auto w-12 h-12 text-gray-300 mb-4" />
              <h3 className="text-base font-sans font-bold text-gray-700 mb-1">Aucun document trouvé</h3>
              <p className="text-xs text-gray-500 max-w-sm mx-auto">
                Essayez d'ajuster vos critères de tri ou de modifier le texte recherché.
              </p>
            </div>
          )}

          {/* Pagination */}
          {!loading && totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-2 rounded-lg border border-gray-200 hover:border-[#C8971A] disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4 text-[#0D2D5E]" />
              </button>
              <span className="text-xs font-bold text-[#0D2D5E] font-mono">
                {page + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-2 rounded-lg border border-gray-200 hover:border-[#C8971A] disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer"
              >
                <ChevronRightIcon className="w-4 h-4 text-[#0D2D5E]" />
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
