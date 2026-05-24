"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import {
    DocumentInfo,
    ChatMessage as ChatMessageType,
    ChatSummary,
    ChatInfo,
} from "@/lib/types";
import Sidebar from "@/components/Sidebar";
import UploadModal from "@/components/UploadModal";
import ChatMessage, { LoadingMessage } from "@/components/ChatMessage";

const SUGGESTIONS = [
    "What was the total revenue for the latest quarter?",
    "Break down operating expenses by category",
    "What are the key risk factors mentioned?",
    "Compare net income year-over-year",
    "What is the current cash and equivalents position?",
    "Summarize the management discussion and analysis",
];

export default function ChatPage() {
    const params = useParams();
    const router = useRouter();
    const chatId = params.chatId as string;

    const [documents, setDocuments] = useState<DocumentInfo[]>([]);
    const [allChats, setAllChats] = useState<ChatSummary[]>([]);
    const [currentChat, setCurrentChat] = useState<ChatInfo | null>(null);
    const [currentDoc, setCurrentDoc] = useState<DocumentInfo | null>(null);
    const [messages, setMessages] = useState<ChatMessageType[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [showUpload, setShowUpload] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    const fetchDocuments = useCallback(async () => {
        try {
            const docs = await api.listDocuments();
            setDocuments(docs);
        } catch {
            console.error("Failed to fetch documents");
        }
    }, []);

    const fetchAllChats = useCallback(async () => {
        try {
            const chats = await api.listAllChats();
            setAllChats(chats);
        } catch {
            console.error("Failed to fetch chats");
        }
    }, []);

    const fetchCurrentChat = useCallback(async () => {
        try {
            const chat = await api.getChat(chatId);
            setCurrentChat(chat);

            // Convert stored messages to ChatMessageType
            const restored: ChatMessageType[] = chat.messages.map((m) => ({
                id: m.id,
                role: m.role as "user" | "assistant",
                content: m.content,
                sources: m.sources.length > 0 ? m.sources : undefined,
                chartData: m.chart_data || undefined,
                timestamp: new Date(m.timestamp),
            }));
            setMessages(restored);

            // Load the associated document
            const doc = await api.getDocument(chat.document_id);
            setCurrentDoc(doc);
        } catch {
            router.push("/");
        }
    }, [chatId, router]);

    useEffect(() => {
        fetchDocuments();
        fetchAllChats();
        fetchCurrentChat();
        const interval = setInterval(() => {
            fetchDocuments();
            fetchAllChats();
        }, 10000);
        return () => clearInterval(interval);
    }, [fetchDocuments, fetchAllChats, fetchCurrentChat]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const handleSend = async (question?: string) => {
        const q = (question || input).trim();
        if (!q || loading || !currentChat) return;

        const userMsg: ChatMessageType = {
            id: crypto.randomUUID(),
            role: "user",
            content: q,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);

        try {
            const response = await api.sendChatMessage(currentChat.id, q);

            const assistantMsg: ChatMessageType = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: response.answer,
                sources: response.sources,
                chartData: response.chart_data || undefined,
                timestamp: new Date(),
            };

            setMessages((prev) => [...prev, assistantMsg]);

            // Refetch chat to get the AI-generated title from backend
            if (currentChat.title === "New Chat" || messages.length === 0) {
                try {
                    const updatedChat = await api.getChat(currentChat.id);
                    setCurrentChat(updatedChat);
                    setAllChats((prev) =>
                        prev.map((c) =>
                            c.id === currentChat.id
                                ? {
                                    ...c,
                                    title: updatedChat.title,
                                    message_count: updatedChat.messages.length,
                                    updated_at: updatedChat.updated_at,
                                }
                                : c
                        )
                    );
                } catch {
                    // ignore refetch failure
                }
            } else {
                setAllChats((prev) =>
                    prev.map((c) =>
                        c.id === currentChat.id
                            ? {
                                ...c,
                                message_count: c.message_count + 2,
                                updated_at: new Date().toISOString(),
                            }
                            : c
                    )
                );
            }
        } catch (err) {
            const errorMsg: ChatMessageType = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: `Error: ${err instanceof Error ? err.message : "Something went wrong. Please try again."}`,
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setLoading(false);
            inputRef.current?.focus();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleDeleteDoc = async (id: string) => {
        try {
            await api.deleteDocument(id);
            setDocuments((prev) => prev.filter((d) => d.id !== id));
            setAllChats((prev) => prev.filter((c) => c.document_id !== id));
            if (currentDoc?.id === id) router.push("/");
        } catch {
            console.error("Failed to delete");
        }
    };

    const handleDeleteChat = async (id: string) => {
        try {
            await api.deleteChat(id);
            setAllChats((prev) => prev.filter((c) => c.id !== id));
            if (id === chatId) router.push("/");
        } catch {
            console.error("Failed to delete chat");
        }
    };

    const handleChatCreated = (chat: ChatSummary) => {
        setAllChats((prev) => [chat, ...prev]);
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
                activeChatId={chatId}
                isOpen={sidebarOpen}
                onClose={() => setSidebarOpen(false)}
                onUploadClick={() => setShowUpload(true)}
                onDeleteDoc={handleDeleteDoc}
                onDeleteChat={handleDeleteChat}
                onChatCreated={handleChatCreated}
                onChatRenamed={handleChatRenamed}
            />

            <div className="main-content">
                <div className="chat-page">
                    {/* Header */}
                    <div className="chat-header">
                        <button className="hamburger" onClick={() => setSidebarOpen(true)} aria-label="Open menu">
                            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><line x1="3" y1="5" x2="17" y2="5"/><line x1="3" y1="10" x2="17" y2="10"/><line x1="3" y1="15" x2="17" y2="15"/></svg>
                        </button>
                        <button
                            className="chat-header__back"
                            onClick={() => router.push("/")}
                        >
                            ← Back
                        </button>
                        <div>
                            <div className="chat-header__title">
                                {currentDoc?.document_title || "Loading..."}
                            </div>
                            <div className="chat-header__company">
                                {currentDoc?.company_name}
                                {currentDoc?.document_date && ` · ${currentDoc.document_date}`}
                            </div>
                        </div>
                    </div>

                    {/* Messages */}
                    <div className="chat-messages">
                        {messages.length === 0 ? (
                            <div className="chat-welcome">
                                <h2 className="chat-welcome__title">
                                    Ask about {currentDoc?.company_name || "this document"}
                                </h2>
                                <p className="chat-welcome__hint">
                                    Ask any question about the financial filing. The AI will provide
                                    cited answers with data from the document.
                                </p>
                                <div className="chat-welcome__suggestions">
                                    {SUGGESTIONS.map((s, i) => (
                                        <button
                                            key={i}
                                            className="chat-welcome__suggestion"
                                            onClick={() => handleSend(s)}
                                        >
                                            {s}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ) : (
                            <>
                                {messages.map((msg) => (
                                    <ChatMessage key={msg.id} message={msg} />
                                ))}
                                {loading && <LoadingMessage />}
                            </>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="chat-input-area">
                        <form
                            className="chat-input-form"
                            onSubmit={(e) => {
                                e.preventDefault();
                                handleSend();
                            }}
                        >
                            <textarea
                                ref={inputRef}
                                className="chat-input"
                                placeholder={`Ask about ${currentDoc?.company_name || "this document"}...`}
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                rows={1}
                                disabled={loading}
                            />
                            <button
                                className="chat-send-btn"
                                type="submit"
                                disabled={!input.trim() || loading}
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
                            </button>
                        </form>
                    </div>
                </div>
            </div>

            {showUpload && (
                <UploadModal
                    onClose={() => setShowUpload(false)}
                    onUploaded={(doc) => {
                        setDocuments((prev) => [doc, ...prev]);
                    }}
                />
            )}
        </div>
    );
}

