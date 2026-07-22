import React, { useState, useRef, useEffect } from "react";
import { ChatMessage } from "../types";
import { Send, Sparkles, Terminal, ShieldCheck, Database, HelpCircle, CornerDownLeft, Loader2, Trash2, FileText, ChevronDown, ChevronUp, AlertTriangle, RefreshCw, Square, ThumbsUp, ThumbsDown, SearchCode, Calculator, Layers, MessageCircleQuestion } from "lucide-react";
import { motion } from "motion/react";

// Miroir exact de NO_ANSWER_MESSAGE (beac-rag-backend/src/rag/prompts.py) : le
// LLM repond exactement ce texte quand le contexte recupere ne permet pas de
// repondre. Dans ce cas, les sources/le type de recherche ne doivent pas
// s'afficher comme s'ils avaient servi a une reponse trouvee — ils induiraient
// en erreur (l'assistant dit "je ne sais pas" a cote de "12 sources").
const NO_ANSWER_MESSAGE = "Je ne dispose pas d'informations suffisantes pour répondre à cette question. Je vous invite à consulter le site officiel : https://www.beac.int";

interface IAAssistantProps {
  messages: ChatMessage[];
  onSendMessage: (text: string, documentId?: string) => Promise<void>;
  isThinking: boolean;
  isStreaming: boolean;
  onStopGeneration: () => void;
  onFeedback: (messageId: string, isPositive: boolean) => void;
  onClearHistory: () => void;
  suggestedPrompt: string;
  setSuggestedPrompt: (text: string) => void;
  suggestedDocumentId?: string;
  setSuggestedDocumentId: (id: string | undefined) => void;
  selectedModel: { key: string; label: string };
  onModelChange: (model: { key: string; label: string }) => void;
  availableModels: { key: string; label: string }[];
}

// Etiquette lisible + icone pour le type de recherche reellement effectue par
// le backend (query_router.py), transmis mais jusqu'ici jamais affiche.
const QUERY_TYPE_INFO: Record<string, { label: string; Icon: typeof SearchCode }> = {
  vector: { label: "Recherche sémantique", Icon: SearchCode },
  sql: { label: "Donnée chiffrée", Icon: Calculator },
  hybrid: { label: "Recherche hybride", Icon: Layers },
  meta: { label: "Question système", Icon: MessageCircleQuestion },
};

// Echappe le HTML avant tout formatage : le texte vient du LLM (donc,
// indirectement, de documents ingeres) et ne doit jamais etre interprete
// comme du balisage par le navigateur (protection XSS).
const escapeHtml = (raw: string) =>
  raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

// Formatage inline sur du texte deja echappe : gras (**mot**), liens markdown
// [texte](url) et URLs nues. Seuls les schemas http(s) sont acceptes ; comme
// le texte est echappe avant cette etape, aucun guillemet/chevron injecte ne
// peut casser hors de l'attribut href genere.
const formatInline = (escaped: string): string => {
  let out = escaped.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  out = out.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noreferrer" class="underline decoration-dotted hover:decoration-solid font-semibold">$1</a>'
  );
  out = out.replace(
    /(?<!")(https?:\/\/[^\s<]+)/g,
    '<a href="$1" target="_blank" rel="noreferrer" class="underline decoration-dotted hover:decoration-solid font-semibold">$1</a>'
  );
  return out;
};

const isTableRow = (line: string) => /^\s*\|.*\|\s*$/.test(line);
const isTableSeparator = (line: string) => /^\s*\|[\s:|-]+\|\s*$/.test(line);
const isOrderedItem = (line: string) => /^\s*\d+\.\s+/.test(line);
const isUnorderedItem = (line: string) => /^\s*-\s+/.test(line);

function splitTableRow(line: string): string[] {
  let trimmed = line.trim();
  if (trimmed.startsWith("|")) trimmed = trimmed.slice(1);
  if (trimmed.endsWith("|")) trimmed = trimmed.slice(0, -1);
  return trimmed.split("|").map((cell) => cell.trim());
}

