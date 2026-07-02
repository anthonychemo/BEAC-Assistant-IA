import React, { useState, useRef, useEffect } from "react";
import { ChatMessage } from "../types";
import { Send, Sparkles, Terminal, ShieldCheck, Database, HelpCircle, CornerDownLeft, Loader2, Info, Trash2, FileText, ChevronDown, ChevronUp } from "lucide-react";
import { motion } from "motion/react";

interface IAAssistantProps {
  messages: ChatMessage[];
  onSendMessage: (text: string) => Promise<void>;
  isThinking: boolean;
  onClearHistory: () => void;
  suggestedPrompt: string;
  setSuggestedPrompt: (text: string) => void;
}

export default function IAAssistant({
  messages,
  onSendMessage,
  isThinking,
  onClearHistory,
  suggestedPrompt,
  setSuggestedPrompt,
}: IAAssistantProps) {
  const [inputText, setInputText] = useState("");
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const feedEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    if (suggestedPrompt) {
      setInputText(suggestedPrompt);
      // immediately clear suggestion so user can edit/send manually
      setSuggestedPrompt("");
    }
  }, [suggestedPrompt, setSuggestedPrompt]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isThinking) return;
    onSendMessage(inputText.trim());
    setInputText("");
  };

  const handleTopicClick = (prompt: string) => {
    setInputText(prompt);
  };

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      next.has(msgId) ? next.delete(msgId) : next.add(msgId);
      return next;
    });
  };

  // Safe custom simple markdown renderer for bold words (**word**) and bullet points (- point) and line breaks
  const formatMessageText = (text: string) => {
    if (!text) return "";
    
    // Split into lines
    const lines = text.split("\n");
    return lines.map((line, idx) => {
      let formattedLine = line;

      // Replace bold syntax **text** with <strong>text</strong>
      const boldRegex = /\*\*(.*?)\*\*/g;
      formattedLine = formattedLine.replace(boldRegex, "<strong>$1</strong>");

      // Check if it is a list bullet point
      if (line.trim().startsWith("- ")) {
        const itemContent = formattedLine.trim().substring(2);
        return (
          <li key={idx} className="ml-4 list-disc text-xs md:text-sm my-1 leading-relaxed" 
              dangerouslySetInnerHTML={{ __html: itemContent }} />
        );
      }

      return (
        <p key={idx} className="min-h-[1.2rem] text-xs md:text-sm my-1.5 leading-relaxed"
           dangerouslySetInnerHTML={{ __html: formattedLine }} />
      );
    });
  };

  const sampleTopics = [
    {
      title: "Régulation des réserves",
      prompt: "Quel est le taux actuel de réserves obligatoires pour les banques CEMAC ?",
      desc: "Instructions COBAC de contrôle de la liquidité régionale."
    },
    {
      title: "Perspectives d'Inflation",
      prompt: "Quellle est la prévision d'inflation régionale dans la zone CEMAC pour l'année ?",
      desc: "Analyses de convergence selon les critères de l'UMAC."
    },
    {
      title: "Ressources à disposition",
      prompt: "Quels rapports d'études et statistiques sont disponibles dans le corpus sémantique ?",
      desc: "Index de volumes monétaires et études historiques."
    },
    {
      title: "Rôle de la COBAC",
      prompt: "Quel est le cadre réglementaire de contrôle des banques de la CEMAC par la COBAC ?",
      desc: "Coopération monétaire et surveillance prudentielle."
    }
  ];

  return (
    <div className="flex-1 bg-[#f8f9fa] flex flex-col lg:flex-row h-[calc(100vh-4rem)] origin-top">
      
      {/* Left Sidebar - Typical Topics */}
      <div className="w-full lg:w-80 bg-[#edeeef] border-b lg:border-b-0 lg:border-r border-[#c4c6d0]/40 p-6 flex flex-col justify-between shrink-0 h-48 lg:h-full overflow-y-auto">
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-2 select-none">
            <Terminal className="w-4 h-4 text-[#0D2D5E]" />
            <h3 className="font-sans font-bold text-[#0D2D5E] text-xs uppercase tracking-wider">
              Thèmes d'Interrogation
            </h3>
          </div>

          <div className="flex lg:flex-col gap-3 overflow-x-auto lg:overflow-x-visible pb-2 lg:pb-0 scrollbar-none">
            {sampleTopics.map((topic, index) => (
              <button
                key={index}
                onClick={() => handleTopicClick(topic.prompt)}
                className="bg-white p-3.5 rounded-lg border border-[#c4c6d0]/30 hover:border-[#C8971A] text-left transition-all shrink-0 w-64 lg:w-full hover:shadow-sm focus:outline-none focus:ring-1 focus:ring-[#C8971A]/40 cursor-pointer"
              >
                <div className="font-sans font-bold text-xs text-[#0D2D5E] mb-1">
                  {topic.title}
                </div>
                <div className="text-[10px] text-black/60 line-clamp-2 leading-relaxed">
                  {topic.desc}
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="hidden lg:flex flex-col gap-4 pt-6 border-t border-gray-200">
          <div className="flex items-center gap-2 bg-white/50 p-3 rounded-lg border border-[#c4c6d0]/20 select-none">
            <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
            <div className="flex flex-col leading-tight">
              <span className="text-[10px] font-bold text-[#0D2D5E]">Canal Sécurisé</span>
              <span className="text-[9px] text-gray-500">Chiffrement AES-256</span>
            </div>
          </div>
          
          <button
            onClick={onClearHistory}
            className="text-left text-[11px] font-bold text-red-500 hover:text-red-600 transition-colors cursor-pointer"
          >
            Effacer l'historique des requêtes
          </button>
        </div>
      </div>

      {/* Right Column - Conversational Feed */}
      <div className="flex-1 flex flex-col min-h-0 bg-white relative">
        
        {/* Chat Header Info bar */}
        <div className="h-14 border-b border-gray-100 px-4 md:px-6 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-2 md:gap-2.5">
            <div className="w-2 rounded-full bg-emerald-500 animate-pulse h-2 shrink-0" />
            <div className="flex flex-col">
              <span className="font-sans font-bold text-xs text-[#0D2D5E] leading-none mb-1">Assistant BEAC IA</span>
              <span className="text-[9px] md:text-[10px] text-black/50 font-medium leading-none">Corpus de la zone CEMAC</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-1.5 bg-gray-50 border border-gray-100 rounded-full px-3 py-1 shrink-0 select-none">
              <Database className="w-3 h-3 text-[#C8971A]" />
              <span className="text-[9px] text-gray-500 font-bold font-mono">gemini-3.5-flash</span>
            </div>
            
            {/* Clear history button for mobile/multi-device accessibility */}
            <button
              onClick={onClearHistory}
              className="flex items-center gap-1 py-1.5 px-2.5 rounded-lg border border-red-100 bg-red-50/50 hover:bg-red-50 text-red-600 font-bold text-[10px] uppercase tracking-wide transition-all active:scale-95 cursor-pointer shrink-0"
              title="Effacer l'historique de discussion"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span className="hidden xs:inline">Réinitialiser</span>
            </button>
          </div>
        </div>

        {/* Message Feed Canvas */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          
          {/* Welcome Message Card */}
          <div className="bg-[#f8f9fa] border border-[#c4c6d0]/20 p-5 rounded-xl max-w-2xl mx-auto flex gap-4 select-none mb-8">
            <div className="w-9 h-9 rounded-full bg-[#0D2D5E]/10 flex items-center justify-center shrink-0">
              <HelpCircle className="w-5 h-5 text-[#0D2D5E]" />
            </div>
            <div className="flex flex-col gap-2">
              <h4 className="font-sans font-bold text-xs text-[#0D2D5E] uppercase tracking-wide">
                Comment interroger l'Assistant de la Banque Centrale ?
              </h4>
              <p className="text-black/70 font-sans text-xs leading-relaxed">
                Posez des questions sur les taux d'intérêt, les directives COBAC ou l'historique d'inflation. L'intelligence s'appuie sur le corpus de rapports agrégés de la CEMAC pour étayer ses réponses de façon rigoureuse.
              </p>
            </div>
          </div>

          {messages.map((msg) => {
            const isUser = msg.role === "user";
            return (
              <div
                key={msg.id}
                className={`flex gap-4 max-w-3xl ${isUser ? "ml-auto justify-end" : "mr-auto"}`}
              >
                {/* Assistant icon */}
                {!isUser && (
                  <div className="w-8 h-8 rounded-full bg-[#C8971A] flex items-center justify-center shrink-0 shadow-sm text-[#0D2D5E]">
                    <Sparkles className="w-4 h-4 fill-current" />
                  </div>
                )}

                {/* Bubble content */}
                <div
                  className={`rounded-2xl p-4 px-5 shadow-sm border max-w-xl ${
                    isUser
                      ? "bg-[#0D2D5E] text-white border-transparent rounded-tr-none"
                      : "bg-[#edeeef]/40 text-[#0D2D5E] border-[#c4c6d0]/20 rounded-tl-none font-medium"
                  }`}
                >
                  <div className="prose prose-sm break-words">
                    {formatMessageText(msg.content)}
                  </div>
                  
                  {/* Timestamp / simulated notice */}
                  <div className="flex justify-between items-center mt-3 pt-2 border-t border-black/5">
                    <span className="text-[9px] opacity-40 font-mono font-bold">
                      {msg.timestamp}
                    </span>
                    {!isUser && (
                      <span className="text-[9px] opacity-65 text-[#C8971A] font-semibold flex items-center gap-1 font-sans">
                        <Info className="w-2.5 h-2.5" /> Source Certifiée BEAC
                      </span>
                    )}
                  </div>
                </div>

                {/* Sources panel (assistant only) */}
                {!isUser && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-1.5 max-w-xl w-full">
                    <button
                      onClick={() => toggleSources(msg.id)}
                      className="flex items-center gap-1.5 text-[10px] font-bold text-[#0D2D5E]/60 hover:text-[#C8971A] transition-colors"
                    >
                      <FileText className="w-3 h-3" />
                      {msg.sources.length} source{msg.sources.length > 1 ? "s" : ""}
                      {expandedSources.has(msg.id)
                        ? <ChevronUp className="w-3 h-3" />
                        : <ChevronDown className="w-3 h-3" />
                      }
                    </button>
                    {expandedSources.has(msg.id) && (
                      <div className="mt-1.5 space-y-1">
                        {msg.sources.map((src, i) => (
                          <div key={i} className="bg-[#f0f2f5] border border-[#c4c6d0]/30 rounded-lg px-3 py-2 text-[10px] text-[#0D2D5E]">
                            <span className="font-bold">{src.source}</span>
                            {src.year && <span className="ml-2 text-gray-500">({src.year})</span>}
                            {src.category && <span className="ml-2 text-[#C8971A] font-semibold">{src.category}</span>}
                            {src.score != null && (
                              <span className="ml-2 text-gray-400">score: {src.score.toFixed(2)}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* User avatar */}
                {isUser && (
                  <div className="w-8 h-8 rounded-full bg-[#0D2D5E]/10 flex items-center justify-center shrink-0 border border-[#0D2D5E]/20 text-[#0D2D5E] font-bold text-xs select-none">
                    U
                  </div>
                )}
              </div>
            );
          })}

          {/* Thinking screen state */}
          {isThinking && (
            <div className="flex gap-4 max-w-3xl mr-auto animate-pulse">
              <div className="w-8 h-8 rounded-full bg-[#C8971A]/50 flex items-center justify-center shrink-0 text-[#0D2D5E]">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
              <div className="rounded-2xl p-4 px-5 bg-[#edeeef]/30 text-gray-400 border border-transparent rounded-tl-none flex items-center gap-2">
                <span className="text-xs font-semibold">L'Assistant parcourt la bibliothèque numérique...</span>
              </div>
            </div>
          )}

          <div ref={feedEndRef} />
        </div>

        {/* Input Bar Form */}
        <div className="p-4 border-t border-gray-100 bg-white shrink-0">
          <form onSubmit={handleSubmit} className="max-w-4xl mx-auto relative flex items-center">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Saisissez votre question institutionnelle..."
              disabled={isThinking}
              className="w-full bg-[#f8f9fa] border border-[#c4c6d0]/40 focus:border-[#C8971A]/70 focus:bg-white focus:outline-none rounded-xl py-3.5 pl-5 pr-14 text-sm font-sans placeholder:text-gray-400"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || isThinking}
              className={`absolute right-2 p-2.5 rounded-lg transition-all ${
                inputText.trim() && !isThinking
                  ? "bg-[#0D2D5E] text-[#C8971A] hover:bg-[#00183e] active:scale-95 cursor-pointer"
                  : "bg-gray-100 text-gray-300 pointer-events-none"
              }`}
              title="Envoyer la question"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="flex items-center justify-center gap-1 mt-2 text-[10px] text-gray-400 select-none">
            <CornerDownLeft className="w-3 h-3" />
            <span>Appuyez sur Entrée pour envoyer votre message de recherche</span>
          </div>
        </div>

      </div>
    </div>
  );
}
