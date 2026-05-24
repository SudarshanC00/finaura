"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChatMessage as ChatMessageType } from "@/lib/types";
import ChartBlock from "./ChartBlock";

interface ChatMessageProps {
    message: ChatMessageType;
}

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // Fallback for older browsers / insecure contexts
            const textarea = document.createElement("textarea");
            textarea.value = text;
            textarea.style.position = "fixed";
            textarea.style.opacity = "0";
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    return (
        <button
            className={`message__copy ${copied ? "message__copy--copied" : ""}`}
            onClick={handleCopy}
            aria-label={copied ? "Copied" : "Copy response"}
            title={copied ? "Copied!" : "Copy"}
        >
            {copied ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            )}
            {copied && <span className="message__copy-label">Copied!</span>}
        </button>
    );
}

export default function ChatMessage({ message }: ChatMessageProps) {
    const isUser = message.role === "user";

    return (
        <div className={`message message--${message.role}`}>
            <div className="message__label">{isUser ? "You" : "Analyst"}</div>
            <div className="message__content">
                {isUser ? (
                    <p>{message.content}</p>
                ) : (
                    <>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                        </ReactMarkdown>
                        {message.chartData && <ChartBlock chart={message.chartData} />}
                        {message.sources && message.sources.length > 0 && (() => {
                            const seen = new Set<string>();
                            const unique = message.sources.filter((src) => {
                                const key = `${src.page}|${src.section}`;
                                if (seen.has(key)) return false;
                                seen.add(key);
                                return true;
                            });
                            return (
                                <div className="message__sources">
                                    <span className="message__sources-label">Sources</span>
                                    {unique.map((src, i) => (
                                        <span key={i} className="message__source">
                                            p.&nbsp;{src.page}
                                            {src.section !== "?" && ` · ${src.section}`}
                                        </span>
                                    ))}
                                </div>
                            );
                        })()}
                    </>
                )}
            </div>
            {!isUser && (
                <CopyButton text={message.content} />
            )}
        </div>
    );
}

export function LoadingMessage() {
    return (
        <div className="message message--assistant">
            <div className="message__label">Analyst</div>
            <div className="message__content">
                <div className="loading-dots">
                    <span />
                    <span />
                    <span />
                </div>
            </div>
        </div>
    );
}
