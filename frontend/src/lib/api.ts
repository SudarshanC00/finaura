import { ChatInfo, ChatSummary, DocumentInfo, QueryRequest, QueryResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE) {
        this.baseUrl = baseUrl;
    }

    async healthCheck(): Promise<{ status: string; api_key_set: boolean }> {
        const res = await fetch(`${this.baseUrl}/api/health`);
        if (!res.ok) throw new Error("API health check failed");
        return res.json();
    }

    async listDocuments(): Promise<DocumentInfo[]> {
        const res = await fetch(`${this.baseUrl}/api/documents`);
        if (!res.ok) throw new Error("Failed to fetch documents");
        return res.json();
    }

    async getDocument(docId: string): Promise<DocumentInfo> {
        const res = await fetch(`${this.baseUrl}/api/documents/${docId}`);
        if (!res.ok) throw new Error("Document not found");
        return res.json();
    }

    async uploadDocument(
        file: File,
        companyName: string,
        documentTitle: string,
        documentDate: string,
    ): Promise<DocumentInfo> {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("company_name", companyName);
        formData.append("document_title", documentTitle);
        formData.append("document_date", documentDate);

        const res = await fetch(`${this.baseUrl}/api/documents/upload`, {
            method: "POST",
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Upload failed" }));
            throw new Error(err.detail || "Upload failed");
        }
        return res.json();
    }

    async deleteDocument(docId: string): Promise<void> {
        const res = await fetch(`${this.baseUrl}/api/documents/${docId}`, {
            method: "DELETE",
        });
        if (!res.ok) throw new Error("Failed to delete document");
    }

    async queryDocument(request: QueryRequest): Promise<QueryResponse> {
        const res = await fetch(`${this.baseUrl}/api/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(request),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Query failed" }));
            throw new Error(err.detail || "Query failed");
        }
        return res.json();
    }

    // ─── Chat APIs ───────────────────────────────────────────────────────

    async listChatsForDocument(docId: string): Promise<ChatSummary[]> {
        const res = await fetch(`${this.baseUrl}/api/documents/${docId}/chats`);
        if (!res.ok) throw new Error("Failed to fetch chats");
        return res.json();
    }

    async listAllChats(): Promise<ChatSummary[]> {
        const res = await fetch(`${this.baseUrl}/api/chats`);
        if (!res.ok) throw new Error("Failed to fetch chats");
        return res.json();
    }

    async createChat(docId: string): Promise<ChatInfo> {
        const res = await fetch(`${this.baseUrl}/api/documents/${docId}/chats`, {
            method: "POST",
        });
        if (!res.ok) throw new Error("Failed to create chat");
        return res.json();
    }

    async getChat(chatId: string): Promise<ChatInfo> {
        const res = await fetch(`${this.baseUrl}/api/chats/${chatId}`);
        if (!res.ok) throw new Error("Chat not found");
        return res.json();
    }

    async deleteChat(chatId: string): Promise<void> {
        const res = await fetch(`${this.baseUrl}/api/chats/${chatId}`, {
            method: "DELETE",
        });
        if (!res.ok) throw new Error("Failed to delete chat");
    }

    async updateChat(chatId: string, data: { title?: string }): Promise<ChatInfo> {
        const res = await fetch(`${this.baseUrl}/api/chats/${chatId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error("Failed to update chat");
        return res.json();
    }


    async sendChatMessage(chatId: string, question: string): Promise<QueryResponse> {
        const res = await fetch(`${this.baseUrl}/api/chats/${chatId}/messages`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Query failed" }));
            throw new Error(err.detail || "Query failed");
        }
        return res.json();
    }
}

export const api = new ApiClient();
