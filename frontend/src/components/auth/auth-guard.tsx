"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading, providers } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && providers?.auth_enabled && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, providers, router]);

  // Auth disabled — render children directly (backward compatible)
  if (!isLoading && !providers?.auth_enabled) {
    return <>{children}</>;
  }

  // Still loading
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen text-[var(--muted-foreground)]">
        Loading...
      </div>
    );
  }

  // Auth enabled but not authenticated — will redirect
  if (!isAuthenticated) {
    return null;
  }

  // Authenticated — render children
  return <>{children}</>;
}
