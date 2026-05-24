"use client";

import React, { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { DocumentInfo, ChatSummary } from "@/lib/types";
import Sidebar from "@/components/Sidebar";
import UploadModal from "@/components/UploadModal";
import { useRouter } from "next/navigation";

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    setDark(document.documentElement.getAttribute("data-theme") === "dark");
  }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
    localStorage.setItem("theme", next ? "dark" : "light");
  };
  return (
    <button className="theme-toggle" onClick={toggle} aria-label="Toggle theme">
      {dark ? (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="5"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
      ) : (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      )}
    </button>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [allChats, setAllChats] = useState<ChatSummary[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [docs, chats] = await Promise.all([
        api.listDocuments(),
        api.listAllChats(),
      ]);
      setDocuments(docs);
      setAllChats(chats);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

  const handleUploaded = (doc: DocumentInfo) =>
    setDocuments((prev) => [doc, ...prev]);
  const handleDelete = async (docId: string) => {
    try {
      await api.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      setAllChats((prev) => prev.filter((c) => c.document_id !== docId));
    } catch {
      /* ignore */
    }
  };
  const handleDeleteChat = async (chatId: string) => {
    try {
      await api.deleteChat(chatId);
      setAllChats((prev) => prev.filter((c) => c.id !== chatId));
    } catch {
      /* ignore */
    }
  };
  const handleChatCreated = (chat: ChatSummary) => {
    setAllChats((prev) => [chat, ...prev]);
    router.push(`/chat/${chat.id}`);
  };
  const handleChatRenamed = (chatId: string, newTitle: string) => {
    setAllChats((prev) =>
      prev.map((c) => (c.id === chatId ? { ...c, title: newTitle } : c))
    );
  };

  return (
    <div className="app-layout">
      <Sidebar
        documents={documents}
        chats={allChats}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onUploadClick={() => setShowUpload(true)}
        onDeleteDoc={handleDelete}
        onDeleteChat={handleDeleteChat}
        onChatCreated={handleChatCreated}
        onChatRenamed={handleChatRenamed}
      />
      <div className="main-content">
        <header className="app-header">
          <div className="app-header__left">
            <button className="hamburger" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><line x1="3" y1="5" x2="17" y2="5"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="15" x2="17" y2="15"/></svg>
            </button>
            <div className="app-header__logo">
              <svg width="32" height="32" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="4" y="28" width="10" height="16" rx="2" fill="#0D9488"/>
                <rect x="19" y="18" width="10" height="26" rx="2" fill="#0D9488" opacity="0.7"/>
                <rect x="34" y="8" width="10" height="36" rx="2" fill="#0D9488" opacity="0.4"/>
                <path d="M6 30 L21 20 L36 10" stroke="#0D9488" strokeWidth="1.5" strokeLinecap="round" fill="none"/>
              </svg>
              <span className="wordmark"><span className="wordmark__fin">Fin</span><span className="wordmark__aura">aura</span></span>
            </div>
          </div>
          <ThemeToggle />
        </header>
        <div className="landing">
          <h1 className="landing__title">Analyze any financial document</h1>
          <p className="landing__subtitle">
            Upload SEC filings, annual reports, or financial statements.
            Ask questions and get cited, data-driven answers powered by <span className="wordmark" style={{ fontSize: 'inherit', fontWeight: 'inherit' }}><span className="wordmark__fin">Fin</span><span className="wordmark__aura">aura</span></span>.
          </p>
          <button
            className="landing__cta"
            onClick={() => setShowUpload(true)}
          >
            Upload a document
          </button>
        </div>
      </div>
      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={handleUploaded}
        />
      )}
    </div>
  );
}
