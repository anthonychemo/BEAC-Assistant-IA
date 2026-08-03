import { useState, useEffect, useRef } from "react";
import { AnimatePresence } from "motion/react";
import Header from "./components/Header";
import Footer from "./components/Footer";
import LandingPage from "./components/LandingPage";
import IAAssistant from "./components/IAAssistant";
import DocumentLibrary from "./components/DocumentLibrary";
import AdminDashboard from "./components/AdminDashboard";
import LoginPortal from "./components/LoginPortal";
import SplashScreen from "./components/SplashScreen";
import { INITIAL_DOCUMENTS, INITIAL_LOGS } from "./data";
import { Document, ChatMessage, Log, DashboardMetrics, ModelChoice } from "./types";

const SPLASH_SESSION_KEY = "beac_splash_shown";
const CHAT_HISTORY_KEY = "beac_chat_history";

function makeWelcomeMessage(text: string): ChatMessage {
  return {
    id: "welcome-1",
    role: "assistant",
    content: text,
    timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
  };
}

function loadStoredChatHistory(): ChatMessage[] | null {
  try {
    // sessionStorage (et non localStorage) : l'historique survit a un F5 mais
    // est efface a la fermeture de l'onglet/navigateur, comme demande.
    const raw = sessionStorage.getItem(CHAT_HISTORY_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : null;
  } catch {
    return null;
  }
}

// Navigation basee sur l'API History du navigateur (pas de react-router) : les
// sections restent toutes montees en permanence (voir plus bas), seule l'URL
// et l'entree d'historique associee a l'onglet actif changent.
const TAB_PATHS: Record<string, string> = {
  accueil: "/",
  chat: "/chat",
  bibliotheque: "/bibliotheque",
  dashboard: "/dashboard",
};

function tabToPath(tab: string): string {
  return TAB_PATHS[tab] ?? "/";
}

function pathToTab(pathname: string): string {
  const normalized = pathname.replace(/\/+$/, "") || "/";
  const found = Object.entries(TAB_PATHS).find(([, path]) => path === normalized);
  return found ? found[0] : "accueil";
}

function resolveInitialTab(): string {
  const tab = pathToTab(window.location.pathname);
  // isAdminLoggedIn demarre toujours a false au chargement (pas de session
  // persistee) : un chargement direct sur /dashboard ne doit jamais afficher
  // le panneau admin.
  return tab === "dashboard" ? "accueil" : tab;
}

export default function App() {
  const [currentTab, setCurrentTab] = useState<string>(resolveInitialTab);

  const setTab = (tab: string) => {
    setCurrentTab(tab);
    if (tabToPath(tab) !== window.location.pathname) {
      window.history.pushState({ tab }, "", tabToPath(tab));
    }
  };
  const [showSplash, setShowSplash] = useState(() => {
    const alreadyShown = sessionStorage.getItem(SPLASH_SESSION_KEY);
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    return !alreadyShown && !prefersReducedMotion;
  });
  const [documents, setDocuments] = useState<Document[]>(INITIAL_DOCUMENTS);
  const [logs, setLogs] = useState<Log[]>(INITIAL_LOGS);
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    documentsIndexed: INITIAL_DOCUMENTS.length,
    ragChunks: 435012,
    feedbackSatisfaction: "—",
    avgResponseTime: "1.2s",
    systemStatus: "Actif",
  });
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [showAdminLogin, setShowAdminLogin] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(
    () => loadStoredChatHistory() ?? [makeWelcomeMessage("Bonjour et bienvenue sur l'assistant de la BEAC. Posez-moi votre question.")]
  );
  const [isThinking, setIsThinking] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [suggestedPrompt, setSuggestedPrompt] = useState("");
  const [suggestedDocumentId, setSuggestedDocumentId] = useState<string | undefined>(undefined);
  const [preSelectedDocType, setPreSelectedDocType] = useState<string | null>(null);
  const [isPipelineActive, setIsPipelineActive] = useState(true);
  const [availableModels, setAvailableModels] = useState<ModelChoice[]>([
    { key: "primary", label: "Modèle principal" },
  ]);
  const [selectedModel, setSelectedModel] = useState<ModelChoice>({
    key: "primary",
    label: "Modèle principal",
  });

  useEffect(() => {
    if (!showSplash) return;
    sessionStorage.setItem(SPLASH_SESSION_KEY, "1");
    const t = setTimeout(() => setShowSplash(false), 1100);
    return () => clearTimeout(t);
  }, [showSplash]);

  // Rattache l'onglet resolu a l'entree d'historique courante (et corrige
  // l'URL si on a atterri directement sur /dashboard sans etre connecte).
  useEffect(() => {
    const initial = resolveInitialTab();
    window.history.replaceState({ tab: initial }, "", tabToPath(initial));
  }, []);

  // Precedent/Suivant du navigateur : restaure l'onglet associe a l'entree
  // d'historique ciblee, sans recreer d'entree (setCurrentTab brut, pas setTab).
  useEffect(() => {
    const onPopState = (e: PopStateEvent) => {
      const tab = (e.state?.tab as string | undefined) ?? pathToTab(window.location.pathname);
      setCurrentTab(tab);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const fetchHealthMetrics = () => {
    fetch("/api/health")
      .then((r) => {
        if (!r.ok) throw new Error("Reponse backend non OK");
        return r.json();
      })
      .then((data) => {
        setMetrics((prev) => ({
          ...prev,
          documentsIndexed: data.documents ?? prev.documentsIndexed,
          ragChunks: data.chunks ?? prev.ragChunks,
          systemStatus: data.status === "ok" ? "Actif" : "Degrade",
          feedbackSatisfaction: data.feedback_satisfaction != null ? `${data.feedback_satisfaction}%` : "—",
        }));
      })
      .catch(() => {
        setMetrics((prev) => ({ ...prev, systemStatus: "Hors ligne" }));
      });
  };

  useEffect(() => {
    fetchHealthMetrics();
  }, []);

  // Persiste l'historique de chat pour la session en cours : un F5 ne doit pas
  // effacer la conversation, mais fermer l'onglet/navigateur si.
  useEffect(() => {
    try {
      sessionStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(chatMessages.slice(-200)));
    } catch {
      // Stockage indisponible (navigation privee stricte, quota depasse...) :
      // l'app reste fonctionnelle, seule la persistance est perdue.
    }
  }, [chatMessages]);

  // Modeles LLM reellement disponibles cote backend (evite un selecteur cosmetique)
  useEffect(() => {
    fetch("/api/metadata")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const models: ModelChoice[] = data?.models ?? [];
        if (models.length > 0) {
          setAvailableModels(models);
          setSelectedModel(models[0]);
        }
      })
      .catch(() => {});
  }, []);

  // Message affiché à l'utilisateur en cas d'échec réseau/backend — jamais de
  // détails techniques. Si un texte technique venait malgré tout à fuiter du
  // backend (regression), on le remplace par ce même message (filet de sécurité).
  const FRIENDLY_ERROR = "Le service est momentanément surchargé en raison d'une forte affluence. Merci de réessayer votre question dans quelques instants.";
  // Miroir exact de _FRIENDLY_ERROR_MIDSTREAM (beac-rag-backend/src/api/app.py) :
  // envoyee quand le LLM echoue apres l'envoi des metadonnees (sources/query_type)
  // mais avant ou pendant le streaming des tokens.
  const FRIENDLY_ERROR_MIDSTREAM = "\n\nDésolé, la réponse a été interrompue en raison d'une forte affluence sur le service. Merci de réessayer votre question.";
  const LEAKED_ERROR_PATTERN = /\[Erreur[^\]]*\]/i;

  const handleAddLog = (message: string, type: "success" | "warning" | "error", targetDoc?: string) => {
    setLogs((prev) => [{
      id: "log-" + Date.now(),
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      type,
      message,
      targetDoc,
    }, ...prev]);
  };

  const handleSendMessage = async (text: string, documentId?: string) => {
    setChatMessages((prev) => [...prev, {
      id: "user-" + Date.now(),
      role: "user",
      content: text,
      documentId,
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
    }]);
    setIsThinking(true);
    setIsStreaming(true);
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const aId = "assistant-" + Date.now();
    setChatMessages((prev) => [...prev, {
      id: aId,
      role: "assistant",
      content: "",
      sources: [],
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
    }]);

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: text,
          model_key: selectedModel.key,
          document_id: documentId ? Number(documentId) : undefined,
        }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error("Erreur backend");
      if (!res.body) throw new Error("Streaming indisponible");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let firstChunk = true;
      // "isThinking" reste actif tant qu'aucun contenu reel n'est arrive : les
      // metadonnees (sources/type de recherche) arrivent des la fin de la
      // recherche, bien avant le premier token du LLM, qui peut prendre
      // plusieurs secondes voire plus. Le couper trop tot laisse un vide sans
      // aucun indicateur pendant cette attente.

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });

        if (firstChunk) {
          firstChunk = false;
          const nl = chunk.indexOf("\n");
          if (nl !== -1) {
            try {
              const meta = JSON.parse(chunk.slice(0, nl));
              if (meta.type === "meta") {
                setChatMessages((prev) => prev.map((m) =>
                  m.id === aId ? { ...m, sources: meta.sources ?? [], query_type: meta.query_type, isError: !!meta.error } : m
                ));
                const rest = chunk.slice(nl + 1);
                if (rest) {
                  setIsThinking(false);
                  setChatMessages((prev) => prev.map((m) =>
                    m.id === aId ? { ...m, content: m.content + rest } : m
                  ));
                }
                continue;
              }
            } catch { /* token normal */ }
          }
        }

        setIsThinking(false);

        // Filet de securite : si un message technique venait a fuiter malgre
        // tout (regression backend), on le remplace par un message clair.
        const safeChunk = LEAKED_ERROR_PATTERN.test(chunk) ? FRIENDLY_ERROR : chunk;
        const leaked = safeChunk !== chunk;
        // Le backend peut aussi envoyer directement le texte d'erreur convivial
        // (query_stream, app.py) comme simple morceau de contenu — sans marqueur
        // JSON d'erreur — quand le LLM echoue apres l'envoi des metadonnees mais
        // avant le premier token. Sans cette detection, isError reste a false et
        // les sources/badges de la recherche restent affiches sous ce message
        // d'erreur (c'est le bug corrige ici).
        const isKnownErrorText = leaked || chunk.includes(FRIENDLY_ERROR) || chunk.includes(FRIENDLY_ERROR_MIDSTREAM);
        setChatMessages((prev) => prev.map((m) =>
          m.id === aId
            ? {
                ...m,
                content: m.content + safeChunk,
                isError: m.isError || isKnownErrorText,
                // Les sources/le type de requete viennent de la recherche qui a
                // precede l'echec du LLM : on les efface des qu'une erreur est
                // detectee pour ne pas laisser croire a une reponse valide.
                ...(isKnownErrorText ? { sources: [], query_type: undefined } : {}),
              }
            : m
        ));
      }
      handleAddLog("Reponse IA : " + text.substring(0, 30) + "...", "success");
    } catch (err: any) {
      if (err?.name === "AbortError") {
        // Arret volontaire par l'utilisateur : on garde le contenu deja recu
        // tel quel, sans le remplacer par un message d'erreur.
        setChatMessages((prev) => prev.map((m) =>
          m.id === aId ? { ...m, content: m.content + "\n\n*[Génération interrompue]*" } : m
        ));
        handleAddLog("Reponse IA interrompue par l'utilisateur", "warning");
      } else {
        setChatMessages((prev) => prev.map((m) =>
          m.id === aId ? { ...m, content: FRIENDLY_ERROR, isError: true, sources: [], query_type: undefined } : m
        ));
        handleAddLog("Echec IA : " + err.message, "error");
      }
    } finally {
      setIsThinking(false);
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleStopGeneration = () => {
    abortControllerRef.current?.abort();
  };

  const handleFeedback = (messageId: string, isPositive: boolean) => {
    const idx = chatMessages.findIndex((m) => m.id === messageId);
    if (idx === -1) return;
    const assistantMsg = chatMessages[idx];
    const questionMsg = [...chatMessages.slice(0, idx)].reverse().find((m) => m.role === "user");
    if (!questionMsg) return;

    setChatMessages((prev) => prev.map((m) =>
      m.id === messageId ? { ...m, feedback: isPositive ? "positive" : "negative" } : m
    ));

    fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: questionMsg.content,
        is_positive: isPositive,
        query_type: assistantMsg.query_type ?? null,
        model_key: selectedModel.key,
      }),
    })
      .then(() => fetchHealthMetrics())
      .catch(() => {
        // Retour non critique : l'etat optimiste local est conserve meme si
        // l'envoi echoue (pas d'annulation visible pour l'utilisateur).
      });
  };

  const handleUploadDocument = (newDoc: Document) => {
    setDocuments((prev) => [newDoc, ...prev]);
    // Incremente le compteur reel (issu de /api/health) au lieu de le
    // recalculer depuis la longueur du tableau local `documents` (qui demarre
    // sur des donnees d'exemple et ecraserait sinon le vrai total backend).
    setMetrics((prev) => ({ ...prev, documentsIndexed: prev.documentsIndexed + 1 }));
    handleAddLog("Document indexe : " + newDoc.title.substring(0, 30), "success");
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8f9fa] pt-16">
      <AnimatePresence>
        {showSplash && <SplashScreen />}
      </AnimatePresence>

      <Header
        currentTab={currentTab}
        setTab={setTab}
        onOpenAdminLogin={() => setShowAdminLogin(true)}
        isAdminLoggedIn={isAdminLoggedIn}
        onLogoutAdmin={() => {
          setIsAdminLoggedIn(false);
          setTab("accueil");
          handleAddLog("Admin deconnecte", "warning");
        }}
      />

      <main className="flex-1 flex flex-col mt-0 select-text">
        <div className={currentTab === "accueil" ? "" : "hidden"}>
          <LandingPage
            onSelectSuggestion={(t) => { setSuggestedPrompt(t); setSuggestedDocumentId(undefined); setTab("chat"); }}
            setTab={setTab}
            setPreSelectedDocType={setPreSelectedDocType}
            metrics={metrics}
          />
        </div>

        <div className={currentTab === "chat" ? "" : "hidden"}>
          <IAAssistant
            messages={chatMessages}
            onSendMessage={handleSendMessage}
            isThinking={isThinking}
            isStreaming={isStreaming}
            onStopGeneration={handleStopGeneration}
            onFeedback={handleFeedback}
            onClearHistory={() => setChatMessages([makeWelcomeMessage("Historique reinitialise.")])}
            suggestedPrompt={suggestedPrompt}
            setSuggestedPrompt={setSuggestedPrompt}
            suggestedDocumentId={suggestedDocumentId}
            setSuggestedDocumentId={setSuggestedDocumentId}
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
            availableModels={availableModels}
          />
        </div>

        <div className={currentTab === "bibliotheque" ? "" : "hidden"}>
          <DocumentLibrary
            onUploadDocument={handleUploadDocument}
            onAskDocInChat={(t, docId) => { setSuggestedPrompt(t); setSuggestedDocumentId(docId); setTab("chat"); }}
            preSelectedType={preSelectedDocType}
            setPreSelectedType={setPreSelectedDocType}
          />
        </div>

        <div className={currentTab === "dashboard" ? "" : "hidden"}>
          <AdminDashboard
            metrics={metrics}
            logs={logs}
            onAddLog={handleAddLog}
            onClearLogs={() => setLogs([])}
            isPipelineActive={isPipelineActive}
            onTogglePipeline={() => {
              const next = !isPipelineActive;
              setIsPipelineActive(next);
              handleAddLog(next ? "Pipeline redemarre" : "Pipeline suspendu", next ? "success" : "warning");
            }}
          />
        </div>
      </main>

      <Footer />

      {showAdminLogin && (
        <LoginPortal
          onClose={() => setShowAdminLogin(false)}
          onLoginSuccess={() => {
            setIsAdminLoggedIn(true);
            setTab("dashboard");
            handleAddLog("Admin connecte", "success");
          }}
        />
      )}
    </div>
  );
}
