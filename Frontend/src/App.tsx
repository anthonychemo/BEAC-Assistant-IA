/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

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
  
  // App metrics
  const [metrics, setMetrics] = useState<DashboardMetrics>({
    documentsIndexed: INITIAL_DOCUMENTS.length,
    ragChunks: 435012,
    feedbackSatisfaction: "94.8%",
    avgResponseTime: "1.2s",
    systemStatus: "Actif"
  });

  // Admin and Login States
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState<boolean>(false);
  const [showAdminLogin, setShowAdminLogin] = useState<boolean>(false);

  // Chat Conversational States
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-1",
      role: "assistant",
      content: "Bonjour et bienvenue sur l'assistant sémantique de la **Banque des États de l'Afrique Centrale**. Je suis instruit sur les rapports annuels, les communiqués officiels et la réglementation bancaire COBAC.\n\nPosez-moi votre question pour démarrer l'analyse de vos données.",
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
    }
  ]);
  const [isThinking, setIsThinking] = useState<boolean>(false);
  const [suggestedPrompt, setSuggestedPrompt] = useState<string>("");
  const [preSelectedDocType, setPreSelectedDocType] = useState<string | null>(null);

  // Pipeline execution state
  const [isPipelineActive, setIsPipelineActive] = useState<boolean>(true);

  // Log injection effect on boot
  useEffect(() => {
    // Sync metrics counts to document list size dynamically so everything is cohesive!
    setMetrics((prev: DashboardMetrics) => ({
      ...prev,
      documentsIndexed: documents.length,
      ragChunks: documents.length * 3421
    }));
  }, [documents]);

  const handleSendMessage = async (text: string) => {
    // 1. Add user message
    const userMsg: ChatMessage = {
      id: `user-msg-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
    };
    
    setChatMessages((prev: ChatMessage[]) => [...prev, userMsg]);
    setIsThinking(true);

    try {
      // 2. Call local full-stack server API
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: text,
          history: chatMessages.slice(-8) // pass last 8 messages for context
        })
      });

      if (!res.ok) {
        throw new Error("Erreur de communication avec l'assistant.");
      }

      const data = await res.json();
      
      // 3. Add AI message response
      const assistantMsg: ChatMessage = {
        id: `assistant-msg-${Date.now()}`,
        role: "assistant",
        content: data.response,
        timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
      };

      setChatMessages((prev: ChatMessage[]) => [...prev, assistantMsg]);

      // Write a log in background
      handleAddLog(
        `Interrogation IA réussie pour la requête : "${text.substring(0, 30)}..."`,
        "success"
      );

    } catch (err: any) {
      console.error(err);
      
      const assistantMsg: ChatMessage = {
        id: `assistant-msg-${Date.now()}`,
        role: "assistant",
        content: "Une erreur de communication est survenue. Veuillez vérifier votre clé d'API.",
        timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
      
      handleAddLog(`Échec de traitement IA : ${err.message}`, "error");
    } finally {
      setIsThinking(false);
    }
  };

  const handleUploadDocument = (newDoc: Document) => {
    setDocuments((prev: Document[]) => [newDoc, ...prev]);
    
    // Inject success log
    handleAddLog(
      `Le document "${newDoc.title}" a été traité avec succès et indexé en chunks.`,
      "success",
      `${newDoc.title.substring(0, 24)}.${newDoc.fileType.toLowerCase()}`
    );
  };

  const handleAskDocInChat = (text: string) => {
    setSuggestedPrompt(text);
    setTab("chat");
  };

  const handleSelectSuggestion = (text: string) => {
    setSuggestedPrompt(text);
    setTab("chat");
  };

  const handleAddLog = (message: string, type: "success" | "warning" | "error", targetDoc?: string) => {
    const newLog: Log = {
      id: `log-custom-${Date.now()}`,
      timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      type,
      message,
      targetDoc
    };
    setLogs((prev: Log[]) => [newLog, ...prev]);
  };

  const handleClearLogs = () => {
    setLogs([]);
  };

  const handleTogglePipeline = () => {
    const nextState = !isPipelineActive;
    setIsPipelineActive(nextState);
    if (nextState) {
      handleAddLog("Le pipeline automatique RAG d'indexation hebdomadaire a été redémarré.", "success");
    } else {
      handleAddLog("Le pipeline RAG a été suspendu manuellement par l'administrateur.", "warning");
    }
  };

  const handleClearHistory = () => {
    setChatMessages([
      {
        id: "welcome-1",
        role: "assistant",
        content: "Historique réinitialisé. Comment puis-je vous éclairer sur l'économie de la zone CEMAC aujourd'hui ?",
        timestamp: new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
      }
    ]);
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#f8f9fa] pt-16">
      
      {/* Universal Institutional Top Bar */}
      <Header
        currentTab={currentTab}
        setTab={setTab}
        onOpenAdminLogin={() => setShowAdminLogin(true)}
        isAdminLoggedIn={isAdminLoggedIn}
        onLogoutAdmin={() => {
          setIsAdminLoggedIn(false);
          handleAddLog("Superviseur DSI déconnecté de la console sécurisée.", "warning");
        }}
      />

      {/* Main routed screen area */}
      <main className="flex-1 flex flex-col mt-0 select-text">
        {currentTab === "accueil" && (
          <LandingPage
            onSelectSuggestion={handleSelectSuggestion}
            setTab={setTab}
            setPreSelectedDocType={setPreSelectedDocType}
          />
        )}
        
        {currentTab === "chat" && (
          <IAAssistant
            messages={chatMessages}
            onSendMessage={handleSendMessage}
            isThinking={isThinking}
            onClearHistory={handleClearHistory}
            suggestedPrompt={suggestedPrompt}
            setSuggestedPrompt={setSuggestedPrompt}
          />
        )}

        {currentTab === "bibliotheque" && (
          <DocumentLibrary
            documents={documents}
            onUploadDocument={handleUploadDocument}
            onAskDocInChat={handleAskDocInChat}
            preSelectedType={preSelectedDocType}
            setPreSelectedType={setPreSelectedDocType}
          />
        )}

        {currentTab === "dashboard" && (
          <AdminDashboard
            metrics={metrics}
            logs={logs}
            onAddLog={handleAddLog}
            onClearLogs={handleClearLogs}
            isPipelineActive={isPipelineActive}
            onTogglePipeline={handleTogglePipeline}
          />
        )}
      </main>

      {/* Shared Footer block */}
      <Footer />

      {/* Login Portal Trigger overlay modal */}
      {showAdminLogin && (
        <LoginPortal
          onClose={() => setShowAdminLogin(false)}
          onLoginSuccess={() => {
            setIsAdminLoggedIn(true);
            setTab("dashboard");
            handleAddLog("Superviseur DSI authentifié avec succès pour la maintenance.", "success");
          }}
        />
      )}

    </div>
  );
}

