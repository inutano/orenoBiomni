"use client";

import { useCallback, useEffect, useState } from "react";
import { getHealth } from "@/lib/api-client";
import type { HealthResponse } from "@/types/health";

export function useHealth(intervalMs = 30000) {
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const refresh = useCallback(async () => {
    try {
      setHealth(await getHealth());
    } catch {
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
  }, [refresh, intervalMs]);

  return { health, refresh };
}
