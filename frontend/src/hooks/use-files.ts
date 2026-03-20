"use client";

import { useCallback, useEffect, useState } from "react";
import * as api from "@/lib/api-client";
import type { FileInfo } from "@/types/files";

export function useFiles(sessionId: string) {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [totalSize, setTotalSize] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await api.listFiles(sessionId);
      setFiles(res.files);
      setTotalSize(res.total_size);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load files");
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const upload = useCallback(
    async (fileList: File[]) => {
      setIsUploading(true);
      setError(null);
      try {
        const res = await api.uploadFiles(sessionId, fileList);
        await refresh();
        return res.uploaded;
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Upload failed";
        setError(msg);
        throw e;
      } finally {
        setIsUploading(false);
      }
    },
    [sessionId, refresh],
  );

  const remove = useCallback(
    async (path: string) => {
      try {
        await api.deleteFile(sessionId, path);
        await refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Delete failed");
      }
    },
    [sessionId, refresh],
  );

  return { files, totalSize, isLoading, isUploading, error, refresh, upload, remove };
}
