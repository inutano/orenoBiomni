"use client";

import { use } from "react";
import { useFiles } from "@/hooks/use-files";
import { FileList } from "@/components/files/file-list";
import { FileUpload } from "@/components/files/file-upload";

export default function FilesPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = use(params);
  const { files, totalSize, isLoading, isUploading, error, upload, remove } =
    useFiles(sessionId);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="border-b border-[var(--border)] px-6 py-4">
        <h2 className="text-lg font-semibold">Session Files</h2>
        <p className="text-sm text-[var(--muted-foreground)]">
          Upload data files or download outputs from code execution.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Upload zone */}
        <FileUpload onUpload={upload} isUploading={isUploading} />

        {/* Error banner */}
        {error && (
          <div className="px-4 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* File list */}
        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-10 rounded-lg bg-[var(--border)] animate-pulse"
              />
            ))}
          </div>
        ) : (
          <FileList
            sessionId={sessionId}
            files={files}
            totalSize={totalSize}
            onDelete={remove}
          />
        )}
      </div>
    </div>
  );
}
