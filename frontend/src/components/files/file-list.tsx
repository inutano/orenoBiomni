"use client";

import {
  Download,
  Trash2,
  File,
  FileText,
  FileCode,
  FileImage,
  FileArchive,
  FlaskConical,
} from "lucide-react";
import { formatTime } from "@/lib/utils";
import { getFileUrl } from "@/lib/api-client";
import type { FileInfo } from "@/types/files";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fileIcon(contentType: string, name: string) {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";

  // Bioinformatics formats
  if (
    ["fasta", "fa", "fastq", "fq", "vcf", "bed", "bam", "sam", "gff", "gtf", "h5ad", "rds"].includes(ext)
  ) {
    return <FlaskConical size={16} className="text-green-500" />;
  }

  if (contentType.startsWith("image/")) {
    return <FileImage size={16} className="text-purple-500" />;
  }
  if (["py", "r", "sh", "js", "ts"].includes(ext)) {
    return <FileCode size={16} className="text-blue-500" />;
  }
  if (
    contentType.startsWith("text/") ||
    ["csv", "tsv", "json", "xml", "txt", "md", "log"].includes(ext)
  ) {
    return <FileText size={16} className="text-orange-500" />;
  }
  if (["zip", "gz", "tar", "bz2", "xz"].includes(ext)) {
    return <FileArchive size={16} className="text-yellow-600" />;
  }

  return <File size={16} className="text-[var(--muted-foreground)]" />;
}

interface FileListProps {
  sessionId: string;
  files: FileInfo[];
  totalSize: number;
  onDelete: (path: string) => void;
}

export function FileList({ sessionId, files, totalSize, onDelete }: FileListProps) {
  if (files.length === 0) {
    return (
      <div className="text-center py-12 text-[var(--muted-foreground)]">
        No files yet. Upload files or run code to generate outputs.
      </div>
    );
  }

  function handleDelete(path: string, name: string) {
    if (window.confirm(`Delete "${name}"?`)) {
      onDelete(path);
    }
  }

  return (
    <div>
      <div className="text-xs text-[var(--muted-foreground)] px-4 py-2">
        {files.length} file{files.length !== 1 ? "s" : ""} &middot;{" "}
        {formatFileSize(totalSize)} total
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] text-left text-[var(--muted-foreground)]">
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Size</th>
              <th className="px-4 py-2 font-medium">Type</th>
              <th className="px-4 py-2 font-medium">Modified</th>
              <th className="px-4 py-2 font-medium">Source</th>
              <th className="px-4 py-2 font-medium w-24">Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr
                key={f.relative_path}
                className="border-b border-[var(--border)] hover:bg-[var(--muted)] transition-colors"
              >
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    {fileIcon(f.content_type, f.name)}
                    <span className="truncate max-w-xs" title={f.relative_path}>
                      {f.name}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-2 text-[var(--muted-foreground)] whitespace-nowrap">
                  {formatFileSize(f.size)}
                </td>
                <td className="px-4 py-2 text-[var(--muted-foreground)] font-mono text-xs">
                  {f.content_type.split("/").pop()}
                </td>
                <td className="px-4 py-2 text-[var(--muted-foreground)] whitespace-nowrap">
                  {formatTime(f.modified_at)}
                </td>
                <td className="px-4 py-2">
                  <span
                    className={`inline-block px-2 py-0.5 rounded text-xs ${
                      f.is_artifact
                        ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                        : "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300"
                    }`}
                  >
                    {f.is_artifact ? "artifact" : "upload"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <a
                      href={getFileUrl(sessionId, f.relative_path)}
                      download={f.name}
                      className="text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                      title="Download"
                    >
                      <Download size={16} />
                    </a>
                    <button
                      onClick={() => handleDelete(f.relative_path, f.name)}
                      className="text-[var(--muted-foreground)] hover:text-[var(--destructive)]"
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
