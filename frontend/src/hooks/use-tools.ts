"use client";

import { useCallback, useEffect, useState } from "react";
import { listTools, listDatasets } from "@/lib/api-client";
import type { ToolModule } from "@/types/tools";
import type { Dataset } from "@/types/tools";

export function useTools(search?: string) {
  const [tools, setTools] = useState<ToolModule[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await listTools(search);
      setTools(res.tools);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tools");
    } finally {
      setIsLoading(false);
    }
  }, [search]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { tools, isLoading, error, refresh };
}

export function useDatasets(search?: string) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await listDatasets(search);
      setDatasets(res.datasets);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load datasets");
    } finally {
      setIsLoading(false);
    }
  }, [search]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { datasets, isLoading, error, refresh };
}
