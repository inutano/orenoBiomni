"use client";

import { useCallback, useRef, useState } from "react";
import { Upload, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const ACCEPTED_EXTENSIONS = [
  ".csv", ".tsv",
  ".fasta", ".fa", ".fastq", ".fq",
  ".vcf", ".bed", ".bam", ".sam", ".gff", ".gtf",
  ".h5ad", ".rds",
  ".py", ".r", ".sh",
  ".txt", ".json", ".xml", ".log",
  ".png", ".jpg", ".jpeg", ".svg", ".pdf",
  ".zip", ".gz", ".tar",
].join(",");

interface FileUploadProps {
  onUpload: (files: File[]) => Promise<unknown>;
  isUploading: boolean;
}

export function FileUpload({ onUpload, isUploading }: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const dropped = Array.from(e.dataTransfer.files);
    if (dropped.length > 0) {
      setSelectedFiles((prev) => [...prev, ...dropped]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? []);
    if (picked.length > 0) {
      setSelectedFiles((prev) => [...prev, ...picked]);
    }
    // Reset input so re-selecting the same file triggers onChange
    if (inputRef.current) inputRef.current.value = "";
  }, []);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleUpload = useCallback(async () => {
    if (selectedFiles.length === 0) return;
    try {
      await onUpload(selectedFiles);
      setSelectedFiles([]);
    } catch {
      // Error is handled by the parent hook
    }
  }, [selectedFiles, onUpload]);

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
          isDragOver
            ? "border-[var(--accent)] bg-[var(--accent)]/5"
            : "border-[var(--border)] hover:border-[var(--muted-foreground)]",
        )}
      >
        <Upload
          size={32}
          className="mx-auto mb-2 text-[var(--muted-foreground)]"
        />
        <p className="text-sm text-[var(--muted-foreground)]">
          Drag and drop files here, or click to browse
        </p>
        <p className="text-xs text-[var(--muted-foreground)] mt-1">
          Max 100 MB per file
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS}
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Selected files list */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-[var(--muted-foreground)]">
            {selectedFiles.length} file{selectedFiles.length !== 1 ? "s" : ""} selected
          </div>
          <ul className="space-y-1">
            {selectedFiles.map((f, i) => (
              <li
                key={`${f.name}-${i}`}
                className="flex items-center justify-between px-3 py-1.5 bg-[var(--muted)] rounded text-sm"
              >
                <span className="truncate flex-1">{f.name}</span>
                <span className="text-xs text-[var(--muted-foreground)] mx-2 whitespace-nowrap">
                  {formatSize(f.size)}
                </span>
                <button
                  onClick={() => removeFile(i)}
                  className="text-[var(--muted-foreground)] hover:text-[var(--destructive)]"
                  title="Remove"
                >
                  <X size={14} />
                </button>
              </li>
            ))}
          </ul>
          <button
            onClick={handleUpload}
            disabled={isUploading}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium",
              "bg-[var(--accent)] text-[var(--accent-foreground)]",
              isUploading ? "opacity-50 cursor-not-allowed" : "hover:opacity-80",
            )}
          >
            {isUploading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload size={16} />
                Upload {selectedFiles.length} file{selectedFiles.length !== 1 ? "s" : ""}
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
