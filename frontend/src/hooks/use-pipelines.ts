"use client";

import { useCallback, useEffect, useState } from "react";
import { listPipelines, getPipeline, cancelPipeline } from "@/lib/api-client";
import type { PipelineListItem, PipelineRead } from "@/types/pipeline";
import { TERMINAL_STATES } from "@/types/wes";

export function usePipelines(sessionId?: string, pollMs = 5000) {
  const [pipelines, setPipelines] = useState<PipelineListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const res = await listPipelines(sessionId);
      setPipelines(res);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    refresh();

    const id = setInterval(() => {
      if (document.hidden) return;
      const hasActive = pipelines.some(
        (p) => !TERMINAL_STATES.includes(p.state),
      );
      if (hasActive || pipelines.length === 0) refresh();
    }, pollMs);

    return () => clearInterval(id);
  }, [refresh, pollMs, pipelines]);

  return { pipelines, isLoading, refresh };
}

export function usePipeline(pipelineId: string | null, pollMs = 3000) {
  const [pipeline, setPipeline] = useState<PipelineRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!pipelineId) return;
    try {
      const res = await getPipeline(pipelineId);
      setPipeline(res);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [pipelineId]);

  useEffect(() => {
    refresh();

    const id = setInterval(() => {
      if (document.hidden) return;
      if (pipeline && !TERMINAL_STATES.includes(pipeline.state)) {
        refresh();
      }
    }, pollMs);

    return () => clearInterval(id);
  }, [refresh, pollMs, pipeline]);

  const cancel = useCallback(async () => {
    if (!pipelineId) return;
    const res = await cancelPipeline(pipelineId);
    setPipeline(res);
  }, [pipelineId]);

  return { pipeline, isLoading, refresh, cancel };
}
