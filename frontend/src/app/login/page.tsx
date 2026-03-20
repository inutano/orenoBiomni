"use client";

import { LoginPage } from "@/components/auth/login-page";
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LoginRoute() {
  const { isAuthenticated, isLoading, providers } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // If already authenticated or auth is disabled, redirect to home
    if (!isLoading && (isAuthenticated || !providers?.auth_enabled)) {
      router.replace("/");
    }
  }, [isAuthenticated, isLoading, providers, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--background)]">
        <p className="text-[var(--muted-foreground)]">Loading...</p>
      </div>
    );
  }

  if (isAuthenticated || !providers?.auth_enabled) {
    return null;
  }

  return <LoginPage />;
}
