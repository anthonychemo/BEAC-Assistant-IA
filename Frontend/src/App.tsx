import { useState, useEffect } from "react";
import Header from "./components/Header";
import Footer from "./components/Footer";
import LandingPage from "./components/LandingPage";
import IAAssistant from "./components/IAAssistant";
import DocumentLibrary from "./components/DocumentLibrary";
import AdminDashboard from "./components/AdminDashboard";
import LoginPortal from "./components/LoginPortal";
import { INITIAL_DOCUMENTS, INITIAL_LOGS } from "./data";
import { Document, ChatMessage, Log, DashboardMetrics } from "./types";

export default function App() {
  const [currentTab, setTab] = useState<string>("accueil");
  const [documents, setDocuments] = useState<Document[]>(INITIAL_DOCUMENTS);
  const [logs, setLogs] = useState<Log[]>(INITIAL_LOGS);
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    documentsIndexed: INITIAL_DOCUMENTS.length,
    ragChunks: 435012,
    feedbackSatisfaction: "94.8%",
    avgResponseTime: "1.2s",
    systemStatus: "Actif",
  });
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(false);
  const [showAdminLogin, setShowAdminLogin] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([{
    id: "welcome-1",
    role: "assistant",
    content: "Bonjour et bienvenue sur l'assistant de la BEAC. Posez-moi votre question.",
    timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
  }]);
  const [isThinking, setIsThinking] = useState(false);
  const [suggestedPrompt, setSuggestedPrompt] = useState("");
  const [preSelectedDocType, setPreSelectedDocType] = useState<string | null>(null);
  const [isPipelineActive, setIsPipelineActive] = useState(true);

  useEffect(() => {
    setMetrics((prev) => ({
      ...prev,
      documentsIndexed: documents.length,
      ragChunks: documents.length * 3421,
    }));
  }, [documents]);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!data) return;
        setMetrics((prev) => ({
          ...prev,
          documentsIndexed: data.documents ?? prev.documentsIndexed,
          ragChunks: data.chunks ?? prev.ragChunks,
          systemStatus: data.status === "ok" ? "Actif" : "Degrade",
        }));
      })
      .catch(() => {});
  }, []);

  const handleAddLog = (message: string, type: "success" | "warning" | "error", targetDoc?: string) => {
    setLogs((prev) => [{
      id: "log-" + Date.now(),
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      type,
      message,
      targetDoc,
    }, ...prev]);
  };

  const handleSendMessage = async (text: string) => {
    setChatMessages((prev) => [...prev, {
      id: "user-" + Date.now(),
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
    }]);
    setIsThinking(true);

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
        body: JSON.stringify({ question: text }),
      });

      if (!res.ok) throw new Error("Erreur backend");
      if (!res.body) throw new Error("Streaming indisponible");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let firstChunk = true;
      setIsThinking(false);

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
                  m.id === aId ? { ...m, sources: meta.sources ?? [], query_type: meta.query_type } : m
                ));
                const rest = chunk.slice(nl + 1);
                if (rest) setChatMessages((prev) => prev.map((m) =>
                  m.id === aId ? { ...m, content: m.content + rest } : m
                ));
                continue;
              }
            } catch { /* token normal */ }
          }
        }

        setChatMessages((prev) => prev.map((m) =>
          m.id === aId ? { ...m, content: m.content + chunk } : m
        ));
      }
      handleAddLog("Reponse IA : " + text.substring(0, 30) + "...", "success");
    } catch (err: any) {
      setChatMessages((prev) => prev.map((m) =>
        m.id === aId ? { ...m, content: "Erreur de communication. Veuillez reessayer." } : m
      ));
      handleAddLog("Echec IA : " + err.message, "error");
    } finally {
      setIsThinking(false);
    }
  };

  const handleUploadDocument = (newDoc: Document) => {
    setDocuments((prev) => [newDoc, ...prev]);
    handleAddLog("Document indexe : " + newDoc.title.substring(0, 30), "success");
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8f9fa] pt-16">
      <Header
        currentTab={currentTab}
        setTab={setTab}
        onOpenAdminLogin={() => setShowAdminLogin(true)}
        isAdminLoggedIn={isAdminLoggedIn}
        onLogoutAdmin={() => {
          setIsAdminLoggedIn(false);
          handleAddLog("Admin deconnecte", "warning");
        }}
      />

      <main className="flex-1 flex flex-col mt-0 select-text">
        <div className={currentTab === "accueil" ? "" : "hidden"}>
          <LandingPage
            onSelectSuggestion={(t) => { setSuggestedPrompt(t); setTab("chat"); }}
            setTab={setTab}
            setPreSelectedDocType={setPreSelectedDocType}
          />
        </div>

        <div className={currentTab === "chat" ? "" : "hidden"}>
          <IAAssistant
            messages={chatMessages}
            onSendMessage={handleSendMessage}
            isThinking={isThinking}
            onClearHistory={() => setChatMessages([{
              id: "welcome-1",
              role: "assistant",
              content: "Historique reinitialise.",
              timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
            }])}
            suggestedPrompt={suggestedPrompt}
            setSuggestedPrompt={setSuggestedPrompt}
          />
        </div>

        <div className={currentTab === "bibliotheque" ? "" : "hidden"}>
          <DocumentLibrary
            documents={documents}
            onUploadDocument={handleUploadDocument}
            onAskDocInChat={(t) => { setSuggestedPrompt(t); setTab("chat"); }}
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
