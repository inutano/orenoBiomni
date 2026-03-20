"use client";

import { useCallback, useEffect, useState } from "react";
import * as api from "@/lib/api-client";
import type { AuthUser, AuthProviders } from "@/types/auth";

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [providers, setProviders] = useState<AuthProviders | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        // Fetch provider config first
        const p = await api.getAuthProviders();
        if (cancelled) return;
        setProviders(p);

        if (!p.auth_enabled) {
          // Auth disabled — treat as always authenticated (anonymous)
          setUser({ id: "anonymous", email: "anonymous@local", display_name: "Anonymous", avatar_url: null, provider: "anonymous" });
          setIsLoading(false);
          return;
        }

        // Auth enabled — check current session
        try {
          const me = await api.getAuthMe();
          if (!cancelled) setUser(me);
        } catch {
          // Not authenticated — user stays null
          if (!cancelled) setUser(null);
        }
      } catch {
        // Backend unreachable — treat as auth disabled for graceful degradation
        if (!cancelled) {
          setProviders({ auth_enabled: false, google: false, github: false });
          setUser({ id: "anonymous", email: "anonymous@local", display_name: "Anonymous", avatar_url: null, provider: "anonymous" });
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    check();
    return () => { cancelled = true; };
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // Ignore errors — cookie might already be cleared
    }
    setUser(null);
    window.location.href = "/login";
  }, []);

  return {
    user,
    isLoading,
    isAuthenticated: user !== null,
    providers,
    logout: handleLogout,
  };
}
