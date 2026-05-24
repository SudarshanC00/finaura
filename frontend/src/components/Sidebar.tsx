"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { DocumentInfo, ChatSummary } from "@/lib/types";
import { api } from "@/lib/api";

interface SidebarProps {
    documents: DocumentInfo[];
    chats: ChatSummary[];
    activeChatId?: string;
    isOpen: boolean;
    onClose: () => void;
    onUploadClick: () => void;
    onDeleteDoc: (docId: string) => void;
    onDeleteChat: (chatId: string) => void;
    onChatCreated: (chat: ChatSummary) => void;
    onChatRenamed: (chatId: string, newTitle: string) => void;
}

function InlineRenameInput({
    chatId, currentTitle, onSave, onCancel,
}: {
    chatId: string; currentTitle: string;
    onSave: (chatId: string, title: string) => void; onCancel: () => void;
}) {
    const [value, setValue] = useState(currentTitle);
    const inputRef = useRef<HTMLInputElement>(null);
    useEffect(() => { inputRef.current?.focus(); inputRef.current?.select(); }, []);
    const handleSave = () => {
        const trimmed = value.trim();
        if (trimmed && trimmed !== currentTitle) onSave(chatId, trimmed);
        else onCancel();
    };
    return (
        <input
            ref={inputRef}
            className="chat-item__rename-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleSave(); if (e.key === "Escape") onCancel(); }}
            onBlur={handleSave}
            onClick={(e) => e.preventDefault()}
        />
    );
}

export default function Sidebar({
    documents, chats, activeChatId, isOpen, onClose, onUploadClick,
    onDeleteDoc, onDeleteChat, onChatCreated, onChatRenamed,
}: SidebarProps) {
    const router = useRouter();
    const [expandedDocs, setExpandedDocs] = useState<Set<string>>(new Set());
    const [creatingChat, setCreatingChat] = useState<string | null>(null);
    const [renamingChatId, setRenamingChatId] = useState<string | null>(null);

    const toggleDoc = (docId: string) => {
        setExpandedDocs((prev) => {
            const next = new Set(prev);
            if (next.has(docId)) next.delete(docId); else next.add(docId);
            return next;
        });
    };

    const handleNewChat = async (docId: string) => {
        try {
            setCreatingChat(docId);
            const chat = await api.createChat(docId);
            onChatCreated({ id: chat.id, document_id: chat.document_id, title: chat.title, created_at: chat.created_at, updated_at: chat.updated_at, message_count: 0 });
            onClose();
            router.push(`/chat/${chat.id}`);
        } catch { /* ignore */ } finally { setCreatingChat(null); }
    };

    const handleRename = async (chatId: string, newTitle: string) => {
        setRenamingChatId(null);
        try { await api.updateChat(chatId, { title: newTitle }); onChatRenamed(chatId, newTitle); } catch { /* ignore */ }
    };

    const getChatsForDoc = (docId: string) => chats.filter((c) => c.document_id === docId);
    const activeChatDocId = chats.find((c) => c.id === activeChatId)?.document_id;

    return (
        <>
            {isOpen && <div className="sidebar-backdrop" onClick={onClose} />}
            <aside className={`sidebar${isOpen ? " sidebar--open" : ""}`}>
                <div className="sidebar__header">
                    <div className="sidebar__title-row">
                        <div className="sidebar__title">Documents</div>
                        <button className="sidebar__close" onClick={onClose} aria-label="Close sidebar">×</button>
                    </div>
                    <button className="sidebar__upload-btn" onClick={() => { onUploadClick(); onClose(); }}>
                        + Upload document
                    </button>
                </div>
                <div className="sidebar__list">
                    {documents.length === 0 ? (
                        <div className="sidebar__empty">
                            No documents yet.<br />Upload a financial filing to get started.
                        </div>
                    ) : (
                        documents.map((doc) => {
                            const docChats = getChatsForDoc(doc.id);
                            const isExpanded = expandedDocs.has(doc.id) || activeChatDocId === doc.id;
                            return (
                                <div key={doc.id} className="doc-group">
                                    <div
                                        className={`doc-card ${activeChatDocId === doc.id ? "doc-card--active" : ""}`}
                                        onClick={() => { if (doc.status === "ready") toggleDoc(doc.id); }}
                                    >
                                        <span className={`doc-card__dot doc-card__dot--${doc.status}`} />
                                        <div className="doc-card__info">
                                            <div className="doc-card__name">{doc.company_name}</div>
                                            <div className="doc-card__meta">
                                                {doc.filename}
                                                {docChats.length > 0 && (
                                                    <span className="doc-card__chat-count"> · {docChats.length} chat{docChats.length !== 1 ? "s" : ""}</span>
                                                )}
                                            </div>
                                        </div>
                                        <span className={`doc-card__status doc-card__status--${doc.status}`}>{doc.status}</span>
                                        <button
                                            className="doc-card__delete"
                                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); if (confirm(`Delete "${doc.company_name}" and all its chats?`)) onDeleteDoc(doc.id); }}
                                            title="Delete"
                                        >×</button>
                                    </div>
                                    {doc.status === "ready" && isExpanded && (
                                        <div className="doc-chats">
                                            <button className="doc-chats__new" onClick={() => handleNewChat(doc.id)} disabled={creatingChat === doc.id}>
                                                {creatingChat === doc.id ? "Creating..." : "+ New chat"}
                                            </button>
                                            {docChats.map((chat) => (
                                                <Link
                                                    key={chat.id}
                                                    href={`/chat/${chat.id}`}
                                                    className={`chat-item ${activeChatId === chat.id ? "chat-item--active" : ""}`}
                                                    onClick={onClose}
                                                >
                                                    {renamingChatId === chat.id ? (
                                                        <InlineRenameInput chatId={chat.id} currentTitle={chat.title} onSave={handleRename} onCancel={() => setRenamingChatId(null)} />
                                                    ) : (
                                                        <span className="chat-item__title">{chat.title}</span>
                                                    )}
                                                    <div className="chat-item__actions">
                                                        <button className="chat-item__action-btn" onClick={(e) => { e.preventDefault(); e.stopPropagation(); setRenamingChatId(chat.id); }} title="Rename">
                                                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                                                        </button>
                                                        <button className="chat-item__action-btn chat-item__action-btn--delete" onClick={(e) => { e.preventDefault(); e.stopPropagation(); if (confirm("Delete this chat?")) onDeleteChat(chat.id); }} title="Delete">
                                                            ×
                                                        </button>
                                                    </div>
                                                </Link>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })
                    )}
                </div>
            </aside>
        </>
    );
}