// Rendu markdown minimal et sûr : gras, liens, listes à puces/numérotées et
// tableaux, regroupés en blocs valides (un seul <ul>/<ol>/<table> par groupe
// de lignes consécutives) plutôt qu'un <li> orphelin par ligne.
function formatMessageText(text: string): React.ReactNode[] {
  if (!text) return [];

  const lines = text.split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const header = splitTableRow(line);
      const bodyRows: string[][] = [];
      i += 2;
      while (i < lines.length && isTableRow(lines[i])) {
        bodyRows.push(splitTableRow(lines[i]));
        i++;
      }
      blocks.push(
        <div key={`table-${blocks.length}`} className="overflow-x-auto my-2 rounded-lg border border-black/10">
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr className="bg-black/5">
                {header.map((cell, ci) => (
                  <th
                    key={ci}
                    className="px-2 py-1.5 text-left font-bold border-b border-black/10"
                    dangerouslySetInnerHTML={{ __html: formatInline(escapeHtml(cell)) }}
                  />
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((row, ri) => (
                <tr key={ri} className={ri % 2 === 1 ? "bg-black/2" : undefined}>
                  {row.map((cell, ci) => (
                    <td
                      key={ci}
                      className="px-2 py-1.5 border-b border-black/5 align-top"
                      dangerouslySetInnerHTML={{ __html: formatInline(escapeHtml(cell)) }}
                    />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    if (isOrderedItem(line)) {
      const items: string[] = [];
      while (i < lines.length && isOrderedItem(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      blocks.push(
        <ol key={`ol-${blocks.length}`} className="list-decimal ml-5 my-1.5 space-y-0.5">
          {items.map((item, ii) => (
            <li
              key={ii}
              className="text-xs md:text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: formatInline(escapeHtml(item)) }}
            />
          ))}
        </ol>
      );
      continue;
    }

    if (isUnorderedItem(line)) {
      const items: string[] = [];
      while (i < lines.length && isUnorderedItem(lines[i])) {
        items.push(lines[i].replace(/^\s*-\s+/, ""));
        i++;
      }
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="list-disc ml-5 my-1.5 space-y-0.5">
          {items.map((item, ii) => (
            <li
              key={ii}
              className="text-xs md:text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: formatInline(escapeHtml(item)) }}
            />
          ))}
        </ul>
      );
      continue;
    }

    blocks.push(
      <p
        key={`p-${blocks.length}`}
        className="min-h-[1.2rem] text-xs md:text-sm my-1.5 leading-relaxed"
        dangerouslySetInnerHTML={{ __html: formatInline(escapeHtml(line)) }}
      />
    );
    i++;
  }

  return blocks;
}

// Reserve de themes d'interrogation couvrant le corpus BEAC ; on en tire 4 au
// hasard a chaque visite plutot que d'afficher toujours les 4 memes.
const TOPIC_POOL: { title: string; prompt: string; desc: string }[] = [
  {
    title: "Régulation des réserves",
    prompt: "Quel est le taux actuel de réserves obligatoires pour les banques CEMAC ?",
    desc: "Instructions COBAC de contrôle de la liquidité régionale.",
  },
  {
    title: "Perspectives d'Inflation",
    prompt: "Quelle est la prévision d'inflation régionale dans la zone CEMAC pour l'année ?",
    desc: "Analyses de convergence selon les critères de l'UMAC.",
  },
  {
    title: "Ressources à disposition",
    prompt: "Quels rapports d'études et statistiques sont disponibles dans le corpus sémantique ?",
    desc: "Index de volumes monétaires et études historiques.",
  },
  {
    title: "Rôle de la COBAC",
    prompt: "Quel est le cadre réglementaire de contrôle des banques de la CEMAC par la COBAC ?",
    desc: "Coopération monétaire et surveillance prudentielle.",
  },
  {
    title: "Systèmes de paiement",
    prompt: "Comment fonctionnent les systèmes de paiement régionaux de la zone CEMAC ?",
    desc: "Infrastructures SYGMA/SYSTAC et interbancarité.",
  },
  {
    title: "Réglementation des changes",
    prompt: "Quelles sont les règles de réglementation des changes extérieurs en zone CEMAC ?",
    desc: "Cadre UMAC applicable aux opérations en devises.",
  },
  {
    title: "Masse monétaire",
    prompt: "Quelle est l'évolution récente de la masse monétaire dans la zone CEMAC ?",
    desc: "Agrégats monétaires et politique de refinancement.",
  },
  {
    title: "Émission monétaire",
    prompt: "Quelles sont les règles d'émission des billets et pièces par la BEAC ?",
    desc: "Prérogatives d'émission et sécurité fiduciaire.",
  },
];

function sampleTopics(pool: typeof TOPIC_POOL, count: number): typeof TOPIC_POOL {
  const shuffled = [...pool];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled.slice(0, count);
}

export default function IAAssistant({
  messages,
  onSendMessage,
  isThinking,
  isStreaming,
  onStopGeneration,
  onFeedback,
  onClearHistory,
  suggestedPrompt,
  setSuggestedPrompt,
  suggestedDocumentId,
  setSuggestedDocumentId,
  selectedModel,
  onModelChange,
  availableModels,
}: IAAssistantProps) {
  const [inputText, setInputText] = useState("");
  // Document cible par le bouton "Analyser IA" de la bibliotheque : reste
  // attache tant que la question n'a pas ete envoyee (l'utilisateur peut la
  // relire/corriger avant d'appuyer sur Entree).
  const [pendingDocumentId, setPendingDocumentId] = useState<string | undefined>(undefined);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [showModelMenu, setShowModelMenu] = useState(false);
  const feedEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [showSidebar, setShowSidebar] = useState(false);
  const [topics, setTopics] = useState(() => sampleTopics(TOPIC_POOL, 4));

  // Enrichit la reserve de themes avec l'annee la plus recente reellement
  // indexee des qu'elle est connue (evite un theme fige qui devient faux).
  useEffect(() => {
    fetch("/api/metadata")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const years: number[] = data?.years ?? [];
        if (years.length === 0) return;
        const latestYear = Math.max(...years);
        const pool = [
          ...TOPIC_POOL,
          {
            title: `Rapports ${latestYear}`,
            prompt: `Que disent les rapports de politique monétaire de ${latestYear} ?`,
            desc: `Synthèse des publications les plus récentes indexées (${latestYear}).`,
          },
        ];
        setTopics(sampleTopics(pool, 4));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isThinking]);

  useEffect(() => {
    if (suggestedPrompt) {
      setInputText(suggestedPrompt);
      setPendingDocumentId(suggestedDocumentId);
      // immediately clear suggestion so user can edit/send manually
      setSuggestedPrompt("");
      setSuggestedDocumentId(undefined);
    }
  }, [suggestedPrompt, suggestedDocumentId, setSuggestedPrompt, setSuggestedDocumentId]);

  // Auto-resize de la zone de saisie multiligne (jusqu'a une hauteur max en CSS).
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [inputText]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isStreaming) return;
    onSendMessage(inputText.trim(), pendingDocumentId);
    setInputText("");
    setPendingDocumentId(undefined);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Entree envoie ; Maj+Entree insere un saut de ligne.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (inputText.trim() && !isStreaming) {
        onSendMessage(inputText.trim(), pendingDocumentId);
        setInputText("");
        setPendingDocumentId(undefined);
      }
    }
  };

  const handleTopicClick = (prompt: string) => {
    setInputText(prompt);
    // Un theme suggere de la barre laterale n'est jamais lie a un document
    // precis : on efface un eventuel documentId en attente (ex: si l'utilisateur
    // avait clique "Analyser IA" puis change d'avis sans envoyer).
    setPendingDocumentId(undefined);
  };

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      next.has(msgId) ? next.delete(msgId) : next.add(msgId);
      return next;
    });
  };

  return (
    <div className="flex-1 bg-[#f8f9fa] flex flex-col lg:flex-row h-[calc(100vh-4rem)]">
      
      {/* Left Sidebar - collapsible sur mobile */}
      <div className={`${showSidebar ? 'flex' : 'hidden'} lg:flex w-full lg:w-72 bg-[#edeeef] border-b lg:border-b-0 lg:border-r border-[#c4c6d0]/40 p-4 flex-col justify-between shrink-0 lg:h-full overflow-y-auto absolute lg:relative z-30 top-0 left-0 right-0 bottom-0`}>
        <div className="flex flex-col gap-5">
          <div className="flex items-center gap-2 select-none">
            <Terminal className="w-4 h-4 text-[#0D2D5E]" />
            <h3 className="font-sans font-bold text-[#0D2D5E] text-xs uppercase tracking-wider flex-1">
              Thèmes d'Interrogation
            </h3>
            <button onClick={() => setShowSidebar(false)} className="lg:hidden p-1 text-[#0D2D5E]/60 hover:text-[#0D2D5E]">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <div className="flex lg:flex-col gap-3 overflow-x-auto lg:overflow-x-visible pb-2 lg:pb-0">
            {topics.map((topic, index) => (
              <button
                key={index}
                onClick={() => { handleTopicClick(topic.prompt); setShowSidebar(false); }}
                className="bg-white p-3 rounded-lg border border-[#c4c6d0]/30 hover:border-[#C8971A] text-left transition-all shrink-0 w-56 lg:w-full hover:shadow-sm focus:outline-none focus:ring-1 focus:ring-[#C8971A]/40 cursor-pointer"
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
            Effacer l'historique des discussions
          </button>
        </div>
      </div>

      {/* Right Column - Conversational Feed */}
      <div className="flex-1 flex flex-col min-h-0 bg-white relative">
        
        {/* Chat Header Info bar */}
        <div className="h-14 border-b border-gray-100 px-4 md:px-6 flex items-center justify-between bg-white shrink-0">
          <div className="flex items-center gap-2 md:gap-2.5">
            <button onClick={() => setShowSidebar(true)} className="lg:hidden p-1.5 text-[#0D2D5E]/60 hover:text-[#0D2D5E] mr-1">
              <Terminal className="w-4 h-4" />
            </button>
            <div className="w-2 rounded-full bg-emerald-500 animate-pulse h-2 shrink-0" />
            <div className="flex flex-col">
              <span className="font-sans font-bold text-xs text-[#0D2D5E] leading-none mb-1">Assistant BEAC IA</span>
              <span className="text-[9px] md:text-[10px] text-black/50 font-medium leading-none">Corpus de la zone CEMAC</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="hidden sm:flex items-center gap-1.5 bg-gray-50 border border-gray-100 rounded-full px-3 py-1 shrink-0 select-none relative">
              <Database className="w-3 h-3 text-[#C8971A]" />
              {availableModels.length > 1 ? (
                <>
                  <button
                    onClick={() => setShowModelMenu((v) => !v)}
                    className="text-[9px] text-gray-500 font-bold font-mono flex items-center gap-1 hover:text-[#C8971A] transition-colors cursor-pointer"
                  >
                    {selectedModel.label}
                    <ChevronDown className="w-3 h-3" />
                  </button>
                  {showModelMenu && (
                    <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 min-w-[180px] py-1">
                      {availableModels.map((m) => (
                        <button
                          key={m.key}
                          onClick={() => { onModelChange(m); setShowModelMenu(false); }}
                          className={`w-full text-left px-3 py-2 text-[11px] font-medium hover:bg-gray-50 transition-colors cursor-pointer ${
                            selectedModel.key === m.key ? "text-[#C8971A] font-bold" : "text-gray-700"
                          }`}
                        >
                          {m.label}
                        </button>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <span className="text-[9px] text-gray-500 font-bold font-mono">{selectedModel.label}</span>
              )}
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

        {/* Message Feed Canvas : colonne centree, a la maniere Claude/ChatGPT */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-8 space-y-7">

            {/* Welcome Message Card */}
            <div className="bg-[#f8f9fa] border border-[#c4c6d0]/20 p-5 rounded-xl flex gap-4 select-none">
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

            {messages.map((msg, msgIdx) => {
              const isUser = msg.role === "user";
              const isError = !isUser && !!msg.isError;
              const retrySourceMsg = isError
                ? [...messages.slice(0, msgIdx)].reverse().find((m) => m.role === "user")
                : undefined;
              const retryText = retrySourceMsg?.content;
              // Les metadonnees (sources, type de recherche) arrivent AVANT le
              // premier token de la reponse (retrieval puis generation) : les
              // afficher des ce moment donnerait l'impression d'une reponse
              // vide accompagnee de sources, avant meme que l'assistant ait
              // ecrit quoi que ce soit. On attend donc qu'il y ait du contenu.
              const hasContent = !!msg.content;
              // L'assistant a explicitement declare ne pas avoir trouve la reponse :
              // les sources retrouvees n'ont pas ete jugees suffisantes, les afficher
              // comme preuve serait trompeur.
              const isNoAnswer = !isUser && msg.content?.trim() === NO_ANSWER_MESSAGE;
              const showFeedback = !isUser && !isError && msg.id !== "welcome-1" && hasContent;
              const showSources = !isUser && !isError && !isNoAnswer && hasContent && msg.sources && msg.sources.length > 0;
              const queryTypeInfo = !isUser && !isError && !isNoAnswer && hasContent && msg.query_type ? QUERY_TYPE_INFO[msg.query_type] : undefined;

              return (
                <div key={msg.id} className="flex gap-3 md:gap-4 items-start">
                  {/* Avatar */}
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 text-[11px] font-bold ${
                      isUser
                        ? "bg-[#0D2D5E]/10 border border-[#0D2D5E]/20 text-[#0D2D5E]"
                        : isError
                        ? "bg-amber-100 text-amber-600"
                        : "bg-[#C8971A] text-[#0D2D5E]"
                    }`}
                  >
                    {isUser ? "U" : isError ? <AlertTriangle className="w-3.5 h-3.5" /> : <Sparkles className="w-3.5 h-3.5 fill-current" />}
                  </div>

                  <div className="flex-1 min-w-0">
                    {/* Contenu : bulle pour l'utilisateur, texte simple pour l'assistant (comme Claude/ChatGPT) */}
                    {isUser ? (
                      <div className="inline-block max-w-full bg-[#f0f2f5] rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm text-[#0D2D5E] font-medium break-words whitespace-pre-wrap">
                        {msg.content}
                      </div>
                    ) : (
                      <div className={`prose prose-sm max-w-none break-words ${isError ? "text-amber-800" : "text-[#1f2937]"}`}>
                        {formatMessageText(msg.content)}
                      </div>
                    )}

                    {/* Ligne meta : horodatage + statut + actions, toujours discrete */}
                    <div className="flex flex-wrap items-center gap-3 mt-1.5">
                      <span className="text-[10px] text-black/30 font-mono font-semibold">{msg.timestamp}</span>

                      {isError && (
                        <span className="text-[10px] text-amber-700 font-semibold flex items-center gap-1">
                          <AlertTriangle className="w-2.5 h-2.5" /> Service temporairement indisponible
                        </span>
                      )}

                      {queryTypeInfo && (
                        <span className="text-[10px] text-[#C8971A]/80 font-semibold flex items-center gap-1">
                          <queryTypeInfo.Icon className="w-2.5 h-2.5" /> {queryTypeInfo.label}
                        </span>
                      )}

                      {isError && retryText && (
                        <button
                          onClick={() => onSendMessage(retryText, retrySourceMsg?.documentId)}
                          disabled={isStreaming}
                          className="flex items-center gap-1 text-[10px] font-bold text-amber-700 hover:text-amber-900 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                        >
                          <RefreshCw className="w-2.5 h-2.5" />
                          Réessayer
                        </button>
                      )}

                      {showFeedback && (
                        <div className="flex items-center gap-0.5">
                          <button
                            onClick={() => onFeedback(msg.id, true)}
                            disabled={!!msg.feedback}
                            title="Réponse utile"
                            className={`p-1 rounded-md transition-colors disabled:cursor-default ${
                              msg.feedback === "positive"
                                ? "text-emerald-600"
                                : "text-black/25 hover:text-emerald-600 hover:bg-emerald-50 cursor-pointer"
                            }`}
                          >
                            <ThumbsUp className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => onFeedback(msg.id, false)}
                            disabled={!!msg.feedback}
                            title="Réponse pas utile"
                            className={`p-1 rounded-md transition-colors disabled:cursor-default ${
                              msg.feedback === "negative"
                                ? "text-red-500"
                                : "text-black/25 hover:text-red-500 hover:bg-red-50 cursor-pointer"
                            }`}
                          >
                            <ThumbsDown className="w-3 h-3" />
                          </button>
                          {msg.feedback && <span className="text-[10px] text-black/30">Merci pour votre retour</span>}
                        </div>
                      )}

                      {showSources && (
                        <button
                          onClick={() => toggleSources(msg.id)}
                          className="flex items-center gap-1 text-[10px] font-semibold text-black/40 hover:text-[#C8971A] transition-colors cursor-pointer"
                        >
                          <FileText className="w-3 h-3" />
                          {msg.sources!.length} source{msg.sources!.length > 1 ? "s" : ""}
                          {expandedSources.has(msg.id) ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                      )}
                    </div>

                    {/* Sources deployees */}
                    {showSources && expandedSources.has(msg.id) && (
                      <div className="mt-2 space-y-1">
                        {msg.sources!.map((src, i) => (
                          <div key={i} className="bg-[#f0f2f5] border border-[#c4c6d0]/30 rounded-lg px-3 py-2 text-[10px] text-[#0D2D5E]">
                            {src.source_url ? (
                              <a href={src.source_url} target="_blank" rel="noreferrer" className="font-bold hover:underline">
                                {src.source}
                              </a>
                            ) : (
                              <span className="font-bold">{src.source}</span>
                            )}
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
                </div>
              );
            })}

            {/* Thinking screen state */}
            {isThinking && (
              <div className="flex gap-3 md:gap-4 items-start animate-pulse">
                <div className="w-7 h-7 rounded-full bg-[#C8971A]/50 flex items-center justify-center shrink-0 text-[#0D2D5E]">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                </div>
                <span className="text-sm font-medium text-gray-400 pt-0.5">
                  L'Assistant parcourt la bibliothèque numérique...
                </span>
              </div>
            )}

            <div ref={feedEndRef} />
          </div>
        </div>

        <div className="border-t border-gray-100 bg-white shrink-0">
          <div className="max-w-3xl mx-auto px-4 md:px-6 py-3 md:py-4">
            <form onSubmit={handleSubmit} className="relative flex items-end">
              <textarea
                ref={textareaRef}
                rows={1}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleInputKeyDown}
                placeholder="Posez votre question..."
                disabled={isStreaming}
                className="w-full max-h-40 resize-none bg-[#f8f9fa] border border-[#c4c6d0]/40 focus:border-[#C8971A]/70 focus:bg-white focus:outline-none rounded-2xl py-3 pl-4 pr-12 text-sm font-sans placeholder:text-gray-400"
              />
              {isStreaming ? (
                <button
                  type="button"
                  onClick={onStopGeneration}
                  title="Arrêter la génération"
                  className="absolute right-2 bottom-2 p-2 rounded-lg bg-red-50 text-red-600 hover:bg-red-100 active:scale-95 transition-all cursor-pointer"
                >
                  <Square className="w-4 h-4 fill-current" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!inputText.trim()}
                  className={`absolute right-2 bottom-2 p-2 rounded-lg transition-all ${
                    inputText.trim()
                      ? "bg-[#0D2D5E] text-[#C8971A] hover:bg-[#00183e] active:scale-95 cursor-pointer"
                      : "bg-gray-100 text-gray-300 pointer-events-none"
                  }`}
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </form>
            <div className="hidden md:flex items-center justify-center gap-1 mt-2 text-[10px] text-gray-400 select-none">
              <CornerDownLeft className="w-3 h-3" />
              <span>Entrée pour envoyer, Maj+Entrée pour un saut de ligne</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
