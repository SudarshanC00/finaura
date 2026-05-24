export interface DocumentInfo {
    id: string;
    filename: string;
    company_name: string;
    document_title: string;
    document_date: string;
    status: "uploading" | "processing" | "ready" | "error";
    created_at: string;
    file_size: number;
    error_message: string;
}

export interface QueryRequest {
    question: string;
    document_id: string;
}

export interface ChartData {
    type: "bar" | "line" | "pie";
    title: string;
    data: Record<string, string | number>[];
    xKey?: string;
    yKeys?: string[];
}

export interface QueryResponse {
    answer: string;
    sources: SourceInfo[];
    chart_data?: ChartData | null;
}

export interface SourceInfo {
    page: string;
    section: string;
    is_table: boolean;
}

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: SourceInfo[];
    chartData?: ChartData | null;
    timestamp: Date | string;
}

export interface ChatMessageStored {
    id: string;
    role: string;
    content: string;
    sources: SourceInfo[];
    chart_data?: ChartData | null;
    timestamp: string;
}

export interface ChatInfo {
    id: string;
    document_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    messages: ChatMessageStored[];
}

export interface ChatSummary {
    id: string;
    document_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    message_count: number;
}
