"use client";

import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { api } from "@/lib/api";
import { DocumentInfo } from "@/lib/types";

interface UploadModalProps {
    onClose: () => void;
    onUploaded: (doc: DocumentInfo) => void;
}

export default function UploadModal({ onClose, onUploaded }: UploadModalProps) {
    const [file, setFile] = useState<File | null>(null);
    const [companyName, setCompanyName] = useState("");
    const [documentTitle, setDocumentTitle] = useState("");
    const [documentDate, setDocumentDate] = useState("");
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState("");

    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles.length > 0) {
            const uploadedFile = acceptedFiles[0];
            setFile(uploadedFile);
            setError("");

            // Auto-detect company name from filename
            // e.g. "Nvidia_10k_report.pdf" -> "Nvidia"
            const nameMatch = uploadedFile.name.match(/^([A-Za-z0-9]+)/);
            if (nameMatch && nameMatch[1]) {
                const detectedName = nameMatch[1];
                // Only set if field is empty
                setCompanyName((prev) => prev.trim() === "" ? detectedName : prev);
            }
        }
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { "application/pdf": [".pdf"] },
        maxFiles: 1,
        multiple: false,
    });

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!file || !companyName.trim()) return;

        setUploading(true);
        setError("");

        try {
            const doc = await api.uploadDocument(
                file,
                companyName.trim(),
                documentTitle.trim(),
                documentDate.trim(),
            );
            onUploaded(doc);
            onClose();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
                <div className="modal__title">
                    Upload financial document
                    <button className="modal__close" onClick={onClose}>×</button>
                </div>

                <form onSubmit={handleSubmit} autoComplete="off">
                    <div
                        {...getRootProps()}
                        className={`dropzone ${isDragActive ? "dropzone--active" : ""}`}
                    >
                        <input {...getInputProps()} />
                        {!file ? (
                            <>
                                <div className="dropzone__icon">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                                </div>
                                <div className="dropzone__text">
                                    {isDragActive ? "Drop your PDF here" : "Drag and drop a PDF, or click to select"}
                                </div>
                                <div className="dropzone__hint">
                                    Supports 10-K, 10-Q, annual reports, and other financial filings
                                </div>
                            </>
                        ) : (
                            <div className="dropzone__file">
                                <span className="dropzone__file-name">{file.name}</span>
                                <span className="dropzone__file-size">{formatFileSize(file.size)}</span>
                            </div>
                        )}
                    </div>

                    <div className="form-group">
                        <label className="form-label">Company name *</label>
                        <input
                            className="form-input"
                            type="text"
                            placeholder="e.g., Nvidia Inc."
                            value={companyName}
                            onChange={(e) => setCompanyName(e.target.value)}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Document title</label>
                        <input
                            className="form-input"
                            type="text"
                            placeholder="e.g., 10-K Annual Report"
                            value={documentTitle}
                            onChange={(e) => setDocumentTitle(e.target.value)}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Filing date / period</label>
                        <input
                            className="form-input"
                            type="text"
                            placeholder="e.g., Fiscal Year 2025"
                            value={documentDate}
                            onChange={(e) => setDocumentDate(e.target.value)}
                        />
                    </div>

                    {error && <div className="form-error">{error}</div>}

                    <button
                        className="form-submit"
                        type="submit"
                        disabled={!file || !companyName.trim() || uploading}
                    >
                        {uploading ? <><span className="spinner" /> Uploading...</> : "Upload and process"}
                    </button>
                </form>
            </div>
        </div>
    );
}
