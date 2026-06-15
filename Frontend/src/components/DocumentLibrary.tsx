import React, { useState, useEffect } from "react";
import { Document, DocumentType } from "../types";
import { Search, SearchCode, Eye, FileText, Upload, Sparkles, Filter, Database, CheckSquare, Square, Trash } from "lucide-react";
import { motion } from "motion/react";

interface DocumentLibraryProps {
  documents: Document[];
  onUploadDocument: (doc: Document) => void;
  onAskDocInChat: (text: string) => void;
  preSelectedType: string | null;
  setPreSelectedType: (type: string | null) => void;
}

export default function DocumentLibrary({
  documents,
  onUploadDocument,
  onAskDocInChat,
  preSelectedType,
  setPreSelectedType,
}: DocumentLibraryProps) {
  const [search, setSearch] = useState("");
  const [selectedType, setSelectedType] = useState<string>("Tous");
  const [selectedSections, setSelectedSections] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>("");

  useEffect(() => {
    if (preSelectedType) {
      setSelectedType(preSelectedType);
      // reset so we don't sticky-lock it forever
      setPreSelectedType(null);
    }
  }, [preSelectedType, setPreSelectedType]);

  const toggleSection = (section: string) => {
    if (selectedSections.includes(section)) {
      setSelectedSections(selectedSections.filter((s) => s !== section));
    } else {
      setSelectedSections([...selectedSections, section]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const processUploadedFile = (name: string, size: number) => {
    const formattedSize = (size / (1024 * 1024)).toFixed(1) + " MB";
    const newDoc: Document = {
      id: `doc-uploaded-${Date.now()}`,
      title: name.replace(/\.[^/.]+$/, ""), // remove extension
      type: "Rapports",
      fileType: name.split(".").pop()?.toUpperCase() || "PDF",
      fileSize: formattedSize,
      date: new Date().toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" }),
      description: "Ce document a été importé par l'utilisateur. Il est temporairement archivé et indexé en mémoire locale pour l'analyse IA.",
      section: "Politique Monétaire",
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
      const file = e.dataTransfer.files[0];
      processUploadedFile(file.name, file.size);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      processUploadedFile(file.name, file.size);
    }
  };

  // Filter logic
  const filteredDocs = documents.filter((doc) => {
    const matchesSearch = doc.title.toLowerCase().includes(search.toLowerCase()) || 
                          doc.description.toLowerCase().includes(search.toLowerCase());
    
    const matchesType = selectedType === "Tous" || doc.type === selectedType;

    const matchesSection = selectedSections.length === 0 || selectedSections.includes(doc.section);

    return matchesSearch && matchesType && matchesSection;
  });

  const docTypes: ("Tous" | DocumentType)[] = ["Tous", "Rapports", "Bulletins", "Working Papers", "Communiqués", "Réglementation"];
  const docSections = ["Politique Monétaire", "Stabilité Financière", "Études Statistiques"];

  return (
    <div className="flex-1 bg-[#f8f9fa] py-8 px-4 md:px-16">
      <div className="max-w-[1280px] mx-auto">
        
        {/* Title */}
        <div className="mb-8">
          <h1 className="font-sans text-[#0D2D5E] text-2xl md:text-3xl font-extrabold tracking-tight mb-2">
            Bibliothèque Universelle de la BEAC
          </h1>
          <p className="text-black/60 font-sans text-sm font-medium">
            Consultez le corpus documentaire et importez de nouvelles pièces pour indexation vectorielle.
          </p>
        </div>

        {/* Top Controls Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-8 items-start">
          
          {/* Main List and filter bar */}
          <div className="lg:col-span-9 flex flex-col gap-6">
            
            {/* Action Bar (Search & Quick Type selection) */}
            <div className="bg-white p-4 border border-[#c4c6d0]/40 rounded-xl shadow-sm flex flex-col gap-4">
              {/* Search input */}
              <div className="relative flex items-center bg-gray-50 border border-gray-200 rounded-lg py-2.5 px-3 focus-within:border-[#C8971A]/70 focus-within:bg-white transition-all">
                <Search className="text-black/40 w-4 h-4 mr-2" />
                <input
                  type="text"
                  placeholder="Rechercher par mot-clé, date ou titre..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="bg-transparent border-none text-black placeholder:text-black/40 focus:outline-none w-full text-sm"
                />
              </div>

              {/* Badges select */}
              <div className="flex flex-wrap gap-2 pt-1 border-t border-gray-100">
                {docTypes.map((type) => (
                  <button
                    key={type}
                    onClick={() => setSelectedType(type)}
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
            </div>

            {/* Document Count Header */}
            <div className="flex justify-between items-center px-1">
              <span className="text-xs font-bold text-black/60 font-mono">
                {filteredDocs.length} DOCUMENT(S) TROUVÉ(S)
              </span>
            </div>

            {/* Document List */}
            {filteredDocs.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="bg-white p-6 border border-[#c4c6d0]/40 rounded-xl hover:border-[#C8971A] transition-all duration-200 shadow-sm flex flex-col justify-between"
                  >
                    <div>
                      {/* Badge and metadata */}
                      <div className="flex justify-between items-start gap-2 mb-4">
                        <span className="bg-[#0D2D5E]/5 text-[#0D2D5E] border border-[#0D2D5E]/10 rounded px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider">
                          {doc.type}
                        </span>
                        <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
                          <span>{doc.fileType}</span>
                          <span className="w-1 h-1 bg-gray-400 rounded-full" />
                          <span>{doc.fileSize}</span>
                        </div>
                      </div>

                      {/* Title */}
                      <h3 className="font-sans text-[#0D2D5E] text-base font-bold mb-2 hover:text-[#C8971A] transition-colors line-clamp-2">
                        {doc.title}
                      </h3>

                      {/* Date & section */}
                      <div className="flex items-center gap-2 mb-3 text-[11px] text-black/50 font-medium">
                        <span>{doc.date}</span>
                        <span className="text-gray-300">|</span>
                        <span className="text-[#C8971A]/95 font-semibold">{doc.section}</span>
                      </div>

                      {/* Description */}
                      <p className="text-black/70 font-sans text-xs mb-6 line-clamp-3 leading-relaxed">
                        {doc.description}
                      </p>
                    </div>

                    {/* Bottom Action buttons */}
                    <div className="grid grid-cols-2 gap-3 pt-4 border-t border-gray-100">
                      <a
                        href={doc.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center justify-center gap-1.5 py-2 px-3 border border-gray-200 hover:border-black hover:bg-gray-50 text-black font-semibold text-xs rounded-lg transition-all text-center cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Consulter
                      </a>

                      <button
                        onClick={() => onAskDocInChat(`Explique-moi le document "${doc.title}" d'octobre/mars disponible dans notre bibliothèque.`)}
                        className="flex items-center justify-center gap-1.5 py-2 px-3 bg-[#C8971A] hover:bg-[#F2B824] text-[#0D2D5E] font-bold text-xs rounded-lg transition-all cursor-pointer shadow-sm"
                      >
                        <Sparkles className="w-3.5 h-3.5 fill-current" />
                        Analyser IA
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-dashed border-gray-300 p-16 text-center select-none">
                <SearchCode className="mx-auto w-12 h-12 text-gray-300 mb-4" />
                <h3 className="text-base font-sans font-bold text-gray-700 mb-1">Aucun document trouvé</h3>
                <p className="text-xs text-gray-500 max-w-sm mx-auto">
                  Essayez d'ajuster vos critères de tri, de modifier le texte recherché ou d'ajouter une nouvelle directive monétaire.
                </p>
              </div>
            )}
          </div>

          {/* Right sidebar filters and uploads */}
          <div className="lg:col-span-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-6 w-full">
            
            {/* Filter segments checkbox panel */}
            <div className="bg-white p-6 border border-[#c4c6d0]/40 rounded-xl shadow-sm">
              <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100">
                <Filter className="w-4 h-4 text-[#C8971A]" />
                <h4 className="font-sans text-[#0D2D5E] text-sm font-bold">Thématiques</h4>
              </div>

              <div className="flex flex-col gap-3">
                {docSections.map((sec) => {
                  const isChecked = selectedSections.includes(sec);
                  return (
                    <button
                      key={sec}
                      onClick={() => toggleSection(sec)}
                      className="flex items-center gap-2 text-left text-xs font-semibold text-black/85 transition-colors hover:text-[#0D2D5E] cursor-pointer"
                    >
                      {isChecked ? (
                        <CheckSquare className="w-4 h-4 text-[#C8971A] shrink-0" />
                      ) : (
                        <Square className="w-4 h-4 text-gray-300 shrink-0" />
                      )}
                      <span>{sec}</span>
                    </button>
                  );
                })}
              </div>

              {selectedSections.length > 0 && (
                <button
                  onClick={() => setSelectedSections([])}
                  className="mt-4 text-[10px] text-red-500 hover:underline font-bold"
                >
                  Réinitialiser les filtres
                </button>
              )}
            </div>

            {/* Institutional File Upload zone */}
            <div className="bg-white p-6 border border-[#c4c6d0]/40 rounded-xl shadow-sm">
              <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100">
                <Upload className="w-4 h-4 text-[#0D2D5E]" />
                <h4 className="font-sans text-[#0D2D5E] text-sm font-bold">Indexation Locale</h4>
              </div>

              <p className="text-[11px] text-black/60 mb-4 leading-relaxed font-sans">
                Déposez un document PDF ou XLS pour l'intégrer instantanément au moteur d'indexation locale de votre session.
              </p>

              {/* Drag n drop box */}
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`border-2 border-dashed rounded-lg p-6 py-8 text-center transition-all relative ${
                  isDragging
                    ? "border-[#C8971A] bg-[#C8971A]/5"
                    : "border-gray-200 hover:border-gray-300 bg-gray-50"
                }`}
              >
                <input
                  type="file"
                  id="library-file-upload"
                  accept=".pdf,.xls,.xlsx,.doc,.docx,.txt"
                  className="hidden"
                  onChange={handleFileChange}
                />
                
                {uploadStatus ? (
                  <div className="flex flex-col items-center justify-center gap-2">
                    <Database className="w-6 h-6 text-[#C8971A] animate-bounce" />
                    <span className="text-xs font-bold text-[#0D2D5E]">{uploadStatus}</span>
                  </div>
                ) : (
                  <label htmlFor="library-file-upload" className="cursor-pointer block">
                    <FileText className="mx-auto w-8 h-8 text-gray-400 mb-2" />
                    <span className="text-xs font-bold text-[#0D2D5E] block mb-1">Sélectionner un fichier</span>
                    <span className="text-[9px] text-gray-500 block">PDF, Word, Excel jusqu'à 20 Mo</span>
                  </label>
                )}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
