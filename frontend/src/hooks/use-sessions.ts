"use client";

import { useCallback, useEffect, useState } from "react";
import * as api from "@/lib/api-client";
import type { SessionListItem } from "@/types/session";

export function useSessions() {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setSessions(await api.listSessions());
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    // Periodic refresh for multi-tab consistency
    const interval = setInterval(refresh, 30_000);
    return () => clearInterval(interval);
  }, [refresh]);

  const create = useCallback(
    async (title?: string) => {
      const session = await api.createSession(title);
      await refresh();
      return session;
    },
    [refresh],
  );

  const remove = useCallback(
    async (id: string) => {
      await api.deleteSession(id);
      await refresh();
    },
    [refresh],
  );

  return { sessions, isLoading, refresh, create, remove };
}
